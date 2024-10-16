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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


import os
import stat
import logging
import json
import argparse
import platform
import copy

from dataclasses import replace
from pathlib import Path
from typing import Sequence, Union, Tuple, Dict, Optional

from kqcircuits.simulations.export.simulation_export import (
    copy_content_into_directory,
    get_post_process_command_lines,
    get_combined_parameters,
    export_simulation_json,
)
from kqcircuits.simulations.export.simulation_validate import validate_simulation
from kqcircuits.simulations.export.util import export_layers
from kqcircuits.util.export_helper import write_commit_reference_file
from kqcircuits.defaults import ELMER_SCRIPT_PATHS, KQC_REMOTE_ACCOUNT, SIM_SCRIPT_PATH
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.simulations.cross_section_simulation import CrossSectionSimulation
from kqcircuits.simulations.export.elmer.elmer_solution import ElmerEPR3DSolution, ElmerSolution, get_elmer_solution
from kqcircuits.simulations.post_process import PostProcess


def export_elmer_json(
    simulation: Union[Simulation, CrossSectionSimulation], solution: ElmerSolution, path: Path, workflow: dict
):
    """
    Export Elmer simulation into json and gds files.

    Args:
        simulation: The simulation to be exported.
        solution: The solution to be exported.
        path: Location where to write json and gds files.
        workflow: Parameters for simulation workflow

    Returns:
         Path to exported json file.
    """
    is_cross_section = isinstance(simulation, CrossSectionSimulation)

    if simulation is None or not isinstance(simulation, (Simulation, CrossSectionSimulation)):
        raise ValueError("Cannot export without simulation")

    # write .gds file
    gds_file = simulation.name + ".gds"
    gds_file_path = str(path.joinpath(gds_file))
    if not Path(gds_file_path).exists():
        export_layers(
            gds_file_path,
            simulation.layout,
            [simulation.cell],
            output_format="GDS2",
            layers=simulation.get_layers(),
        )

    sim_data = simulation.get_simulation_data()
    sol_data = solution.get_solution_data()
    full_name = simulation.name + solution.name

    if is_cross_section:
        sif_names = [f"{full_name}_C"]
        if sol_data["run_inductance_sim"]:
            if any((london > 0 for london in sim_data["london_penetration_depth"].values())):
                sif_names += [f"{full_name}_L"]
            else:
                sif_names += [f"{full_name}_C0"]
    elif solution.tool == "wave_equation":
        if solution.sweep_type == "interpolating":
            sif_names = []
        else:
            sif_names = [full_name + "_f" + str(f).replace(".", "_") for f in sol_data["frequency"]]
    else:
        sif_names = [full_name]

    json_data = {
        "name": full_name,
        "workflow": workflow,
        **sim_data,
        **sol_data,
        "sif_names": sif_names,
        "gds_file": gds_file,
        "parameters": get_combined_parameters(simulation, solution),
    }

    # write .json file
    json_file_path = str(path.joinpath(full_name + ".json"))
    export_simulation_json(json_data, json_file_path)

    return json_file_path


