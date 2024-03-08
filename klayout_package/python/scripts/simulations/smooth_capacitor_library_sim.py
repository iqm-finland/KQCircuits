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
from kqcircuits.elements.smooth_capacitor import SmoothCapacitor
from kqcircuits.pya_resolver import pya
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

sim_class = get_single_element_sim_class(SmoothCapacitor)  # pylint: disable=invalid-name

# Simulation parameters, using multiface interdigital as starting point
sim_parameters = {
    "name": "smooth_capacitor",
    "use_internal_ports": True,
    "use_ports": True,
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(1000, 1000)),
    "finger_control": 1,
    "finger_width": 10,
    "finger_gap": 5,
    "ground_gap": 10,
}
# Parameters that differ from sim_parameters for gap type
export_parameters = {
    "path": dir_path,
    "ansys_tool": "q3d",
    "post_process": PostProcess("produce_cmatrix_table.py"),
    "exit_after_run": True,
    "percent_error": 0.1,
    "minimum_converged_passes": 1,
    "maximum_passes": 20,
    "minimum_passes": 15,
}

infinite = 1e30
# Sweep ranges
finger_numbers = [round(v, 5) for v in np.linspace(0.2, 5, 49)]
chip_distances = [4, 5.5, 8, 16, infinite]
a_def = [10]
b_def = [6]

num = 4
finger_numbers_comp = [round((5 ** (1 / num)) ** i, 1) for i in range(-num, num + 1)]
chip_distances_comp = [4, 8, infinite]
as_comp = [2, 10, 20]
bs_comp = [2, 6, 18, 32]

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Cross sweep number of fingers
simulations = []

# Default sweep
simulations += cross_sweep_simulation(
    layout,
    sim_class,
    {**sim_parameters, "face_stack": ["1t1", "2b1"]},
    {
        "finger_control": finger_numbers,
        "chip_distance": [d for d in chip_distances if d != infinite],
        "a": a_def,
        "b": b_def,
        "a2": a_def,
        "b2": b_def,
    },
)
if infinite in chip_distances:
    simulations += cross_sweep_simulation(
        layout,
        sim_class,
        {**sim_parameters, "face_stack": ["1t1"], "chip_distance": infinite},
        {"finger_control": finger_numbers, "a": a_def, "b": b_def, "a2": a_def, "b2": b_def},
    )

# Compensation
for n in finger_numbers_comp:
    for d in chip_distances_comp:
        sim_params = {**sim_parameters, "face_stack": ["1t1"] if d == infinite else ["1t1", "2b1"]}
        for a in as_comp:
            for b in bs_comp:
                for a2 in as_comp:
                    for b2 in bs_comp:
                        if a in a_def and b in b_def and a2 in a_def and b2 in b_def:
                            continue  # do not create defaults again
                        if a + b > a2 + b2:
                            continue  # due to symmetry, we can skip almost half of the simulations
                        simulations += cross_sweep_simulation(
                            layout,
                            sim_class,
                            sim_params,
                            {"finger_control": [n], "chip_distance": [d], "a": [a], "b": [b], "a2": [a2], "b2": [b2]},
                        )

# Export Ansys files
export_ansys(simulations, **export_parameters)

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
