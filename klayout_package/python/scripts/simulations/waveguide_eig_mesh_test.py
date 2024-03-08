# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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

import sys
import logging

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.simulation_export import export_simulation_oas
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.waveguides_sim import WaveGuidesSim
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)

# This is a test case for initial mesh refinement in Ansys

sim_class = WaveGuidesSim  # pylint: disable=invalid-name
path = create_or_empty_tmp_directory("waveguide_eig_mesh_test")

box_size_x = 6000
box_size_y = 1000

sim_parameters = {
    "name": "waveguides",
    "use_internal_ports": True,
    "use_edge_ports": False,
    "port_termination_end": False,
    "use_ports": True,
    "box": pya.DBox(pya.DPoint(-box_size_x / 2.0, -box_size_y / 2.0), pya.DPoint(box_size_x / 2.0, box_size_y / 2.0)),
    "cpw_length": 4000,  # if edge_ports then this has to be box_size_x
    "a": 10,
    "b": 6,
    "add_bumps": False,
    "face_stack": ["1t1"],
    "n_guides": 1,
    "port_size": 50,
}

export_parameters_ansys = {
    "path": path,
    "ansys_tool": "eigenmode",
    "maximum_passes": 2,
    "percent_refinement": 30,
    "mesh_size": {"1t1_gap": 4},
    "exit_after_run": True,
    "max_delta_f": 0.1,  # maximum relative difference for convergence in %
    "n_modes": 1,  # eigenmodes to solve
    "min_frequency": 10,  # minimum allowed eigenmode frequency
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

simulations = [sim_class(layout, **sim_parameters)]

# Create simulation
open_with_klayout_or_default_application(export_simulation_oas(simulations, path))

export_ansys(simulations, **export_parameters_ansys)
