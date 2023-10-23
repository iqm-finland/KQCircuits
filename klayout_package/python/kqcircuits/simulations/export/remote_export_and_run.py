# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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


from pathlib import Path
import subprocess
import platform
import sys
import logging
import os
import stat
import uuid
from kqcircuits.defaults import TMP_PATH, SCRIPTS_PATH, KQC_REMOTE_TMP_PATH

logging.basicConfig(level=logging.WARN, stream=sys.stdout)

def _prepare_remote_tmp(ssh_login, kqc_remote_tmp_path):
    """
    Internal helper function to create remote tmp directory if it doesnt exist and raise error if its not empty

    Args:
        ssh_login              (str): ssh login info "user@hostname"
        kqc_remote_tmp_path    (str): current run tmp directory on remote
    """
    ssh_cmd = f"ssh {ssh_login} 'mkdir -p {kqc_remote_tmp_path} && ! {{ ls -1qA {kqc_remote_tmp_path} | grep -q . ; }}'"
    is_empty = subprocess.call(ssh_cmd, shell=True)
    if is_empty:
        logging.error(f"Your remote tmp folder {kqc_remote_tmp_path} is not empty!")
        logging.error("Either delete its contents manually or use another directory")
        sys.exit()

def _get_sbatch_time(export_tmp_paths) -> int:
    """
    Internal helper function to extract sbatch time limit from simulation.sh files

    Args:
        export_tmp_paths  (list[str]): list of export paths

    Returns:
        sbatch_time (int) Number of seconds for setting ssh timeout.
                          This is equal to total amount of time reserved for all batch jobs sent to remote
    """
    def _get_single_sbatch_time(simulation_script):
        with open(simulation_script , 'r') as f:
            for line in f:
                res = line.strip().partition("#SBATCH --time=")[2]
                if len(res) == 8:
                    times = res.split(':')
                    if len(times)==3:
                        return 3600*int(times[0]) + 60*int(times[1]) + int(times[2])
        return 0

    sbatch_time = 0
    for d in export_tmp_paths:
        t_meshes = _get_single_sbatch_time(Path(d)/"simulation_meshes.sh")
        t = _get_single_sbatch_time(Path(d)/"simulation.sh")
        if t == 0 or t_meshes == 0:
            logging.warning("Could not extract the sbatch time limit from simulation.sh or simulation_meshes.sh")
            logging.warning("Wait script timeout of 60 minutes will be used")
            return 3600
        else:
            sbatch_time += t

    return sbatch_time

