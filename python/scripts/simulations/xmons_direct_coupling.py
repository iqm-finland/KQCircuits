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
sim_class = XMonsDirectCouplingSim  # pylint: disable=invalid-name
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
