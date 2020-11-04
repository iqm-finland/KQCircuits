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

class_name = "FingerCapacitorSim"

# Override default parameters as needed
parameters = {
    'use_internal_ports': False,
    'use_ports': True,
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(1000, 1000)),
    "finger_number": 5,
    "finger_width": 15,
    "finger_gap_side": 5,
    "finger_gap_end": 5,
    "finger_length": 20,
    "ground_padding": 10,
    "corner_r": 2
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
dir_name = Path(__file__).stem + "_output"
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


# Export function
def do_export(override_parameters):
    simulation = cls(layout, **{**parameters, **override_parameters})
    hfss_export = HfssExport(simulation, path=dir_path, port_width=200, wafer_stack_type="multiface")
    hfss_export.write()
    return hfss_export


# Sweep over one parameter
def do_sweep(parameter, values):
    return [do_export({parameter: value, 'name': 'finger_capacitor_{}_{}'.format(parameter, value)}) for value in
            values]


# Base simulation
hfss_exports += [do_export({'name': 'capacitor'})]

# Sweep CPW length (for measuring port-to-ground capacitance offset)
#
# Sweep number of fingers
fin_range = [3, 5, 7]

# Sweep finger length
len_range = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100 ]

for nr in fin_range:
    for leng in len_range:
        hfss_exports += [do_export({'finger_number': nr,
                                   'finger_length': leng,
                                   'name': 'finger_capacitor_{}_{}'.format(nr, leng)})]

# Write batch files
hfss_batch = HfssBatch(hfss_exports, path=dir_path, import_script_path=import_script_path, exit_after_run=True)
hfss_batch.write_oas()
hfss_batch.write_batch()

subprocess.call(str(hfss_batch.oas_filename), shell=True)
# subprocess.call(str(hfss_export.gds_filename), shell=True)
