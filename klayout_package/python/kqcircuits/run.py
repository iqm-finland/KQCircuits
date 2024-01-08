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
import argparse
import logging
import sys
import subprocess
from os import listdir, chdir
from os.path import isfile, join
from pathlib import Path
from kqcircuits.simulations.export.export_and_run import export_and_run
from kqcircuits.simulations.export.export_singularity import export_singularity
from kqcircuits.simulations.export.remote_export_and_run import remote_export_and_run, remote_run_only
from kqcircuits.defaults import TMP_PATH, SCRIPTS_PATH, ROOT_PATH

logging.basicConfig(level=logging.WARN, stream=sys.stdout)

def run():
    parser = argparse.ArgumentParser(description='KQC console scripts')

    subparser = parser.add_subparsers(dest="command")

    simulate_parser = subparser.add_parser('sim', help='KQC simulation \
            export and run script. Run and export with a single command!')
    mask_parser = subparser.add_parser('mask', help='Build KQC Mask.')

    singularity_parser = subparser.add_parser('singularity', help='Build and push \
                                              singularity image to remote host.')

    simulate_parser.add_argument('export_script', type=str, help='Name of the export script')
    simulate_parser.add_argument('--export-path-basename', type=str, default=None,
                                 help='The export folder will be `TMP_PATH / Path(export_path_basename)`, \
                                       if not given, then it will be `TMP_PATH / Path(args.export_script).stem`')
    simulate_parser.add_argument('-q', '--quiet', action="store_true", help='Quiet mode: No GUI')
    simulate_parser.add_argument('-e', '--export-only', action="store_true",
                                 help='Do not run simulation, only export generated files.')

    simulate_parser.add_argument('--remote', action="store_true",
                                 help='Export and run the simulations at remote host "user@host"')
    simulate_parser.add_argument('--remote-run-only', action="store_true",
                                 help='Run the simulation at remote host "user@host"')
    simulate_parser.add_argument('--kqc-remote-tmp-path', type=str, help='Path to the used tmp directory on remote')

    simulate_parser.add_argument('--detach', action="store_true",
                                 help='Detach the remote simulation from terminal, not waiting for it to finish')
    simulate_parser.add_argument('--poll-interval', type=int,
                                 help='Interval for polling the job state of remote simulation in seconds')

    mask_parser.add_argument('mask_script', type=str, help='Name of the mask script')
    mask_parser.add_argument('-d', '--debug', action="store_true", help="Debug mode. Use a single process and "
                             "print logs to standard output too.")
    mask_parser.add_argument('-m', '--mock_chips', action="store_true", help="Replace all chips with empty frames for "
                                                                             "faster testing of the mask layout")
    mask_parser.add_argument('-s', '--skip_extras', action="store_true", help="Skip netlist and documentation export")
    mask_parser.add_argument('-c N', action="store_true", help="Limit the number of used CPUs to 'N'")

    singularity_parser.add_argument('--build', action="store_true", help='build singularity image locally')
    singularity_parser.add_argument('--push', type=str, help='Destination of the export "user@host:dir"\
                                    if left empty the defaults from .remote_profile.txt will be used')
    singularity_parser.add_argument('--singularity-remote-path', type=str,
                                    help='Installation path for the singularity image on remote')

    args, args_for_script = parser.parse_known_args()

    if args.command == "sim":
        if args.export_script == "ls":
            simdir = Path(SCRIPTS_PATH / "simulations")
            for f in listdir(simdir):
                if isfile(join(simdir, f)):
                    print(f)
            return

        if args.remote:
            remote_host = str(args.export_script)
            remote_export_and_run(remote_host,
                                  args.kqc_remote_tmp_path,
                                  args.detach,
                                  args.poll_interval,
                                  args.export_path_basename,
                                  args_for_script)
            return
        if args.remote_run_only:
            remote_host = str(args.export_script)
            remote_run_only(remote_host,
                            args.kqc_remote_tmp_path,
                            args.detach,
                            args.poll_interval,
                            args_for_script)
            return

        script_file = Path(args.export_script)
        if args.export_path_basename is not None:
            export_path = TMP_PATH / args.export_path_basename
        else:
            export_path = TMP_PATH / script_file.stem

        if not script_file.is_file():
            script_file = Path(SCRIPTS_PATH / "simulations" / script_file)
            if not script_file.is_file():
                logging.error(f"Export script not found at {args.export_script} or {script_file}")
                return
        export_and_run(script_file, export_path, args.quiet, args.export_only, args_for_script)
    elif args.command == "mask":
        if args.mask_script == "ls":
            maskdir = Path(SCRIPTS_PATH / "masks")
            for f in listdir(maskdir):
                if isfile(join(maskdir, f)):
                    print(f)
            return
        script_file = Path(args.mask_script)
        if not script_file.is_file():
            script_file = Path(SCRIPTS_PATH / "masks" / args.mask_script)
            if not script_file.is_file():
                logging.error(f"Mask script not found at {args.mask_script} or {script_file}")
                return
        if args.debug:
            subprocess.call([sys.executable, script_file, '-d'])
        else:  # Windows needs this for multiprocessing
            with open(script_file) as mask_file:
                exec(mask_file.read())  # pylint: disable=exec-used
    elif args.command == "singularity":
        if args.build:
            chdir(Path(ROOT_PATH / "singularity"))
            with open('install_software.sh','r') as f:
                for line in f:
                    if 'export MPI_VERSION=' in line:
                        mpi_v = line.partition('export MPI_VERSION=')[2].strip()
                        print((f"Singularity will use MPI version {mpi_v}. "
                                "Make sure this corresponds to the MPI version on the target machine\n"
                                "MPI and other package versions used by singularity can be changed "
                                "in the beginning of the /singularity/install_software.sh script"))
                        break
            subprocess.call("./singularity.sh", shell=True)
        elif args.push is not None:
            export_singularity(args.push, args.singularity_remote_path)
    else:
        parser.print_usage()
