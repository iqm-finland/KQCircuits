# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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

from kqcircuits.elements.spiral_capacitor import SpiralCapacitor
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.cross_section.epr_correction_export import get_epr_correction_simulations

from kqcircuits.simulations.epr.spiral_capacitor import partition_regions, correction_cuts
from kqcircuits.simulations.export.elmer.elmer_solution import ElmerEPR3DSolution
from kqcircuits.simulations.export.elmer.mesh_size_helpers import refine_metal_edges
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.simulation_export import export_simulation_oas, cross_combine
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)

use_xsection = True

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
SimClass = get_single_element_sim_class(
    SpiralCapacitor,
    partition_region_function=partition_regions,
)
sim_parameters = {
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(600, 600)),
    "tls_sheet_approximation": True,
    "detach_tls_sheets_from_body": False,  # elmer knows how to use the non-detached surfaces
    "n": 48,
    "ground_gap": 10,
    "face_stack": ["1t1", "2b1"],
    "chip_distance": 8,
    "metal_height": [0.2, 0.2],
    "a": 3,
    "b": 8,
    "use_internal_ports": True,
}

sweep = [
    {"spiral_angle": 901.775, "finger_width": 5, "finger_gap": 2.5},
    {"spiral_angle": 618.206, "finger_width": 10, "finger_gap": 2.5},
    {"spiral_angle": 491.361, "finger_width": 15, "finger_gap": 2.5},
    {"spiral_angle": 412.482, "finger_width": 20, "finger_gap": 2.5},
    {"spiral_angle": 913.559, "finger_width": 5, "finger_gap": 5.0},
    {"spiral_angle": 655.023, "finger_width": 10, "finger_gap": 5.0},
    {"spiral_angle": 533.178, "finger_width": 15, "finger_gap": 5.0},
    {"spiral_angle": 446.403, "finger_width": 20, "finger_gap": 5.0},
    {"spiral_angle": 904.242, "finger_width": 5, "finger_gap": 7.5},
    {"spiral_angle": 669.373, "finger_width": 10, "finger_gap": 7.5},
    {"spiral_angle": 550.579, "finger_width": 15, "finger_gap": 7.5},
    {"spiral_angle": 465.815, "finger_width": 20, "finger_gap": 7.5},
]

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Sweep solution type
simulations = cross_combine(
    [SimClass(layout, **sim_parameters, **s, name=f"spiral_capacitor_{i}") for i, s in enumerate(sweep)],
    ElmerEPR3DSolution(
        mesh_size=refine_metal_edges(2.0, ignore_region="waveguides"),
        linear_system_method="mg",
    ),
)

workflow = {
    "run_gmsh_gui": False,
    "run_elmergrid": True,
    "run_elmer": True,
    "run_paraview": False,
    "python_executable": "python",
    "gmsh_n_threads": -1,  #  Number of omp threads in gmsh
    "elmer_n_processes": -1,  # Number of dependent processes (tasks) in elmer
    "elmer_n_threads": 1,  # Number of omp threads per process in elmer
}

# Export simulation files
export_elmer(
    simulations,
    path=dir_path,
    workflow=workflow,
    post_process=[
        PostProcess("produce_cmatrix_table.py"),
        (PostProcess("epr.sh", command="sh", folder="") if use_xsection else PostProcess("produce_epr_table.py")),
    ],
)

# produce EPR correction simulations
if use_xsection:
    correction_simulations, post_process = get_epr_correction_simulations(
        simulations, correction_cuts, metal_height=0.2
    )
    export_elmer(
        correction_simulations,
        dir_path,
        file_prefix="epr",
        post_process=post_process,
    )

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
if use_xsection:
    open_with_klayout_or_default_application(export_simulation_oas(correction_simulations, dir_path, "epr"))
