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

import logging
import sys
from pathlib import Path

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import sweep_simulation, export_simulation_oas

from kqcircuits.simulations.xmons_direct_coupling_sim import XMonsDirectCouplingSim
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
sim_class = XMonsDirectCouplingSim  # pylint: disable=invalid-name
sim_parameters = {
    "name": "three_coupled_xmons",
    "use_internal_ports": True,
    "box": pya.DBox(pya.DPoint(3500, 3500), pya.DPoint(6500, 6500)),
}

export_parameters = {
    "path": dir_path,
    "ansys_tool": "eigenmode",
    "percent_refinement": 30,
    "maximum_passes": 17,
    "minimum_passes": 1,
    "minimum_converged_passes": 2,
    "exit_after_run": True,
    "max_delta_f": 0.1,  # maximum relative difference for convergence in %
    "n_modes": 2,  # eigenmodes to solve
    "min_frequency": 0.1,  # minimum allowed eigenmode frequency
    "simulation_flags": ["pyepr"],  # required for setting up pyepr specific stuff
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Nominal simulation
simulations = [sim_class(layout, **sim_parameters)]

# Sweep geometry for simulations
simulations += sweep_simulation(layout, sim_class, sim_parameters, {"qubit_spacing": [5, 15], "cpl_width": [12]})

# Export Ansys files
export_ansys(simulations, **export_parameters)

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
