# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
import logging
import sys
from pathlib import Path
import subprocess

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import sweep_simulation, export_simulation_oas

from kqcircuits.simulations.xmons_direct_coupling_sim import XMonsDirectCouplingSim
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
sim_class = XMonsDirectCouplingSim
sim_parameters = {
    'name': 'three_coupled_xmons',
    "use_internal_ports": True,
    "box": pya.DBox(pya.DPoint(3500, 3500), pya.DPoint(6500, 6500))
}
export_parameters = {
    'path': dir_path,
    'frequency': 1,
    'exit_after_run': False
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Sweep simulations
simulations = sweep_simulation(layout, sim_class, sim_parameters, {
    #'waveguide_length': range(10, 510, 50),
    'cpl_width': [10]
})

# Export Ansys files
export_ansys(simulations, **export_parameters)

# Write and open oas file
subprocess.call(export_simulation_oas(simulations, dir_path), shell=True)
