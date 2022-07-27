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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).


# Makes a .png image of all PCells into the pcell_images directory.

import os
import sys
import subprocess
from multiprocessing import Pool
from kqcircuits.util.library_helper import _get_all_pcell_classes
from kqcircuits.defaults import ROOT_PATH, STARTUPINFO


kqc_root_path = sys.argv[1] if len(sys.argv) == 2 else str(ROOT_PATH)
sys.path.append(kqc_root_path)
from setup_helper import klayout_configdir
configdir = klayout_configdir(kqc_root_path)
if not os.path.exists(f"{configdir}/python/kqcircuits"):
    print("Documentation generation needs KLayout. Please run setup_within_klayout.py.")
    sys.exit(-1)

DIR = ROOT_PATH.joinpath("docs/pcell_images")
DIR.mkdir(exist_ok=True)

script = ROOT_PATH.joinpath("docs/pcell2png.py")

if os.name == "nt":
    exe = os.path.join(os.getenv("APPDATA"), "KLayout", "klayout_app.exe")
    exe = f'set "KLAYOUT_HOME={configdir}" & "{exe}"'
else:
    exe = f'KLAYOUT_HOME={configdir} klayout'

# TODO only calculate for changed files
def to_png(cell):
    pcell = cell[0]
    lib = pcell.__module__
    cls = pcell.__name__
    cmd = f'{exe} -z -nc -r {script} -rd lib_name={lib} -rd cls_name={cls} -rd dest_dir={DIR} -rd cls_path={cell[1]}'
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True,
        universal_newlines=True, startupinfo=STARTUPINFO)


if __name__ == "__main__":

    print("Creating PCell images...")
    pcells = _get_all_pcell_classes()
    pool = Pool(os.cpu_count())
    err = pool.map(to_png, pcells)

    ret = 0
    for e in err:
        if e:
            print(e, file = sys.stderr)
            ret = -1
    print("Finished creating PCell images.")
    exit(ret)
