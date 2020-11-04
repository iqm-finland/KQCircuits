# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
import shutil
import time
from pathlib import Path
import subprocess

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.single_xmons_full_chip_sim import SingleXmonsFullChipSim
from kqcircuits.simulations.export.hfss.hfss_export import HfssExport

# Override default parameters as needed
parameters = {
    'use_ports': True,
    'launchers': True,            # True includes bonding pads and tapers, false includes only waveguides
    'use_test_resonators': True,  # True makes XS1, false makes XS2
    'n': 16,                      # Reduce number of point in waveguide corners
}

# Create output directory
dir_name = Path(__file__).stem + "_output"
dir_path = Path.cwd().parent.parent.joinpath("tmp").joinpath(dir_name)
if dir_path.exists():
    if dir_path.is_dir():
        shutil.rmtree(dir_path)
time.sleep(0.1)
dir_path.mkdir()

# Script path on bargo
import_script_path = r"C:\Users\IQM\kqcircuit\scripts\simulations\hfss"

# Create and export simulation
simulation = SingleXmonsFullChipSim(pya.Layout(), **parameters)
hfss_export = HfssExport(simulation, path=dir_path, port_width=200)
hfss_export.write()

# Open output file
subprocess.call(str(hfss_export.oas_filename), shell=True)
