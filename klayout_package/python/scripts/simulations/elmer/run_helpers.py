# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not, see
# https://www.gnu.org/licenses/gpl-3.0.html.
#
# The software distribution should follow IQM trademark policy for open-source software
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).


import logging
import shutil
import subprocess
import os
import sys
import platform
import json
import glob
from pathlib import Path
from multiprocessing import Pool
import importlib.util

has_tqdm = importlib.util.find_spec("tqdm") is not None
if has_tqdm:
    from tqdm import tqdm


def write_simulation_machine_versions_file(path, name):
    """
    Writes file SIMULATION_MACHINE_VERSIONS into given file path.
    """
    versions = {}
    versions["platform"] = platform.platform()
    versions["python"] = sys.version_info

    gmsh_versions_list = []
    with open(path.joinpath("log_files").joinpath(name + ".Gmsh.log")) as f:
        gmsh_log = f.readlines()
        gmsh_versions_list = [line.replace("\n", "") for line in gmsh_log if "ersion" in line]

    elmer_versions_list = []
    with open(next(path.joinpath("log_files").glob("*Elmer.log"))) as f:
        elmer_log = f.readlines()
        elmer_versions_list = [line.replace("\n", "") for line in elmer_log if "ersion" in line]

    versions["gmsh"] = gmsh_versions_list
    versions["elmer"] = elmer_versions_list

    mpi_command = "mpirun" if shutil.which("mpirun") is not None else "mpiexec"
    if shutil.which(mpi_command) is not None:
        if mpi_command == "mpiexec":
            output = subprocess.check_output([mpi_command])
        else:
            output = subprocess.check_output([mpi_command, "--version"])
        versions["mpi"] = output.decode("ascii").split("\n", maxsplit=1)[0]

    paraview_command = "paraview"
    if shutil.which(paraview_command) is not None:
        try:
            output = subprocess.check_output([paraview_command, "--version"])
            versions["paraview"] = output.decode("ascii").split("\n", maxsplit=1)[0]
        except subprocess.CalledProcessError:
            versions["paraview"] = "unknown_version"

    with open("SIMULATION_MACHINE_VERSIONS.json", "w") as file:
        json.dump(versions, file)


def run_elmer_grid(msh_path, n_processes, exec_path_override=None):
    elmergrid_executable = shutil.which("ElmerGrid")
    if elmergrid_executable is not None:
        subprocess.check_call([elmergrid_executable, "14", "2", msh_path], cwd=exec_path_override)
        if n_processes > 1:
            subprocess.check_call(
                [
                    elmergrid_executable,
                    "2",
                    "2",
                    Path(msh_path).stem + "/",
                    "-metis",
                    str(n_processes),
                    "4",
                    "-removeunused",
                ],
                cwd=exec_path_override,
            )
    else:
        logging.warning(
            "ElmerGrid was not found! Make sure you have ElmerFEM installed: " "https://github.com/ElmerCSC/elmerfem"
        )
        sys.exit()


# Helper function to check if wsl is used
def is_microsoft(exec_path_override=None) -> bool:
    # See if version file contains the string microsoft -> wsl
    run_cmd = ["grep", "-qi", "microsoft", "/proc/version"]
    ret = subprocess.call(run_cmd, cwd=exec_path_override)
    # subprocess returns 0 if substring is found, 1 if not and some other error code is the call fails
    if ret not in (0, 1):
        raise RuntimeError(f"Unexpected return code {ret} in is_microsoft() subprocess call")
    return not ret


# Helper function to check if Elmer is run with singularity
# Note that this function only works when run OUTSIDE of singularity
def is_singularity(exec_path_override=None) -> bool:
    # Follow the symbolic link pointing to ElmerSolver and check if path contains "singularity"
    run_cmd = ["readlink", "-f", "$(which", "ElmerSolver)", "|", "grep", "-qi", "singularity"]
    ret = subprocess.call(" ".join(run_cmd), shell=True, cwd=exec_path_override)
    # subprocess returns 0 if substring is found, 1 if not and some other error code is the call fails
    if ret not in (0, 1):
        raise RuntimeError(f"Unexpected return code {ret} is_singularity() subprocess call")
    return not ret


def worker(command, outfile, cwd, env):
    """
    Worker for first level parallelization using Pool

    Args:
        command (str):       Command to be executed
        outfile (str/Path):  If not None the output will be written to this file
        cwd     (str/Path):  Working directory where the command will be executed
        env     (dict):      Environment variables

    Returns:
        Exit code of the process
    """
    is_windows = os.name == "nt"
    try:
        if outfile is not None:
            with open(outfile, "w") as f:
                return subprocess.check_call(
                    ["bash", command] if is_windows else command, stdout=f, stderr=f, text=True, env=env, cwd=cwd
                )
        else:
            return subprocess.check_call(["bash", command] if is_windows else command, text=True, env=env, cwd=cwd)
    except subprocess.CalledProcessError as err:
        logging.warning(f"The worker for {err.cmd} exited with code {err.returncode}")
        logging.warning(err)
        if is_windows and "is not recognized as an internal or external command" in err.stderr:
            logging.warning("Do you have Bash (e.g. Git Bash or MSYS2) installed?")
        return err


