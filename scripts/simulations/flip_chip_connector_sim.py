# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
import sys
import logging
from pathlib import Path
import subprocess

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import export_simulation_oas, sweep_simulation
from kqcircuits.simulations.flip_chip_connector_sim import FlipChipConnectorSim
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
sim_class = FlipChipConnectorSim
sim_parameters = {
    'name': 'flip_chip',
    'use_internal_ports': False,
    'use_ports': True,
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(600, 500)),
    'waveguide_length': 100,
    'r': 10,
    'a': 10,
    'b': 10,
    'port_width': 200,
    'wafer_stack_type': "multiface"
}
export_parameters = {
    'path': dir_path,
    'frequency': [5, 10, 20],
    'max_delta_s': 0.001,
    'sweep_start': 0,
    'sweep_end': 30,
    'sweep_count': 1001,
    'maximum_passes': 20,
    'exit_after_run': True
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Sweep simulations
simulations = sweep_simulation(layout, sim_class, sim_parameters, {
    'chip_distance': [2, 3, 4, 5, 6, 7, 8, 9, 10]
})

# Export Ansys files
export_ansys(simulations, **export_parameters)

# Write and open oas file
subprocess.call(export_simulation_oas(simulations, dir_path), shell=True)