def export_elmer_script(
    json_filenames,
    path: Path,
    workflow=None,
    script_folder: str = "scripts",
    file_prefix: str = "simulation",
    script_file: str = "run.py",
    post_process=None,
    compile_elmer_modules=False,
):
    """
    Create script files for running one or more simulations.
    Create also a main script to launch all the simulations at once.

    Args:
        json_filenames: List of paths to json files to be included into the script.
        path: Location where to write the script file.
        workflow: Parameters for simulation workflow
        script_folder: Path to the Elmer-scripts folder.
        file_prefix: File prefix of the script file to be created.
        script_file: Name of the script file to run.
        post_process: List of PostProcess objects, a single PostProcess object, or None to be executed after simulations
        compile_elmer_modules: Compile custom Elmer energy integration module at runtime. Not supported on Windows.

    Returns:

        Path of exported main script file
    """

    if workflow is None:
        workflow = {}
    sbatch = "sbatch_parameters" in workflow

    python_executable = workflow.get("python_executable", "python")
    main_script_filename = str(path.joinpath(file_prefix + ".sh"))
    execution_script = Path(script_folder).joinpath(script_file)

    n_jsons = len(json_filenames)
    elmer_compile_str = (
        'echo "Compiling Elmer modules"\n'
        f"elmerf90 -fcheck=all {script_folder}/SaveBoundaryEnergy.F90 -o SaveBoundaryEnergy > /dev/null\n"
    )

    path.joinpath("log_files").mkdir(parents=True, exist_ok=True)

    def _write_script(filename, lines, interp_line="#!/bin/bash\n"):
        """Writes a script and makes it executable.
        `lines` is a string or list of strings that will be written into `filename`"""
        with open(filename, "w", encoding="utf-8") as file:
            if isinstance(lines, list):
                lines = "".join(lines)
            file.write(interp_line + lines)
        # change permissions
        os.chmod(filename, os.stat(filename).st_mode | stat.S_IEXEC)

    def _get_from_json(json_filename, keys):
        with open(json_filename, encoding="utf-8") as f:
            json_data = json.load(f)
            # return as a tuple
            return (*[json_data[k] for k in keys],)

    def _sim_part_echo(i, part):
        return f'echo "Simulation {i + 1}/{n_jsons} {part}"\n'

    if sbatch:

        def _multiply_time(time_str, multiplier):
            """
            Helper function to multiply a time of format "HH:MM:SS" with a constant. In
            this case, we multiply timeout per simulation by the number of simulations

            Args:
                time_str (str): Time in format "HH:MM:SS"
                multiplier (float): multiplier

            Returns:
                New time string in format "HH:MM:SS"
            """
            time_str = time_str.strip()
            if len(time_str) != 8:
                raise ValueError('Invalid sbatch/slurm time formatting! Format has to be "HH:MM:SS"')
            hours = int(int(time_str[0:2]) * multiplier)
            minutes = int(int(time_str[3:5]) * multiplier)
            seconds = int(int(time_str[6:8]) * multiplier)
            if seconds > 60:
                minutes = minutes + seconds // 60
                seconds = seconds % 60
            if minutes > 60:
                hours = hours + minutes // 60
                minutes = minutes % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        def _multiply_mem(mem_str, multiplier):
            """
            Helper function to multiply a memory specification with a constant. If multiplier < 1,
            will convert to using smaller units if possible

            Args:
                mem_str (str): Amount of memory in format "1234X" where "X" specifies the unit
                               and anything before is a number specifying the amount
                multiplier (float): multiplier

            Returns:
                New memory string
            """
            original_memstr = mem_str.strip()
            unit = original_memstr[-1]
            if unit in ("K", "M", "G", "T"):
                original_mem_int = int(original_memstr.partition(unit)[0])
            else:
                original_mem_int = int(original_memstr)
                unit = "M"
            downconversion = {"M": "K", "G": "M", "T": "G"}
            if multiplier < 1.0 and unit != "K":
                elmer_mem_per_f = int(original_mem_int * 1024 * multiplier)
                elmer_mem_per_f = str(elmer_mem_per_f) + downconversion[unit]
            else:
                elmer_mem_per_f = int(original_mem_int * multiplier)
                elmer_mem_per_f = str(elmer_mem_per_f) + unit
            return elmer_mem_per_f

        def _divup(a, b):
            return -(a // -b)

        def _get_srun_command(nodes, tasks, cores, memory):
            return f"srun -N {nodes} -n {tasks} -c {cores} --cpu-bind none --exact --mem={memory}"

        def _get_sbatch_lines(sbatch_settings):
            lines = []
            for s_key, s_value in sbatch_settings.items():
                lines.append(f"#SBATCH {s_key}={s_value}\n")
            lines += [
                "\n# set the number of threads based on --cpus-per-task\n",
                "export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK\n\n",
            ]
            return lines

        sbatch_parameters = workflow["sbatch_parameters"]

        parallelization_level = workflow["_parallelization_level"]
        n_simulations = workflow["_n_simulations"]
        _n_workers = int(sbatch_parameters.pop("n_workers", 1))

        if parallelization_level == "full_simulation":
            n_workers_full = _n_workers
            n_workers_elmer_only = 1
            n_simulations_gmsh = n_simulations
        elif parallelization_level == "elmer":
            n_workers_full = 1
            n_workers_elmer_only = _n_workers
            n_simulations_gmsh = 1
        elif parallelization_level == "none":
            n_workers_full = 1
            n_workers_elmer_only = 1
            n_simulations_gmsh = 1
        else:
            logging.warning(f"Unknown parallelization level {parallelization_level}")

        if sbatch_parameters.get("--account", "project_0") == "project_0":
            sbatch_parameters["--account"] = KQC_REMOTE_ACCOUNT

        common_keys = [k for k in sbatch_parameters.keys() if k.startswith("--")]
        sbatch_settings_elmer = {k: sbatch_parameters.pop(k) for k in common_keys}

        sbatch_settings_meshes = sbatch_settings_elmer.copy()

        max_cpus_per_node = int(sbatch_parameters.pop("max_threads_per_node", 40))

        elmer_tasks_per_worker = int(sbatch_parameters.pop("elmer_n_processes", 10))
        elmer_cpus_per_task = int(sbatch_parameters.pop("elmer_n_threads", 1))
        if elmer_cpus_per_task > 1 and elmer_tasks_per_worker > 1:
            logging.warning(
                "Using both process and thread level parallelization with Elmer might result in poor performance"
            )
        elmer_cpus_per_worker = elmer_tasks_per_worker * elmer_cpus_per_task

        elmer_mem_per_worker = sbatch_parameters.pop("elmer_mem", "64G")

        if elmer_cpus_per_worker > max_cpus_per_node:
            elmer_nodes_per_worker = _divup(elmer_cpus_per_worker, max_cpus_per_node)
            elmer_total_nodes = elmer_nodes_per_worker * _n_workers
            elmer_tasks_per_node = min(elmer_tasks_per_worker, max_cpus_per_node)
            elmer_mem_per_node = _multiply_mem(elmer_mem_per_worker, _n_workers / elmer_total_nodes)
        else:
            elmer_nodes_per_worker = 1
            elmer_max_workers_per_node = max_cpus_per_node // elmer_cpus_per_worker
            elmer_total_nodes = _divup(_n_workers, elmer_max_workers_per_node)
            elmer_workers_per_node = min(_n_workers, elmer_max_workers_per_node)
            elmer_tasks_per_node = elmer_workers_per_node * elmer_tasks_per_worker
            elmer_mem_per_node = _multiply_mem(elmer_mem_per_worker, elmer_workers_per_node)

        gmsh_cpus_per_worker = int(sbatch_parameters.pop("gmsh_n_threads", 10))
        if gmsh_cpus_per_worker > max_cpus_per_node:
            raise RuntimeError(
                f"Requested more gmsh threads per worker {gmsh_cpus_per_worker}"
                f" than the limit per node {max_cpus_per_node}"
            )
        gmsh_max_workers_per_node = max_cpus_per_node // gmsh_cpus_per_worker
        gmsh_n_nodes = _divup(n_workers_full, gmsh_max_workers_per_node)
        gmsh_mem_per_worker = sbatch_parameters.pop("gmsh_mem", "64G")

        gmsh_workers_per_node = min(n_workers_full, gmsh_max_workers_per_node)
        gmsh_mem_per_node = _multiply_mem(gmsh_mem_per_worker, gmsh_workers_per_node)

        sbatch_settings_elmer["--time"] = _multiply_time(
            sbatch_parameters.pop("elmer_time", "00:10:00"), _divup(n_simulations, _n_workers)
        )
        sbatch_settings_elmer["--nodes"] = elmer_total_nodes
        sbatch_settings_elmer["--ntasks-per-node"] = elmer_tasks_per_node
        sbatch_settings_elmer["--cpus-per-task"] = elmer_cpus_per_task
        sbatch_settings_elmer["--mem"] = elmer_mem_per_node

        sbatch_settings_meshes["--time"] = _multiply_time(
            sbatch_parameters.pop("gmsh_time", "00:10:00"), _divup(n_simulations_gmsh, n_workers_full)
        )
        sbatch_settings_meshes["--nodes"] = gmsh_n_nodes
        sbatch_settings_meshes["--ntasks-per-node"] = gmsh_workers_per_node
        sbatch_settings_meshes["--cpus-per-task"] = gmsh_cpus_per_worker
        sbatch_settings_meshes["--mem"] = gmsh_mem_per_node

        srun_cmd_gmsh = _get_srun_command(1, 1, gmsh_cpus_per_worker, gmsh_mem_per_worker)
        srun_cmd_script = _get_srun_command(1, 1, 1, elmer_mem_per_worker)
        srun_cmd_elmer = _get_srun_command(
            elmer_nodes_per_worker, elmer_tasks_per_worker, elmer_cpus_per_task, elmer_mem_per_worker
        )

        if len(sbatch_parameters) > 0:
            logging.warning("Unused sbatch parameters: ")
            for k, v in sbatch_parameters.items():
                logging.warning(f"{k} : {v}")

        meshes_script_lines = _get_sbatch_lines(sbatch_settings_meshes)

        if compile_elmer_modules:
            meshes_script_lines.append(elmer_compile_str)

        for i, json_filename in enumerate(json_filenames):

            (simulation_name,) = _get_from_json(json_filename, ["name"])
            python_run_cmd = f'{python_executable} -u "{execution_script}" "{Path(json_filename).relative_to(path)}"'

            def get_log_cmd(logfile_suffix, filename=simulation_name):
                return f'2>&1 >> "log_files/{filename}.{logfile_suffix}.log"\n'

            script_lines = [
                "set -e\n",
                _sim_part_echo(i, "Gmsh"),
                f'{srun_cmd_gmsh} {python_run_cmd} --only-gmsh -q {get_log_cmd("Gmsh")}',
                _sim_part_echo(i, "ElmerGrid"),
                f'{srun_cmd_gmsh} ElmerGrid 14 2 "{simulation_name}.msh" {get_log_cmd("ElmerGrid")}',
            ]

            if int(elmer_tasks_per_worker) > 1:
                script_lines.append(
                    f'{srun_cmd_gmsh} ElmerGrid 2 2 "{simulation_name}" -metis {elmer_tasks_per_worker}'
                    f' 4 --partdual --removeunused {get_log_cmd("ElmerGrid")}'
                )

            script_lines += [
                _sim_part_echo(i, "Write Elmer sif files"),
                f'{srun_cmd_gmsh} {python_run_cmd} --only-elmer-sifs {get_log_cmd("Elmer_sifs")}',
            ]

            script_filename_meshes = str(path.joinpath(simulation_name + "_meshes.sh"))
            _write_script(script_filename_meshes, script_lines)

            meshes_script_lines += [
                f'echo "Submitting gmsh and ElmerGrid part {i + 1}/{n_jsons}"\n',
                'echo "--------------------------------------------"\n',
                f'source "{Path(script_filename_meshes).relative_to(path)}" &\n',
            ]

            if (i + 1) % n_workers_full == 0 or (i + 1) == n_jsons:
                meshes_script_lines.append("wait\n")

        _write_script(str(path.joinpath(file_prefix + "_meshes.sh")), meshes_script_lines)

        main_script_lines = _get_sbatch_lines(sbatch_settings_elmer)

        for i, json_filename in enumerate(json_filenames):
            simulation_name, sif_names = _get_from_json(json_filename, ["name", "sif_names"])

            sifs_split = [
                sif_names[i : min(i + n_workers_elmer_only, len(sif_names))]
                for i in range(0, len(sif_names), n_workers_elmer_only)
            ]

            python_run_cmd = f'{python_executable} -u "{execution_script}" "{Path(json_filename).relative_to(path)}"'

            def get_log_cmd(logfile_suffix, filename=simulation_name):  # pylint: disable=function-redefined
                return f'2>&1 >> "log_files/{filename}.{logfile_suffix}.log"\n'

            script_lines = ["set -e\n", _sim_part_echo(i, "Elmer")]

            for sif_list in sifs_split:
                for sif in sif_list:
                    sif_path = f"{simulation_name}/{sif}.sif"
                    script_lines.append(
                        f'{srun_cmd_elmer} ElmerSolver_mpi "{sif_path}" 2>&1 >> "log_files/{sif}.Elmer.log" & \n'
                    )
                script_lines.append("wait\n")

            script_lines += [
                _sim_part_echo(i, "write results json"),
                f'{srun_cmd_script} {python_run_cmd} --write-project-results {get_log_cmd("write_project_results")}',
            ]

            script_filename = str(path.joinpath(simulation_name + ".sh"))
            _write_script(script_filename, script_lines)

            main_script_lines += [
                f'echo "Submitting ElmerSolver part {i + 1}/{n_jsons}"\n',
                'echo "--------------------------------------------"\n',
                f'source "{Path(script_filename).relative_to(path)}" &\n',
            ]
            if (i + 1) % n_workers_full == 0 or (i + 1) == n_jsons:
                main_script_lines.append("wait\n")

        main_script_lines += [
            'echo "--------------------------------------------"\n',
            'echo "Write versions file"\n',
            f"{srun_cmd_script} {python_run_cmd} --write-versions-file\n",
        ]

    else:  # local workflow
        n_workers = workflow.get("n_workers", 1)
        parallelization_level = workflow["_parallelization_level"]
        parallelize_workload = parallelization_level == "full_simulation" and n_workers > 1

        main_script_lines = []

        if compile_elmer_modules:
            main_script_lines.append(elmer_compile_str)

        if parallelize_workload:
            main_script_lines.append(f"export OMP_NUM_THREADS={workflow['elmer_n_threads']}\n")
            main_script_lines.append(f"{python_executable} {script_folder}/simple_workload_manager.py {n_workers}")

        for i, json_filename in enumerate(json_filenames):
            (simulation_name,) = _get_from_json(json_filename, ["name"])
            python_run_cmd = f'{python_executable} "{execution_script}" "{Path(json_filename).relative_to(path)}"'

            def get_log_cmd(logfile_suffix, filename=simulation_name):
                return f'2>&1 >> "log_files/{filename}.{logfile_suffix}.log"\n'

            script_filename = str(path.joinpath(simulation_name + ".sh"))
            script_lines = [
                "set -e\n",
                _sim_part_echo(i, "Gmsh"),
                f'{python_run_cmd} --only-gmsh {get_log_cmd("Gmsh")}',
                _sim_part_echo(i, "ElmerGrid"),
                f'{python_run_cmd} --only-elmergrid {get_log_cmd("ElmerGrid")}',
                _sim_part_echo(i, "Write Elmer sif files"),
                f'{python_run_cmd} --only-elmer-sifs {get_log_cmd("Elmer_sifs")}',
                _sim_part_echo(i, "Elmer"),
                f"{python_run_cmd} --only-elmer\n",
                _sim_part_echo(i, "Paraview"),
                f"{python_run_cmd} --only-paraview\n",
                _sim_part_echo(i, "Write results json"),
                f'{python_run_cmd} --write-project-results {get_log_cmd("write_project_results")}',
            ]

            _write_script(script_filename, script_lines)

            if parallelize_workload:
                main_script_lines.append(f' "./{Path(script_filename).relative_to(path)}"')
            else:
                main_script_lines += [
                    f'echo "Submitting the main script of simulation {i + 1}/{n_jsons}"\n',
                    'echo "--------------------------------------------"\n',
                    f'"./{Path(script_filename).relative_to(path)}"\n',
                ]

        main_script_lines += [
            'echo "--------------------------------------------"\n',
            'echo "Write versions file"\n',
            f"{python_run_cmd} --write-versions-file\n",
        ]

    main_script_lines.append("\n" + get_post_process_command_lines(post_process, path, json_filenames))
    _write_script(main_script_filename, main_script_lines)

    return main_script_filename


def export_elmer(
    simulations: Sequence[
        Union[
            Simulation,
            Tuple[Simulation, ElmerSolution],
            CrossSectionSimulation,
            Tuple[CrossSectionSimulation, ElmerSolution],
        ]
    ],
    path: Path,
    script_folder: str = "scripts",
    file_prefix: str = "simulation",
    script_file: str = "run.py",
    workflow: Optional[Dict] = None,
    skip_errors: bool = False,
    post_process: Optional[Union[PostProcess, Sequence[PostProcess]]] = None,
    **solution_params,
) -> Path:
    """
    Exports an elmer simulation model to the simulation path.

    Args:
        simulations: List of Simulation objects or tuples containing Simulation and Solution objects.
        path: Location where to output the simulation model
        script_folder: Path to the Elmer-scripts folder.
        file_prefix: File prefix of the script file to be created.
        script_file: Name of the script file to run.
        workflow: Parameters for simulation workflow
        skip_errors: Skip simulations that cause errors. (Default: False)

            .. warning::

               **Use this carefully**, some of your simulations might not make sense physically and
               you might end up wasting time on bad simulations.
        post_process: List of PostProcess objects, a single PostProcess object, or None to be executed after simulations
        solution_params: ElmerSolution parameters if simulations is a list of Simulation objects.

    Returns:
        Path to exported script file.
    """

    common_sol = None if all(isinstance(s, Sequence) for s in simulations) else get_elmer_solution(**solution_params)

    workflow = _update_elmer_workflow(simulations, common_sol, workflow)

    # If doing 3D epr simulations the custom Elmer energy integration module is compiled at runtime
    epr_sim = _is_epr_sim(simulations, common_sol)
    script_paths = ELMER_SCRIPT_PATHS + [SIM_SCRIPT_PATH / "elmer_modules"] if epr_sim else ELMER_SCRIPT_PATHS

    write_commit_reference_file(path)
    copy_content_into_directory(script_paths, path, script_folder)

    def make_names_elmer_compatible(sim, sol):
        """Replace dots with dashes and make lowercase"""
        sim.name = sim.name.replace(".", "-").lower()
        sol_name = sol.name.replace(".", "-").lower()
        if 2 * (len(sim.name) + len(sol_name)) + len("_20np01_t0001.vtu") >= 128:
            logging.warning(
                "Simulation and solution names might be too long for Elmer."
                "Try to shorten them or create the sweep manually"
            )

        return (sim, replace(sol, name=sol_name))

    json_filenames = []

    for sim_sol in simulations:
        simulation, solution = sim_sol if isinstance(sim_sol, Sequence) else (sim_sol, common_sol)
        simulation, solution = make_names_elmer_compatible(simulation, solution)
        validate_simulation(simulation, solution)
        try:
            json_filenames.append(export_elmer_json(simulation, solution, path, workflow))
        except (IndexError, ValueError, Exception) as e:  # pylint: disable=broad-except
            if skip_errors:
                logging.warning(
                    f"Simulation {simulation.name} skipped due to {e.args}. "
                    "Some of your other simulations might not make sense geometrically. "
                    "Disable `skip_errors` to see the full traceback."
                )
            else:
                raise UserWarning(
                    "Generating simulation failed. You can discard the errors using `skip_errors` in `export_elmer`. "
                    "Moreover, `skip_errors` enables visual inspection of failed and successful simulation "
                    "geometry files."
                ) from e

    return export_elmer_script(
        json_filenames,
        path,
        workflow,
        script_folder=script_folder,
        file_prefix=file_prefix,
        script_file=script_file,
        post_process=post_process,
        compile_elmer_modules=epr_sim,
    )


def _is_epr_sim(simulations, common_sol):
    """Helper to check if doing 3D epr simulation"""
    epr_sim = False
    if common_sol is None:
        if any(isinstance(simsol[1], ElmerEPR3DSolution) for simsol in simulations):
            epr_sim = True
    elif isinstance(common_sol, ElmerEPR3DSolution):
        epr_sim = True

    if epr_sim and platform.system() == "Windows":
        logging.warning("Elmer 3D EPR Simulations are not supported on Windows")
    return epr_sim


def _update_elmer_workflow(simulations, common_solution, workflow):
    """
    Modify workflow based on number of simulations and available computing resources

    Args:
        simulations: List of Simulation objects or tuples containing Simulation and Solution objects.
        common_solution: Solution object if not contained in `simulations`
        workflow: workflow to be updated

    Returns:
        Updated workflow
    """
    if workflow is None:
        workflow = {}
    workflow = copy.deepcopy(workflow)
    parallelization_level = "none"
    n_worker_lim = 1
    num_sims = len(simulations)

    if num_sims == 1:
        sol_obj = simulations[0][1] if common_solution is None else common_solution

        if sol_obj.tool == "wave_equation" and len(sol_obj.frequency) > 1:
            parallelization_level = "elmer"
            n_worker_lim = len(sol_obj.frequency)
    elif num_sims > 1:
        # TODO enable Elmer level parallelism with solution sweep
        n_worker_lim = num_sims
        parallelization_level = "full_simulation"

    workflow["_parallelization_level"] = parallelization_level
    workflow["_n_simulations"] = n_worker_lim

    if "sbatch_parameters" in workflow:
        n_workers = workflow["sbatch_parameters"].get("n_workers", 1.0)
        workflow["sbatch_parameters"]["n_workers"] = min(int(n_workers), n_worker_lim)
        workflow.pop("elmer_n_processes", "")
        workflow.pop("elmer_n_threads", "")
        workflow.pop("n_workers", "")
        workflow.pop("gmsh_n_threads", "")
    else:

        n_workers = workflow.get("n_workers", 1)
        n_processes = workflow.get("elmer_n_processes", 1)
        n_threads = workflow.get("elmer_n_threads", 1)

        if n_processes > 1 and n_threads > 1:
            logging.warning(
                "Using both process and thread level parallelization with Elmer might result in poor performance"
            )

        # for the moment avoid psutil.cpu_count(logical=False)
        max_cpus = int(os.cpu_count() / 2 + 0.5)
        workflow["local_machine_cpu_count"] = max_cpus

        if n_workers == -1:
            n_processes = 1 if n_processes == -1 else n_processes
            n_threads = 1 if n_threads == -1 else n_threads
            n_workers = max(max_cpus // (n_threads * n_processes), 1)
            n_workers = min(n_workers, n_worker_lim)
        elif n_processes == -1:
            n_workers = min(n_workers, n_worker_lim)
            n_threads = 1 if n_threads == -1 else n_threads
            n_processes = max(max_cpus // (n_threads * n_workers), 1)
        elif n_threads == -1:
            n_workers = min(n_workers, n_worker_lim)
            n_threads = max(max_cpus // (n_processes * n_workers), 1)

        requested_cpus = n_workers * n_processes * n_threads
        if requested_cpus > max_cpus:
            logging.warning(f"Requested more CPUs ({requested_cpus}) than available ({max_cpus})")

        gmsh_n_threads = workflow.get("gmsh_n_threads", 1)
        if gmsh_n_threads == -1:
            if parallelization_level == "full_simulation":
                gmsh_n_threads = max(max_cpus // n_workers, 1)
            else:
                gmsh_n_threads = max_cpus

        workflow["n_workers"] = n_workers
        workflow["elmer_n_processes"] = n_processes
        workflow["elmer_n_threads"] = n_threads
        workflow["gmsh_n_threads"] = gmsh_n_threads

    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--quiet", action="store_true")
    args, _ = parser.parse_known_args()

    if args.quiet:
        workflow.update(
            {
                "run_gmsh_gui": False,  # For GMSH: if true, the mesh is shown after it is done
                # (for large meshes this can take a long time)
                "run_paraview": False,  # this is visual view of the results
            }
        )

    return workflow
