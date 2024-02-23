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

import os
import argparse
from run_helpers import pool_run_cmds


_description = """
Run Elmer simulations with first-level parallelisation.
This means that N workers are created to run the given simulations, which themselves may be parallelised.
For example, with n_workers=4 and elmer_n_processes=2 in the workflow settings, up to 8 processes are used.
"""

parser = argparse.ArgumentParser(description=_description, epilog="A progress bar is shown if `tqdm` is installed.")
parser.add_argument("n_workers", metavar="n_workers", type=int, help="Number of workers to use")
parser.add_argument("simulations", metavar="sim", type=str, nargs="+", help="All simulations to simulate (`.sh` file)")

if __name__ == "__main__":
    args = parser.parse_args()
    env = os.environ.copy()
    pool_run_cmds(args.n_workers, args.simulations, env=env, cwd=os.getcwd())
