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
from kqcircuits.elements.circular_capacitor import CircularCapacitor
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class
from kqcircuits.simulations.export.simulation_export import export_simulation_oas, cross_combine
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.cross_section.cross_section_export import (
    create_cross_sections_from_simulations,
    visualise_cross_section_cut_on_original_layout,
)
from kqcircuits.simulations.export.elmer.elmer_solution import ElmerCapacitanceSolution, ElmerCrossSectionSolution


sim_class = get_single_element_sim_class(
    CircularCapacitor,
    # Mapping from port refpoint names to the cross-section simulation names (suffixes) used to deembed the waveguides
    # related to the ports
    deembed_cross_sections={"port_a": "port_a", "port_b": "port_b"},
)  # pylint: disable=invalid-name


flip_chip = False
etch_opposite_face = False
var_str = ("_f" if flip_chip else "") + ("e" if etch_opposite_face else "")

# Simulation parameters
sim_parameters = {
    "name": "circular_capacitor" + var_str,
    "use_internal_ports": False,
    "use_ports": True,
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(600, 600)),
    "port_size": 200,
    "face_stack": ["1t1", "2b1"] if flip_chip else ["1t1"],
    "etch_opposite_face": etch_opposite_face,
    "chip_distance": 8,
    "ground_gap": 20,
    "waveguide_length": 100,
    "r_inner": 30,
    "r_outer": 120,
    "swept_angle": 180,
    "outer_island_width": 40,
    "a": 10,
    "b": 6,
    "a2": 4,
    "b2": 10,
    "n": 64,
}

solution = ElmerCapacitanceSolution(
    mesh_size={
        "1t1_gap&1t1_signal_1": [2.0, 2.0, 0.5],
        "1t1_gap&1t1_signal_2": [2.0, 2.0, 0.5],
        "1t1_gap&1t1_ground": [2.0, 2.0, 0.5],
        "2b1_gap&2b1_ground": [2.0, 2.0, 0.5],
        "optimize": {},
    },
    linear_system_method="mg",
)

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + var_str + "_output")

# Get layout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
layout = get_active_or_new_layout()

simulations = [sim_class(layout, **sim_parameters)]

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

# Run 2D simulations as a post-processing step for the 3D simulations
# As a final step tabulate Cmatrix data including the deembedding
pp3d = PostProcess("cross_sections.sh", command="sh", folder="")
pp2d = PostProcess("produce_cmatrix_table.py")

# Export 3D simulations
export_elmer(cross_combine(simulations, solution), path=dir_path, workflow=workflow, post_process=pp3d)


# Create cross-sections
box_x, box_y = sim_parameters["box"].width(), sim_parameters["box"].height()
cuts = [
    (pya.DPoint(1, box_y / 2 - 100), pya.DPoint(1, box_y / 2 + 100)),
    (pya.DPoint(box_x - 1, box_y / 2 - 100), pya.DPoint(box_x - 1, box_y / 2 + 100)),
]

cross_sections = create_cross_sections_from_simulations(
    simulations,
    cuts,
    sim_names=[f"{sim_parameters['name']}_port_{port}" for port in ["a", "b"]],
    ma_permittivity=8.0,
    ms_permittivity=11.4,
    sa_permittivity=4.0,
    ma_thickness=0.0048,
    ms_thickness=0.0003,
    sa_thickness=0.0024,
    magnification_order=3,
)

visualise_cross_section_cut_on_original_layout(simulations, cuts)

solution2d = ElmerCrossSectionSolution(run_inductance_sim=False, mesh_size={"ma_layer&ms_layer": [0.5e-3, 0.5e-3, 0.2]})

# Run cross-section simulations in parallel, each with a single task
workflow.update(
    {
        "elmer_n_processes": 1,
        "gmsh_n_threads": 1,
        "n_workers": -1,
    }
)

# Export 2D simulations
export_elmer(
    cross_combine(cross_sections, solution2d),
    dir_path,
    file_prefix="cross_sections",
    workflow=workflow,
    post_process=pp2d,
)

open_with_klayout_or_default_application(export_simulation_oas(cross_sections, dir_path, "cross_sections"))
# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
