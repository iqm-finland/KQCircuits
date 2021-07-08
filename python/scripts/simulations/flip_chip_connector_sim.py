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
sim_class = FlipChipConnectorSim  # pylint: disable=invalid-name
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
