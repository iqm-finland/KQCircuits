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
from kqcircuits.defaults import TMP_PATH, SCRIPTS_PATH

logging.basicConfig(level=logging.WARN, stream=sys.stdout)


def _clear_remote_tmp(ssh_login, kqc_remote_tmp_path):
    """
    Internal helper function to delete temp directory on remote

    Args:
        ssh_login              (str): ssh login info "user@hostname"
        kqc_remote_tmp_path    (str): current run tmp directory on remote
    """
    subprocess.check_call(['ssh', ssh_login, 'rm','-r', Path(kqc_remote_tmp_path)])

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

def _get_sbatch_time(export_tmp_paths: str) -> int:
    """
    Internal helper function to extract sbatch time limit from simulation.sh files

    Args:
        export_tmp_paths  (list[str]): list of export paths

    Returns:
        sbatch_time (int) Number of seconds for setting ssh timeout.
                          This is equal to total amount of time reserved for all batch jobs sent to remote
    """
    def _get_single_sbatch_time(tmp_path: str):
        with open(Path(tmp_path)/"simulation.sh" , 'r') as f:
            for line in f:
                res = line.strip().partition("#SBATCH --time=")[2]
                if len(res) == 8:
                    times = res.split(':')
                    if len(times)==3:
                        return 3600*int(times[0]) + 60*int(times[1]) + int(times[2])

        logging.warning("Could not extract the sbatch time limit from simulation.sh. Ssh default timeout will be used")
        return 0

    sbatch_time = 0
    for d in export_tmp_paths:
        t = _get_single_sbatch_time(d)
        if t == 0:
            return 0
        else:
            sbatch_time += t

    return sbatch_time

def _remote_run(ssh_login: str, export_tmp_paths: list, kqc_remote_tmp_path: str):
    """
    Internal helper function to copy and run simulations to remote and back

    Args:
        ssh_login              (str): ssh login info "user@hostname"
        export_tmp_paths (list[str]): list of local tmp simulation export paths for the simulations to be run
        kqc_remote_tmp_path         (str): tmp directory on remote
    """
    if platform.system() == 'Windows':  # Windows
        logging.error("Connecting to remote host not supported on Windows")
        sys.exit()
    elif platform.system() == 'Darwin':  # macOS
        logging.error("Connecting to remote host not supported on Mac OS")
        sys.exit()
    # Else linux

    # Add uuid to the remote path for this run
    # Allows simultaneous calls to "kqc sim --remote"
    kqc_remote_tmp_path = str(Path(kqc_remote_tmp_path) / ('run_' + str(uuid.uuid4())))
    # Create remote tmp if it doesnt exist, and check that its empty
    _prepare_remote_tmp(ssh_login,kqc_remote_tmp_path)

    dirs_remote = [str(Path(kqc_remote_tmp_path) / str(Path(d).name)) for d in export_tmp_paths]

    print(f"\x1b[0;32;40mFollowing simulations will be run in {ssh_login}")
    for d1,d2 in zip(export_tmp_paths, dirs_remote):
        print(f"{d1}   --->   {d2}")
    print("\x1b[0m")


    remote_script_name = "remote_simulation.sh"
    remote_simulation_script = str(TMP_PATH / remote_script_name)
    simlist = ' '.join(dirs_remote)

    # hardcoded option for copying back the vtu and pvtu files from remote
    copy_vtus = False
    copy_vtus = '#' if copy_vtus else ''

    remote_simulation = f"""#!/bin/bash
    date
    sim_list=({simlist})

    for i in "${{sim_list[@]}}"; do
        cd "${{i}}" || exit
        sbatch -W ./simulation.sh &
    done;
    wait

    # delete meshes and vtus
    for i in "${{sim_list[@]}}"; do
        cd "${{i}}" || exit
        find . -name 'mesh.*' -delete
        {copy_vtus}find . -name '*.vtu' -delete
        {copy_vtus}find . -name '*.pvtu' -delete
        rm -r scripts
        rm ./*.msh || true
        find . -name 'partitioning.*' -exec rm -r "{{}}" +
    done;

    echo "Finished all batch jobs at"
    date
    """

    with open(remote_simulation_script, "w") as file:
        file.write(remote_simulation)

    os.chmod(remote_simulation_script, os.stat(remote_simulation_script).st_mode | stat.S_IEXEC)


    copy_cmd = ['scp', '-r'] + export_tmp_paths + [remote_simulation_script, ssh_login + ':' + kqc_remote_tmp_path]

    sbatch_time = _get_sbatch_time(export_tmp_paths)
    ssh_options = f'-o ServerAliveInterval={sbatch_time} -tt' if sbatch_time != 0 else '-tt'
    run_cmd =  f"""ssh {ssh_login} {ssh_options} 'bash -l -c "cd {kqc_remote_tmp_path} && ./{remote_script_name}"'"""
    copy_to_local_cmd = f"""scp -r {ssh_login}:"{simlist}" {str(TMP_PATH)}"""

    data_at_remote = False
    try:
        # COPY (dirs_local) -> (dirs_remote)
        subprocess.check_call(copy_cmd)
        data_at_remote = True

        # Force to use login shell on remote
        subprocess.call(run_cmd, shell=True)
        # copy results back
        subprocess.check_call(copy_to_local_cmd, shell=True) # Couldnt get this to work without shell
        _clear_remote_tmp(ssh_login, kqc_remote_tmp_path)
    except: # pylint: disable=bare-except
        logging.warning("Remote run not succesfull")
        if data_at_remote:
            try:
                _clear_remote_tmp(ssh_login, kqc_remote_tmp_path)
                logging.warning("Data automatically deleted on remote")
            except: # pylint: disable=bare-except
                logging.warning("Can't connect to the remote. Please manually delete data")
        else:
            logging.warning("Exit before moving data to remote")


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
                          kqc_remote_tmp_path: str='~/KQCircuits/tmp/',
                          args=None):
    """
    Exports locally and runs KQC simulations on a remote host. Froced to use no GUI (--quiet, -q option)

    Args:
        ssh_login              (str): ssh login info "user@hostname"
        kqc_remote_tmp_path    (str): tmp directory on remote
        args                  (list): a list of strings:
                                        - If starts with a letter and ends with ".py"  -> export script
                                        - If starts with "-" or "--"                   -> script option
    """

    if kqc_remote_tmp_path is None:
        kqc_remote_tmp_path = '~/KQCircuits/tmp/'

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
    _remote_run(ssh_login, export_tmp_paths, kqc_remote_tmp_path)


def remote_run_only(ssh_login: str,
                    export_tmp_dirs: list = None,
                    kqc_remote_tmp_path: str=None):
    """
    Runs already locally exported simulations on remote host

    Args:
        ssh_login              (str): ssh login info "user@hostname"
        export_tmp_dirs  (list[str]): list of local tmp simulation folder names
                                      Could contain other arguments from console script which are filtered out
        kqc_remote_tmp_path    (str): tmp directory on remote
    """
    if kqc_remote_tmp_path is None:
        kqc_remote_tmp_path = '~/KQCircuits/tmp/'

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
    _remote_run(ssh_login, paths_filtered, kqc_remote_tmp_path)
