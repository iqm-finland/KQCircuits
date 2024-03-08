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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

import logging
import sys
from pathlib import Path

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.circular_capacitor import CircularCapacitor
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import cross_sweep_simulation, export_simulation_oas
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

sim_class = get_single_element_sim_class(CircularCapacitor)  # pylint: disable=invalid-name

# Simulation parameters
sim_parameters = {
    "name": "circular_capacitor",
    "use_internal_ports": True,
    "use_ports": True,
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(1000, 1000)),
    "port_size": 200,
    "face_stack": ["1t1"],
    "corner_r": 2,
    "chip_distance": 8,
    "ground_gap": 20,
    "fixed_length": 0,
    "r_inner": 75,
    "r_outer": 120,
    "swept_angle": 180,
    "outer_island_width": 40,
    "a": 10,
    "b": 6,
}
export_parameters = {
    "path": dir_path,
    "ansys_tool": "q3d",
    "post_process": PostProcess("produce_cmatrix_table.py"),
    "exit_after_run": True,
    "percent_error": 0.3,
    "minimum_converged_passes": 2,
    "maximum_passes": 20,
}

# Sweep ranges
chip_distances = [4, 5, 6, 7, 8, 9, 10, 12, 14, 18, 22]
r_inner = [10, 75]
swept_angle = [10, 40, 70, 100, 130, 160, 180, 190, 220, 250, 280, 310, 340]
ab_single = [(10, 6), (5, 20), (4, 30)]
ab_multi = [(4.0, 2.5), (3.5, 32.0), (2.0, 32.0)]

# Get layout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
layout = get_active_or_new_layout()

# Cross sweep number of fingers and finger length
simulations = []

# Smaller geometry single face sweep
for ab in ab_single:
    simulations += cross_sweep_simulation(
        layout,
        sim_class,
        sim_parameters,
        {
            "r_inner": [10],
            "r_outer": [55],
            "outer_island_width": [20],
            "swept_angle": swept_angle,
            "a": [ab[0]],
            "a2": [ab[0]],
            "b": [ab[1]],
            "b2": [ab[1]],
        },
    )

# Single face sweep
for ab in ab_single:
    simulations += cross_sweep_simulation(
        layout,
        sim_class,
        sim_parameters,
        {
            "r_inner": r_inner,
            "swept_angle": swept_angle,
            "a": [ab[0]],
            "a2": [ab[0]],
            "b": [ab[1]],
            "b2": [ab[1]],
        },
    )

for ab in ab_multi:
    simulations += cross_sweep_simulation(
        layout,
        sim_class,
        {**sim_parameters, "face_stack": ["1t1", "2b1"]},
        {
            "chip_distance": chip_distances,
            "r_inner": r_inner,
            "swept_angle": swept_angle,
            "a": [ab[0]],
            "a2": [ab[0]],
            "b": [ab[1]],
            "b2": [ab[1]],
        },
    )


# simulations for getting the ballpark
# simulations += cross_sweep_simulation(layout, sim_class, sim_parameters, {
#     'r_inner': np.arange(10, 40+31, 5, dtype=int).tolist(),
#     'r_outer': np.arange(100-10, 100+11, 5, dtype=int).tolist(),
#     'swept_angle': [10, 180, 340],
# })

# Export Ansys files
export_ansys(simulations, **export_parameters)

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
