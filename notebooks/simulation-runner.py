# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import sys
import shutil
import logging
import time
from pathlib import Path
from importlib import import_module
import subprocess

from kqcircuits.klayout_view import MissingUILibraryException
from kqcircuits.pya_resolver import pya
import kqcircuits.util.library_helper as library_helper

from kqcircuits.klayout_view import KLayoutView
from kqcircuits.simulations.export.hfss.hfss_export import HfssExport, HfssBatch

logging.basicConfig(level=logging.WARN, stream=sys.stdout)

class_name = "SingleXmonsFullChipSim"

# Override default parameters as needed
parameters = {
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(2000, 2000)),
    #    "qubit_spacing": -8,  # um, 3 um between the qubit arms
    #    "arm_width_a": 24,
    #    "arm_width_b": 66,  # gap of 3 um around the center island
    #    "enable_flux_lines": False,
    #    "enable_transmission_line": True,
    #    "enable_drive_lines": False,
}

# ------------------------------------------------------------
# Resolve module and class
# ------------------------------------------------------------
module_name = library_helper.to_module_name(class_name)
library_name = library_helper.to_library_name(class_name)
try:
    module = import_module("kqcircuits.simulations." + module_name)
except ImportError as e:
    raise Exception("Failed to find module {}.".format(module_name)) from e
cls = getattr(module, class_name)

# ------------------------------------------------------------
# Create output directory
# ------------------------------------------------------------
dir_name = module_name + "_output"
dir_path = Path.cwd().parent.joinpath("tmp").joinpath(dir_name)
if dir_path.exists():
    if dir_path.is_dir():
        shutil.rmtree(dir_path)
time.sleep(0.1)
dir_path.mkdir()

# Script path on bargo
import_script_path = r"C:\Users\IQM\kqcircuit\simulation_scripts\hfss"

# ------------------------------------------------------------
# CREATE & EXPORT LAYOUT
# ------------------------------------------------------------

try:
    klayoutview = KLayoutView(current=True)
    klayoutview.add_default_layers()
    layout = klayoutview.get_active_layout()
except MissingUILibraryException:
    layout = pya.Layout()

hfss_exports = []
for length in [1, 2, 5, 10, 20, 50, 100, 200]:
    simulation = cls(layout, **{**parameters, 'waveguide_length': length, 'use_internal_ports': True, 'name': 'cpw_length_{}um'.format(length)})
    hfss_export = HfssExport(simulation, path=dir_path)
    hfss_export.write()
    hfss_exports.append(hfss_export)

hfss_batch = HfssBatch(hfss_exports, path=dir_path, import_script_path=import_script_path)
hfss_batch.write_oas()
hfss_batch.write_batch()

subprocess.call(str(hfss_batch.oas_filename), shell=True)
# subprocess.call(str(hfss_export.gds_filename), shell=True)