def _remote_run(ssh_login: str,
                export_tmp_paths: list,
                kqc_remote_tmp_path: str,
                detach_simulation: bool,
                poll_interval: int):
    """
    Internal helper function to copy and run simulations to remote and back

    Args:
        ssh_login              (str): ssh login info "user@hostname"
        export_tmp_paths (list[str]): list of local tmp simulation export paths for the simulations to be run
        kqc_remote_tmp_path    (str): tmp directory on remote
        detach_simulation      (bool): Detach the remote simulation from terminal, not waiting for it to finish
        poll_interval           (int): Polling interval in seconds when waiting for the remote simulation to finish
    """
    if platform.system() == 'Windows':  # Windows
        logging.error("Connecting to remote host not supported on Windows")
        sys.exit()
    elif platform.system() == 'Darwin':  # macOS
        logging.error("Connecting to remote host not supported on Mac OS")
        sys.exit()
    # Else linux

    # set defaults
    if kqc_remote_tmp_path is None:
        kqc_remote_tmp_path = KQC_REMOTE_TMP_PATH

    if poll_interval is None:
        poll_interval = 60

    # Check if we sugin sbatch by checking if all export folders have `simulation_meshes.sh`
    if not all(((Path(d)/"simulation_meshes.sh").is_file() for d in export_tmp_paths)):
        logging.error('Simulation not exported with "sbatch" (simulation_meshes.sh does not exist)' )
        sys.exit()

    # Add uuid to the remote path for this run
    # Allows simultaneous calls to "kqc sim --remote"
    run_uuid = str(uuid.uuid4())
    kqc_remote_tmp_path = str(Path(kqc_remote_tmp_path) / ('run_' + run_uuid))
    # Create remote tmp if it doesnt exist, and check that its empty
    _prepare_remote_tmp(ssh_login,kqc_remote_tmp_path)

    dirs_remote = [str(Path(kqc_remote_tmp_path) / str(Path(d).name)) for d in export_tmp_paths]

    print('\nFEM simulations prepared successfully.\n'
          'Submitting the following simulations to the remote host (can take some time):', flush=True)
    for d1,d2 in zip(export_tmp_paths, dirs_remote):
        print(f"{d1}   --->   user@remote:{d2}", flush=True)
    print("\n", flush=True)


    remote_script_name = f"remote_simulation_{run_uuid}.sh"
    remote_simulation_script = str(TMP_PATH / remote_script_name)
    simlist = ' '.join(dirs_remote)

    remote_simulation = f"""#!/bin/bash
    sim_list=({simlist})

    for i in "${{sim_list[@]}}"; do
        cd "${{i}}" || exit
        RES=$(sbatch -J "{run_uuid}" ./simulation_meshes.sh) && sbatch -d afterok:${{RES##* }} -J "{run_uuid}" ./simulation.sh
    done;
    """
    with open(remote_simulation_script, "w") as file:
        file.write(remote_simulation)

    os.chmod(remote_simulation_script, os.stat(remote_simulation_script).st_mode | stat.S_IEXEC)

    # hardcoded option for copying back the vtu and pvtu files from remote
    copy_vtus = False
    skip_patterns = '-name "mesh.*" -o -name "*.msh" -o -name "scripts" -o -name "partitioning.*"'
    if not copy_vtus:
        skip_patterns = skip_patterns + ' -o -name "*.vtu" -o -name "*.pvtu"'
    skip_patterns = r'\( ' + skip_patterns +  r' \)'

    poll_interval_str = f"{poll_interval}s" if poll_interval <= 60 else f"{round(float(poll_interval)/60, 1)} min"
    # Write script to run in the background and copy results back once simulation is finished
    wait_and_copy_back_script = str(TMP_PATH / f"fetch_remote_simulation_data_{run_uuid}.sh")
    wait_and_copy_back = f"""#!/bin/bash
    set -e
    echo "\n---------START-WAIT-SCRIPT---------"
    echo "Simulations sent to queue at:"
    date +"%d-%m-%y %T"
    sleep 5
    echo "\nExplanation of Slurm job states"
    echo "ALL: Number of all unfinished jobs"
    echo " PD: Number of pending jobs"
    echo "  R: Number of currently running jobs\n"

    jobs_states=$(ssh {ssh_login} "squeue -h -n {run_uuid} -o%t")
    n_all=$(echo "$jobs_states" | wc -w)
    n_pd=$(echo "$jobs_states" | grep PD | wc -w)
    n_run=$(echo "$jobs_states" | grep R | wc -w)

    while [[ "$n_all" -gt 0  && $counter -le {_get_sbatch_time(export_tmp_paths)} ]]
    do
        echo -n "[ALL: $n_all, PD: $n_pd, R: $n_run] " && date +"%d-%m-%y %T"

        if [[ "$n_run" -gt 0 ]]
        then
            counter=$((counter + {poll_interval}))
        fi

        sleep {poll_interval}

        jobs_states=$(ssh {ssh_login} "squeue -h -n {run_uuid} -o%t")
        n_all=$(echo "$jobs_states" | wc -w)
        n_pd=$(echo "$jobs_states" | grep PD | wc -w)
        n_run=$(echo "$jobs_states" | grep R | wc -w)
    done

    ssh {ssh_login} 'find {kqc_remote_tmp_path} {skip_patterns} -exec rm -r "{{}}" +'

    scp -r -q {ssh_login}:"{simlist}" {str(TMP_PATH)}
    ssh {ssh_login} "rm -r {kqc_remote_tmp_path}"
    echo "\nSimulations finished at:"
    date +"%d-%m-%y %T"
    echo "---------STOP-WAIT-SCRIPT---------"
    rm -- "$0"
    """

    with open(wait_and_copy_back_script, "w") as file:
        file.write(wait_and_copy_back)
    os.chmod(wait_and_copy_back_script, os.stat(wait_and_copy_back_script).st_mode | stat.S_IEXEC)


    try:
        copy_cmd = ['scp', '-r', '-q'] + export_tmp_paths + \
                   [remote_simulation_script, ssh_login + ':' + kqc_remote_tmp_path]
        run_cmd =  f"""ssh {ssh_login} -tt -q 'bash -l -c "cd {kqc_remote_tmp_path} && ./{remote_script_name}"'"""
        # COPY (dirs_local) -> (dirs_remote)
        subprocess.check_call(copy_cmd)
        # Remove remote simulation script from local tmp folder
        subprocess.check_call(['rm',  remote_simulation_script])
        # Force to use login shell on remote to get correct env variables
        subprocess.check_call(run_cmd, shell=True)

        print(f"Simulations started and connection to remote closed.\n"
              f"Starting a script to follow the submitted jobs with {poll_interval_str} interval", flush=True)
        # start ssh poll and wait script
        if detach_simulation:
            nohup_file = str(TMP_PATH / f"nohup_{run_uuid}.out")
            wait_and_copy_back_script = "nohup " + wait_and_copy_back_script + " > " + nohup_file + " 2>&1 &"

        subprocess.check_call(wait_and_copy_back_script, shell=True)

        if detach_simulation:
            print("Simulation wait script sent to background. You can follow the job state with"
                  f" 'watch cat {nohup_file}'", flush=True)

    except Exception as exc:
        raise RuntimeError("Starting remote run failed. Please manually fetch and delete data from remote") from exc

