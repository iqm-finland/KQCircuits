# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
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


# Makes a .png image of all PCells into the pcell_images directory.

import os
import sys
import subprocess
from multiprocessing import Pool
from kqcircuits.util.library_helper import _get_all_pcell_classes
from kqcircuits.defaults import STARTUPINFO


DIR = "pcell_images"


def to_png(pcell):
    cmd = f"python pcell2png.py {pcell.__module__} {pcell.__name__} pcell_images"
    return subprocess.check_output(
        cmd, stderr=subprocess.STDOUT, shell=True, universal_newlines=True, startupinfo=STARTUPINFO
    )


if __name__ == "__main__":
    print(f"Creating PCell images in {DIR}...")
    os.makedirs(DIR, exist_ok=True)

    skip = True if "--skip-excluded-modules" in sys.argv else False
    pcells = _get_all_pcell_classes(skip_modules=skip)
    pool = Pool(os.cpu_count())
    err = pool.map(to_png, pcells)

    ret = 0
    for e in err:
        if e:
            print(e, file=sys.stderr)
            ret = -1
    print("Finished creating PCell images.")
    exit(ret)
