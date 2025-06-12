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

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.circular_capacitor import CircularCapacitor
from kqcircuits.simulations.export.elmer.mesh_size_helpers import refine_metal_edges
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class
from kqcircuits.simulations.export.simulation_export import cross_sweep_simulation, export_simulation_oas, cross_combine
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.cross_section.epr_correction_export import get_epr_correction_simulations
from kqcircuits.simulations.export.elmer.elmer_solution import ElmerEPR3DSolution
from kqcircuits.simulations.epr.circular_capacitor import partition_regions, correction_cuts

sim_class = get_single_element_sim_class(
    CircularCapacitor,
    partition_region_function=partition_regions,
    deembed_cross_sections={"port_a": "port_amer", "port_b": "port_bmer"},
)  # pylint: disable=invalid-name

# Export for running on HPC cluster with SLURM
use_sbatch = False

flip_chip = False
etch_opposite_face = False
var_str = ("_f" if flip_chip else "") + ("e" if etch_opposite_face else "")

# By default the simulation excites all signals present sequentially.
# This keyword can be used to specify custom voltages on each signal instead
# If used, no capacitance will be produced
voltage_excitations = None  # [1.0, -0.5]

ground_gap = 20
# If False the waveguides connected to the element will extend to the boundary of
# simulation box
use_internal_ports = False
# Only applicable if use_internal_ports =True
# Choose whether a piece of waveguide is added to the ports or not
# Only a small ground "wire" is produced that is 10um separated from the island
include_waveguides = True

wg_len = -ground_gap if use_internal_ports and not include_waveguides else 100

# Simulation parameters
sim_parameters = {
    "name": "circular_capacitor_epr" + var_str,
    "use_internal_ports": use_internal_ports,
    "use_ports": True,
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(600, 600)),
    "port_size": 200,
    "face_stack": ["1t1", "2b1"] if flip_chip else ["1t1"],
    "etch_opposite_face": etch_opposite_face,
    "chip_distance": 8,
    "ground_gap": ground_gap,
    "waveguide_length": wg_len,
    # This has the same effect as increasing the waveguide_length but parametrizes the total size of the element
    # "fixed_length": 500,
    "r_inner": 30,
    "r_outer": 120,
    "swept_angle": 180,
    "outer_island_width": 40,
    "a": 10,
    "b": 6,
    "a2": 10,
    "b2": 6,
    "tls_sheet_approximation": True,
    "metal_height": [0.2],  # Required for the TLS sheets to be generated
    "detach_tls_sheets_from_body": False,
    "n": 64,  # Rougher shapes make the meshing more efficient
    "vertical_over_etching": 0.050,  # Use a small vertical over etching (substrate trench)
}


solution = ElmerEPR3DSolution(
    mesh_size=refine_metal_edges(2.0, 0.5),
    mesh_optimizer={},
    linear_system_method="mg",
    voltage_excitations=voltage_excitations,
)

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + var_str + "_output")

# Get layout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
layout = get_active_or_new_layout()

# Cross sweep number of fingers and finger length
simulations = []
simulations += cross_sweep_simulation(
    layout,
    sim_class,
    sim_parameters,
    {
        "swept_angle": [30, 180, 300, 340, 350],
    },
)

pp = [PostProcess("elmer_profiler.py")]

if use_sbatch:
    # Simulation scripts are divided into 2 parts when run on remote and they need to be launched using source
    pp += [
        PostProcess("epr_meshes.sh", command="source", folder=""),
        PostProcess("epr.sh", command="source", folder=""),
    ]
else:
    pp += [PostProcess("epr.sh", command="sh", folder="")]

simulations = cross_combine(simulations, solution)

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

if use_sbatch:
    # see explanations of sbatch parameters in waveguides_sim_compare.py

    # The cross-sections are ran from the same allocation as the main simulation
    # so a bit extra time should be allocated to them
    workflow["sbatch_parameters"] = {
        "--account": "project_0",
        "--partition": "large",
        "n_workers": 5,
        # `max_threads_per_node` is reduced from 40 to 20 to only allocate half of the CPUs per node.
        #  Otherwise there would be either idle memory in the Gmsh phase or idle cores in the Elmer
        # phase as our requested doesnt match the available hardware
        "max_threads_per_node": 20,
        "elmer_n_processes": 4,
        "elmer_n_threads": 1,
        "elmer_mem": "32G",
        "elmer_time": "00:45:00",
        "gmsh_n_threads": 4,
        "gmsh_mem": "4G",
        "gmsh_time": "00:35:00",
    }

export_elmer(simulations, path=dir_path, workflow=workflow, post_process=pp)

correction_simulations, post_process = get_epr_correction_simulations(simulations, correction_cuts, metal_height=0.2)

# Run cross-section simulations in parallel, each with a single task
workflow.update(
    {
        "elmer_n_processes": 1,
        "gmsh_n_threads": 1,
        "n_workers": -1,
    }
)

if use_sbatch:
    # Even though the cross-sections are already fast we can speed them up by redistributing the
    # resources allocated for the main simulation. Though this is risky and needs to be manually adjusted
    # based on the above original sbatch_parameters
    workflow["sbatch_parameters"].update(
        {
            "gmsh_n_threads": 1,  # This is needed! other settings below are optional
            # original number of cores = 5*4=20.
            # original memory = 5*32GB = 160GB =>per new worker 160GB / 20 = 8GB (max)
            "n_workers": 20,
            "elmer_n_processes": 1,
            "elmer_mem": "8G",
        }
    )

export_elmer(
    correction_simulations,
    dir_path,
    file_prefix="epr",
    workflow=workflow,
    post_process=post_process + [PostProcess("produce_cmatrix_table.py")],
)
open_with_klayout_or_default_application(export_simulation_oas(correction_simulations, dir_path, "epr"))
# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