def _allowed_simulations():
    """
    Helper to list allowed simulations, simulations scripts and tmp directory.

    Returns:
        tuple containing

            * allowed_simulations (list[str]): List of allowed simulation names
                                               cpw_fem_xsection.py added as an exception to this
            * simdir                    (str): Path to simulation scripts directory under KQCircuits
            * tmpdir                    (str): Path to tmp directory under KQCircuits
    """

    tmpdir = str(TMP_PATH)

    if 'KQCircuits' not in tmpdir:
        logging.error('Non-default tmp path. \
                      Check that the KQC_ROOT_PATH environment variable is properly set')
        sys.exit()

    simdir = str(SCRIPTS_PATH / "simulations")

    if 'KQCircuits' not in simdir:
        logging.error('Non-default simulations path. \
                      Check that the KQC_ROOT_PATH environment variable is properly set')
        sys.exit()

    allowed_simulations = ['cpw_fem_xsection.py']
    for f in os.listdir(simdir):
        if os.path.isfile(os.path.join(simdir, f)):
            allowed_simulations.append(f)

    return (allowed_simulations, simdir, tmpdir)


def remote_export_and_run(ssh_login: str,
                          kqc_remote_tmp_path: str=None,
                          detach_simulation :bool=False,
                          poll_interval: int=None,
                          export_path_basename: str=None,
                          args=None):
    """
    Exports locally and runs KQC simulations on a remote host. Froced to use no GUI (--quiet, -q option)

    Args:
        ssh_login              (str): ssh login info "user@hostname"
        kqc_remote_tmp_path    (str): tmp directory on remote
        detach_simulation     (bool): Detach the remote simulation from terminal, not waiting for it to finish
        poll_interval           (int): Polling interval in seconds when waiting for the remote simulation to finish
        export_path_basename   (str): Alternative export folder name for the simulation
                                      If None, the simulation script name will be used
        args                  (list): a list of strings:
                                        - If starts with a letter and ends with ".py"  -> export script
                                        - If starts with "-" or "--"                   -> script option
    """

    allowed_simulations, simdir, tmpdir = _allowed_simulations()

    export_scripts = []
    # By default use --use-sbatch and -q flags. Note that the export script must support this
    args_for_script = ['--use-sbatch', '-q']
    # Separate export script filenames and script arguments
    for arg in args:
        if arg.startswith('-'):
            args_for_script.append(arg)
        else:
            if arg.endswith('.py'):
                arg_filename = Path(arg).name
                arg_path = Path(simdir) / arg_filename
                if arg_filename != arg:
                    logging.warning(f"Concatenating the path to its final component and search in {simdir} instead")
                    logging.warning(f"{arg} -> {arg_filename} -> {arg_path}")
                if arg in allowed_simulations:
                    export_scripts.append(arg_path)
                else:
                    logging.warning(f"Skipping unkown simulation: {arg}")
            else:
                logging.warning(f"Skipping unkown argument: {arg}")

    if export_path_basename is not None and len(export_scripts) == 1:
        export_tmp_paths = [str(Path(tmpdir) / str(export_path_basename))]
    else:
        export_tmp_paths = [str(Path(tmpdir) / str(script.stem)) for script in export_scripts]

    if len(export_scripts) == 0:
        logging.error("No valid simulation script provided in remote_export_and_run")
        sys.exit()

    # Export simulation files locally
    for export_path, export_script in zip(export_tmp_paths, export_scripts):
        export_cmd = [sys.executable, export_script,
            '--simulation-export-path', str(export_path)] + args_for_script
        subprocess.call(export_cmd)

    # Run on remote
    _remote_run(ssh_login,
                export_tmp_paths,
                kqc_remote_tmp_path,
                detach_simulation,
                poll_interval)


def remote_run_only(ssh_login: str,
                    kqc_remote_tmp_path: str=None,
                    detach_simulation: bool=False,
                    poll_interval: int=None,
                    export_tmp_dirs: list=None):
    """
    Runs already locally exported simulations on remote host

    Args:
        ssh_login              (str): ssh login info "user@hostname"
        kqc_remote_tmp_path    (str): tmp directory on remote
        detach_simulation      (bool): Detach the remote simulation from terminal, not waiting for it to finish
        poll_interval           (int): Polling interval in seconds when waiting for the remote simulation to finish
        export_tmp_dirs   (list[str]): list of local tmp simulation folder names
                                       Could contain other arguments from console script which are filtered out
    """
    allowed_simulations, _, tmpdir = _allowed_simulations()

    allowed_simulations = [str(Path(sim).stem) for sim in allowed_simulations]

    paths_filtered = []
    if export_tmp_dirs is not None:
        for p in export_tmp_dirs:
            # Only allow paths directly under KQC tmp path
            p_filename = Path(p).name
            p_path = Path(tmpdir) / p_filename
            if p_filename != p:
                logging.warning(f"Concatenating the path to its final component and search in {tmpdir} instead")
                logging.warning(f"{p} -> {p_filename} -> {p_path}")
            if os.path.isdir(p_path):
                if any((sim in p  for sim in allowed_simulations)):
                    paths_filtered.append(p_path)

    if len(paths_filtered) == 0:
        logging.error("No valid simulation export paths provided in remote_run_only")
        sys.exit()

    # Run on remote
    _remote_run(ssh_login,
                paths_filtered,
                kqc_remote_tmp_path,
                detach_simulation,
                poll_interval)
