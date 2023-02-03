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
import importlib.util
import argparse
import subprocess

from multiprocessing import Pool

has_tqdm = importlib.util.find_spec("tqdm") is not None
if has_tqdm:
    from tqdm import tqdm

_description = """
Run Elmer simulations with first-level parallelisation.
This means that N workers are created to run the given simulations, which themselves may be parallelised.
For example, with n_workers=4 and elmer_n_processes=2 in the workflow settings, up to 8 processes are used.
"""

parser = argparse.ArgumentParser(description=_description, epilog='A progress bar is shown if `tqdm` is installed.')
parser.add_argument('n_workers', metavar='n_workers', type=int, help='Number of workers to use')
parser.add_argument('simulations', metavar='sim', type=str, nargs='+', help='All simulations to simulate (`.sh` file)')


def worker(command):
    is_windows = os.name == 'nt'
    try:
        return subprocess.run(
            ['bash', command] if is_windows else command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as err:
        print(f'The worker for {err.cmd} exited with code {err.returncode}')
        if is_windows and 'is not recognized as an internal or external command' in err.stderr:
            print('Do you have Bash (e.g. Git Bash or MSYS2) installed?')
        return err

if __name__ == '__main__':
    args = parser.parse_args()
    pool = Pool(args.n_workers)  # pylint: disable=consider-using-with

    if has_tqdm:
        progress_bar = tqdm(total=len(args.simulations), unit='sim')

    def update_progress_bar(process):
        if has_tqdm:
            progress_bar.update()
        else:
            print(process.stdout, 'done!')

    print("Starting simulations:\n")
    for sim in args.simulations:
        pool.apply_async(worker, (sim,), callback=update_progress_bar)

    pool.close()
    pool.join()
