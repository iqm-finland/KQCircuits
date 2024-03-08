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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

"""
This is a geometry diff tool to compare .oas or .gds files using LayoutDiff.

Expects two arguments: two files or two directories. It only compares OASIS or GDS2 files. If an
additional `-s` argument is given it will use `SmartCellMapping` to match PCells that may have been
renamed. Optional `-k` argument fires up KLayout and loads the differing files for further
investigation.

By default it runs using a single CPU, for extra speed, but also extra memory usage(!), you may
specify the number of CPUs to use in parallel, like: `-c 4`.

When two directories are compared it descends recursively and considers all .oas and .gds files.
Files only present in one directory will be reported to the user. Files present in both directories
are compared and reported if different.
"""


import os
import subprocess
from pathlib import Path
from sys import argv, exit as die
from multiprocessing import Pool
from kqcircuits.pya_resolver import pya, klayout_executable_command


def _load_oas_file(layout, file_name):
    load_opts = pya.LoadLayoutOptions()
    load_opts.warn_level = 0
    layout.read(file_name, load_opts)


def _filediff(files):
    diff = pya.LayoutDiff()
    smart = diff.SmartCellMapping if "-s" in argv else 0
    a, b = files
    l1 = pya.Layout()
    l2 = pya.Layout()
    _load_oas_file(l1, str(a))
    _load_oas_file(l2, str(b))
    c1 = l1.top_cells()[0] if smart else l1
    c2 = l2.top_cells()[0] if smart else l2
    if not diff.compare(c1, c2, smart):
        print(f"Differ: {a} {b}")
        return a, b
    else:
        return None


if __name__ == "__main__":
    if len(argv) < 3:
        print("Usage: 'gdiff X Y', where X and Y are both .oas or .gds files or directories containing such files.")
        die(-1)

    a = Path(argv[1]).resolve()
    b = Path(argv[2]).resolve()

    if a.is_file() and b.is_file():
        if a.suffix not in (".oas", ".gds") or b.suffix not in (".oas", ".gds"):
            print("Only compares OASIS and GDS files!")
            die(-1)
        d = _filediff((a, b))
        if d and "-k" in argv:
            subprocess.call((klayout_executable_command(), "-rx", "-t", "-i", "-s", d[0], d[1]))
        die(0)
    elif not (a.is_dir() and b.is_dir()):
        print("This command expects either two files or two directories!")
        die(-1)

    workdir = Path.cwd()
    os.chdir(a)
    da = set(list(Path().rglob("*.gds")) + list(Path().rglob("*.oas")))
    os.chdir(b)
    db = set(list(Path().rglob("*.gds")) + list(Path().rglob("*.oas")))
    os.chdir(workdir)

    for f in da - db:
        print("A only:", f)
    for f in db - da:
        print("B only:", f)

    file_pairs = ((a.joinpath(f), b.joinpath(f)) for f in sorted(list(db & da)))
    pmap = Pool(int(argv[argv.index("-c") + 1])).map if "-c" in argv else map  # pylint: disable=consider-using-with

    for d in pmap(_filediff, file_pairs):
        if d and "-k" in argv:
            subprocess.call((klayout_executable_command(), "-rx", "-t", "-i", "-s", d[0], d[1]))
