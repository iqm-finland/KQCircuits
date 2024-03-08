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

import numpy as np

from kqcircuits.pya_resolver import pya
from kqcircuits.qubits.swissmon import Swissmon
from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import cross_sweep_simulation, export_simulation_oas
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)


# Simulation parameters
sim_class = get_single_element_sim_class(Swissmon)  # pylint: disable=invalid-name
sim_parameters = {
    "name": "single_xmon_sim",
    "use_internal_ports": True,
    "use_ports": True,
    "face_stack": ["1t1", "2b1"],
    "chip_distance": 5.5,
    "face_ids": ["2b1", "1t1"],
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(3000, 3000)),
}

dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

export_parameters = {
    "path": dir_path,
    "exit_after_run": True,
    "mesh_size": {face_id + "_gap": 20 for face_id in ["1t1", "2b1"]},  # converges fast
    "ansys_tool": "eigenmode",
    "max_delta_f": 0.5,
    "maximum_passes": 2,
    "minimum_passes": 1,
    "minimum_converged_passes": 1,
    "n_modes": 2,
    "min_frequency": 0.5,  # minimum allowed frequency
}


# Get layout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
layout = get_active_or_new_layout()

# Sweep simulations
simulations = [sim_class(layout, **sim_parameters)]

# No need to filter simulations according to ones that can be generated,
# as in the end we will use `skip_errors=True` to skip these in `export_ansys`.
# Here, the negative radii don't make sense, but we can still export the rest
# of the simulations.
simulations += cross_sweep_simulation(layout, sim_class, sim_parameters, {"island_r": np.linspace(-100, 100, 6)})


export_ansys(simulations, **export_parameters, skip_errors=True)

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
