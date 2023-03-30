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
from pathlib import Path
from kqcircuits.simulations.export.export_and_run import export_and_run
from kqcircuits.defaults import TMP_PATH, SCRIPTS_PATH

logging.basicConfig(level=logging.WARN, stream=sys.stdout)

def run():
    parser = argparse.ArgumentParser(description='KQC console scripts')

    subparser = parser.add_subparsers(dest="command")

    simulate_parser = subparser.add_parser('simulate', help='KQC simulation \
            export and run script. Run and export with a single command!')
    mask_parser = subparser.add_parser('mask', help='Build KQC Mask.')

    simulate_parser.add_argument('export_script', type=str, help='Name of the export script')
    simulate_parser.add_argument('--export-path-basename', type=str, default=None,
                                 help='The export folder will be `TMP_PATH / Path(export_path_basename)`, \
                                       if not given, then it will be `TMP_PATH / Path(args.export_script).stem`')
    simulate_parser.add_argument('-q', '--quiet', action="store_true", help='Quiet mode: No GUI')

    mask_parser.add_argument('mask_script', type=str, help='Name of the mask script')
    mask_parser.add_argument('-d', '--debug', action="store_true", help="Debug mode. Use a single process and "
                             "print logs to standard output too.")
    mask_parser.add_argument('-c N', action="store_true", help="Limit the number of used CPUs to 'N'")

    args, args_for_script = parser.parse_known_args()

    if args.command == "simulate":
        script_file = Path(args.export_script)
        if not script_file.is_file():
            script_file = Path(SCRIPTS_PATH / "simulations" / args.export_script)
            if not script_file.is_file():
                logging.error(f"Export script not found at {args.export_script} or {script_file}")
                return
        if args.export_path_basename is not None:
            export_path = TMP_PATH / args.export_path_basename
        else:
            export_path = TMP_PATH / Path(args.export_script).stem
        export_and_run(script_file, export_path, args.quiet, args_for_script)
    elif args.command == "mask":
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
    else:
        parser.print_usage()
