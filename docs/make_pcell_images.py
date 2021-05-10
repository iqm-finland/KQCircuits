# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

# Makes a .png image of all PCells into the pcell_images directory.

import os
import sys
import subprocess
from multiprocessing import Pool
from kqcircuits.util.library_helper import _get_all_pcell_classes
from kqcircuits.defaults import ROOT_PATH


DIR = ROOT_PATH.joinpath("docs/pcell_images")
DIR.mkdir(exist_ok=True)

script = ROOT_PATH.joinpath("scripts/util/pcell2png.py")

if os.name == "nt":
    exe = os.path.join(os.getenv("APPDATA"), "KLayout", "klayout_app.exe")
else:
    exe = "klayout"


# TODO only calculate for changed files
def to_png(pcell):
    lib = pcell.__module__
    cls = pcell.__name__
    cmd = f'{exe} -z -nc -r {script} -rd lib_name={lib} -rd cls_name={cls} -rd dest_dir={DIR}'
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, universal_newlines=True)


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
