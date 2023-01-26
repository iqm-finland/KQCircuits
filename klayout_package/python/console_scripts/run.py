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
from pathlib import Path
from kqcircuits.simulations.export.export_and_run import export_and_run
from kqcircuits.defaults import TMP_PATH


def run():
    parser = argparse.ArgumentParser(description='KQC console scripts')

    subparser = parser.add_subparsers(dest="command")

    simulate_parser = subparser.add_parser('simulate', help='KQC simulation \
            export and run script. Run and export with a single command!')

    simulate_parser.add_argument('export_script', type=str, help='Name of the export script')
    simulate_parser.add_argument('-q', '--quiet', action="store_true", help='Quiet mode: No GUI')

    args, args_for_script = parser.parse_known_args()

    if args.command == "simulate":
        if Path(args.export_script).is_file():
            export_path = TMP_PATH / Path(args.export_script).stem
            export_and_run(args.export_script, export_path, args.quiet, args_for_script)
        else:
            print ("Export script not found: ", args.export_script)
