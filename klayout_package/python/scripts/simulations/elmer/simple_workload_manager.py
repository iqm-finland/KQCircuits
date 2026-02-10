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
import argparse
from run_helpers import pool_run_cmds


_description = """
Run Elmer simulations with first-level parallelisation.
This means that N workers are created to run the given simulations, which themselves may be parallelised.
For example, with n_workers=4 and elmer_n_processes=2 in the workflow settings, up to 8 processes are used.

Usage options:

1. Give list of simulation scripts on command line:  "python simple_workload_manager.py 4 sim1.sh sim2.sh ..."
2. Load simulation script names from a file:         "python simple_workload_manager.py 4 simulation_list.txt"

"""

parser = argparse.ArgumentParser(description=_description, epilog="A progress bar is shown if `tqdm` is installed.")
parser.add_argument("n_workers", metavar="n_workers", type=int, help="Number of workers to use")
parser.add_argument("simulations", metavar="sim", type=str, nargs="+", help="All simulations to simulate")

if __name__ == "__main__":
    args = parser.parse_args()
    env = os.environ.copy()
    sim_list = args.simulations

    # Load from file if a single .txt file is given
    if len(sim_list) == 1 and sim_list[0].endswith(".txt"):
        with open(args.simulations[0], "r", encoding="utf-8") as f:
            sim_list = [l.strip() for l in f if len(l.strip()) > 0]
    pool_run_cmds(args.n_workers, sim_list, env=env, cwd=os.getcwd())
