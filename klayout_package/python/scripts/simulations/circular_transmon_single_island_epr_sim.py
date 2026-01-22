# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
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
from kqcircuits.qubits.circular_transmon_single_island import CircularTransmonSingleIsland
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class
from kqcircuits.simulations.export.simulation_export import export_simulation_oas, cross_combine
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.cross_section.epr_correction_export import get_epr_correction_simulations
from kqcircuits.simulations.export.elmer.elmer_solution import ElmerEPR3DSolution
from kqcircuits.simulations.epr.circular_transmon_single_island import partition_regions, correction_cuts
from kqcircuits.simulations.export.elmer.mesh_size_helpers import refine_metal_edges

SimClass = get_single_element_sim_class(
    CircularTransmonSingleIsland,
    partition_region_function=partition_regions,
    # Ignoring coupler ports, which means they cannot be excited for these simulations, and they don't get waveguides
    # drawn leading to them.
    ignore_ports=[f"port_coupler_{i}" for i in range(10)],
)

# Simulation parameters
sim_parameters = {
    "name": "circular_transmon_single_island_epr",
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(1000, 1000)),
    "n": 64,  # decrease n to speed up simulation
    "tls_sheet_approximation": True,
    "metal_height": [0.2],  # Required for the TLS sheets to be generated
    "detach_tls_sheets_from_body": False,
}


solution = ElmerEPR3DSolution(
    mesh_size=refine_metal_edges(3.0, 0.5),
    mesh_optimizer={},
)

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Get layout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
layout = get_active_or_new_layout()

simulations = [SimClass(layout, **sim_parameters)]

# Uncomment below if you want to try sweeping qubit geometry.
# Cross-varies three ground gap widths and three coupler arc lengths.
# Prepare for a long simulation time if you enable this.

# simulations = cross_sweep_simulation(
#     layout,
#     SimClass,
#     sim_parameters,
#     {"ground_gap": [80, 120, 160], "couplers_arc_amplitude": [[15, 45, 15], [35, 45, 15], [45, 45, 15]]},
# )

simulations = cross_combine(simulations, solution)

workflow_3d = {
    "run_gmsh_gui": True,
    "run_elmergrid": True,
    "run_elmer": True,
    "run_paraview": True,
    "python_executable": "python",
    "gmsh_n_threads": -1,  #  Number of omp threads in gmsh
    "elmer_n_processes": -1,  # Number of dependent processes (tasks) in elmer
    "elmer_n_threads": 1,  # Number of omp threads per process in elmer
}
workflow_2d = {
    **workflow_3d,
    "gmsh_n_threads": 1,
    "elmer_n_processes": 1,
    "n_workers": -1,
}

export_elmer(
    simulations,
    path=dir_path,
    workflow=workflow_3d,
    post_process=[PostProcess("epr", command=None, folder="")],
)

correction_simulations, post_process = get_epr_correction_simulations(simulations, correction_cuts)

export_elmer(
    correction_simulations,
    dir_path,
    file_prefix="epr",
    workflow=workflow_2d,
    post_process=post_process + [PostProcess("produce_cmatrix_table.py"), PostProcess("elmer_profiler.py")],
)

open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
open_with_klayout_or_default_application(export_simulation_oas(correction_simulations, dir_path, "epr"))