def pool_run_cmds(n_workers: int, cmds: list, output_files: list = None, cwd=None, env=None):
    """
    Workload manager for running multiple commands (Elmer instances) in parallel

    Args:
        n_workers           (int):   Max number of parallel processes
        cmds           (list[str]):  list of commands
        output_files   (list[str]):  list of output files, if none will print to stdout
        cwd             (str/Path):  Working directory where the commands will be executed
                                     (usually KQCircuits/tmp/sim_name)
        env                 (dict):  Environment variables

    """
    pool = Pool(n_workers)  # pylint: disable=consider-using-with

    if cwd is None:
        cwd = os.getcwd()
    if env is None:
        env = os.environ.copy()
    if has_tqdm:
        progress_bar = tqdm(total=len(cmds), unit="sim")

    def update_progress_bar(process):
        if has_tqdm:
            progress_bar.update()
        else:
            print(process.stdout, "done!")

    if output_files is None:
        output_files = len(cmds) * [None]
    print("Starting simulations:\n")
    for sim, f in zip(cmds, output_files):
        pool.apply_async(
            worker,
            (
                sim,
                f,
                cwd,
                env,
            ),
            callback=update_progress_bar,
        )

    pool.close()
    pool.join()


def elmer_check_warnings(log_file, cwd=None):
    """
    Reads the Elmer log file and propagates all warnings to python logging.warning

    Also logs a warning in case a linear system did not converge

    Args:
        log_file      (str): Relative path of the Elmer.log file (from cwd)
        cwd      (str/Path): Working directory where the commands will be executed
    """
    if cwd is not None:
        log_file = Path(cwd).joinpath(log_file)

    log_file = Path(log_file).resolve()

    with open(log_file, "r") as f:
        lines = [line.rstrip() for line in f]

    # Only log each warning once
    for ind, l in enumerate(lines):
        l_lower = l.lower()
        if "warning" in l_lower:
            logging.warning(f"{l.replace('WARNING::', '')}. See {log_file}:{ind+1}")
        elif "did not converge" in l_lower:
            logging.warning(f" Linear system iteration did not converge. See {log_file}:{ind+1}")
        elif "solution trivially zero" in l_lower:
            logging.warning(f" Solution trivially zero. See {log_file}:{ind+1}")


def _run_elmer_solver(sim_name, sif_names, n_parallel_simulations, n_processes, n_threads, exec_path_override=None):
    """
    Internal function for running ElmerSolver based on explicit variables instead of the json file

    Args:
        sim_name (str): Simulation name e.g name of the folder with sif files
        sif_names (list[str]): Simulation sif names. These sifs need to already exist when calling this function
        n_parallel_simulations (int): Number of parallel simulations
        n_processes (int): Number of dependent processes for each simulation
        n_threads (int): Number of threads to be used with elmer
        exec_path_override (str/Path): Working directory where the commands will be executed
                                       (usually KQCircuits/tmp/sim_name)
    """

    my_env = os.environ.copy()
    my_env["OMP_NUM_THREADS"] = str(n_threads)

    elmersolver_executable = shutil.which("ElmerSolver")
    elmersolver_mpi_executable = shutil.which("ElmerSolver_mpi")

    sif_paths = [Path(sim_name).joinpath(f"{sif_file}.sif") for sif_file in sif_names]

    if n_processes > 1 and elmersolver_mpi_executable is not None:
        if is_microsoft(exec_path_override) and is_singularity(exec_path_override):
            # If using wsl and singularity the mpi command needs to be given inside singularity
            run_cmds = [[elmersolver_mpi_executable, sif, "-np", str(n_processes)] for sif in sif_paths]
        else:
            mpi_command = "mpirun" if shutil.which("mpirun") is not None else "mpiexec"
            run_cmds = [[mpi_command, "-np", str(n_processes), elmersolver_mpi_executable, sif] for sif in sif_paths]

    elif elmersolver_executable is not None:
        run_cmds = [[elmersolver_executable, sif] for sif in sif_paths]
    else:
        logging.warning(
            "ElmerSolver was not found! Make sure you have ElmerFEM installed: " "https://github.com/ElmerCSC/elmerfem"
        )
        sys.exit()
    output_files = [f"log_files/{sif}.Elmer.log" for sif in sif_names]

    if n_parallel_simulations > 1:
        pool_run_cmds(n_parallel_simulations, run_cmds, output_files=output_files, cwd=exec_path_override, env=my_env)
    else:
        for cmd, out in zip(run_cmds, output_files):
            with open(out, "w") as f:
                subprocess.check_call(cmd, cwd=exec_path_override, env=my_env, stdout=f)

    for f in output_files:
        elmer_check_warnings(f, cwd=exec_path_override)


def run_elmer_solver(json_data, exec_path_override=None):
    """
    Runs Elmersolver for the sif files defined in json_data
    The meshes and .sif files must be already prepared and found in `exec_path_override` directory

    Args:
        json_data (dict): Simulation data loaded from the .json in simulation tmp folder
        exec_path_override(Path): Working directory from where the simulations are run (usually KQCircuits/tmp/sim_name)

    """
    if json_data["workflow"]["_parallelization_level"] == "elmer":
        n_parallel_simulations = json_data["workflow"].get("n_workers", 1)
    else:
        n_parallel_simulations = 1

    n_processes = json_data["workflow"].get("elmer_n_processes", 1)
    n_threads = json_data["workflow"].get("elmer_n_threads", 1)

    _run_elmer_solver(
        sim_name=json_data["name"],
        sif_names=json_data["sif_names"],
        n_parallel_simulations=n_parallel_simulations,
        n_processes=n_processes,
        n_threads=n_threads,
        exec_path_override=exec_path_override,
    )


def run_paraview(result_path, n_processes, exec_path_override=None):
    paraview_executable = shutil.which("paraview")
    if paraview_executable is not None:
        if n_processes > 1:
            pvtu_files = glob.glob("{}*.pvtu".format(result_path))
            subprocess.check_call([paraview_executable] + pvtu_files, cwd=exec_path_override)
        else:
            vtu_files = glob.glob("{}*.vtu".format(result_path))
            subprocess.check_call([paraview_executable] + vtu_files, cwd=exec_path_override)
    else:
        logging.warning("Paraview was not found! Make sure you have it installed: https://www.paraview.org/")
        sys.exit()
