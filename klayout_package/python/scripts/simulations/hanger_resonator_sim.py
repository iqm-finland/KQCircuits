# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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
import argparse
from pathlib import Path

from kqcircuits.elements.hanger_resonator import HangerResonator
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.elmer.mesh_size_helpers import refine_metal_edges
from kqcircuits.simulations.export.simulation_export import export_simulation_oas
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)

import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--use-sbatch", action="store_true", help="Use sbatch (Slurm)")
args, unknown = parser.parse_known_args()

# Simulation parameters
coupling_length = 500.0
head_length = 500.0
# If resonator ports are used the real length of the resonator will be `resonator_length` + 200um
resonator_length = 6000.0
turn_radius = 50

box_size_x = coupling_length + 2 * turn_radius + 2000
box_y1 = -max(head_length, resonator_length - coupling_length - head_length) - 1000.0
box_y2 = 1000.0

sim_class = get_single_element_sim_class(
    HangerResonator,
    transformation_from_center=lambda cell: pya.DTrans(0, False, -coupling_length / 2.0, -(box_y1 + box_y2) / 2.0),
    # To make the simulation faster the resonator ports are ignored.
    # Remove to get the full 4x4 S-matrix
    ignore_ports=["port_resonator_a", "port_resonator_b"],
)

sim_parameters = {
    "name": "hanger_resonator_sim",
    "box": pya.DBox(
        pya.DPoint(-box_size_x / 2.0 + coupling_length / 2.0, box_y1),
        pya.DPoint(box_size_x / 2.0 + coupling_length / 2.0, box_y2),
    ),
    "coupling_length": coupling_length,
    "head_length": head_length,
    "resonator_length": resonator_length,
    "r": turn_radius,
    "res_a": 10,
    "res_b": 6,
    "a": 10,
    "b": 6,
    "ground_width": 10,
}

use_elmer = True
wave_equation = True
interpolating_sweep = True
use_sbatch = args.use_sbatch

if use_elmer:
    if wave_equation:
        path = create_or_empty_tmp_directory(Path(__file__).stem + "_elmer_wave")
    else:
        path = create_or_empty_tmp_directory(Path(__file__).stem + "_elmer")

else:
    if wave_equation:
        path = create_or_empty_tmp_directory(Path(__file__).stem + "_hfss")
    else:
        path = create_or_empty_tmp_directory(Path(__file__).stem + "_q3d")


if use_elmer:
    mesh_size = refine_metal_edges(5.0)

    if wave_equation:
        if interpolating_sweep:
            interp_freq = np.linspace(5, 15, 1001)
            export_parameters_elmer = {
                "path": path,
                "tool": "wave_equation",
                "frequency": [min(interp_freq), max(interp_freq)],
                "sweep_type": "interpolating",
                "max_delta_s": 1e-6,
                "frequency_batch": 3,
                "post_process": PostProcess("interpolate_s_parameters.py", frequencies=interp_freq.tolist()),
            }
        else:
            export_parameters_elmer = {
                "path": path,
                "tool": "wave_equation",
                "frequency": np.linspace(5, 15, 5),
                "sweep_type": "explicit",
            }
    else:
        export_parameters_elmer = {
            "path": path,
            "tool": "capacitance",
            "linear_system_method": "mg",
            "p_element_order": 3,
        }

    # fmt: off
    workflow = {
        'run_gmsh_gui': False,  # For GMSH: if true, the mesh is shown after it is done
                               # (for large meshes this can take a long time)
        'run_elmergrid': True,
        'run_elmer': True,
        'run_paraview': False,  # this is visual view of the results
                               # which can be removed to speed up the process
        'python_executable': 'python', # use 'kqclib' when using singularity
                                       # image (you can also put a full path)
        'gmsh_n_threads': -1,  # <---------- This defines the number of processes in the
                               #             second level of parallelization. -1 uses all
                               #             the physical cores (based on the machine which
                               #             was used to prepare the simulation).
        'elmer_n_processes': 3,  # <------ This defines the number of
                                                 #         processes in the second level
                                                 #         of parallelization. -1 uses all
                                                 #         the physical cores (based on
                                                 #         the machine which was used to
                                                 #         prepare the simulation)
        'elmer_n_threads': 1,  # <------ This defines the number of omp threads per process
        'n_workers': 3,              # <--------- This defines the number of
                                      #            parallel independent processes.
                                      #            Setting this larger than 1 activates
                                      #            the use of the simple workload manager.
    }
    if use_sbatch:
        # if simulation is run in a HPC system, sbatch_parameters can be given here
        # The values given here are all per simulation (except n_workers)
        # and the real allocation size is calculated and requested automatically.

        # If a job submission fails with "sbatch: error: Batch job submission failed: "it is most probably
        # due to reserving too much memory per node or exceeding partitions time limit.
        # You might need to check the remote for the limits and adjust these settings to fit the restrictions
        workflow['sbatch_parameters'] = {


            '--account':'project_0',    # <-- Remote account for billing
            '--partition':'test',       # <-- Slurm partition used, options depend on the remote
            'n_workers': 3,             # <-- Number of parallel simulations, the total amount of resources requested
                                        #     is `n_workers` times the definitions below for single simulation
            'max_threads_per_node': 40, # <-- Max number of tasks allowed on a node. dependent on the used remote host
                                        #     Automatically divides the tasks to as few nodes as possible
            'elmer_n_processes':10,     # <-- Number of tasks per simulation
            'elmer_n_threads':1,        # <-- Number of threads per task
            'elmer_mem':'32G',          # <-- Amount of memory per simulation
            'elmer_time':'00:05:00',    # <-- Maximum time per simulation

            'gmsh_n_threads':10,        # <-- Threads per simulation
            'gmsh_mem':'32G',           # <-- Allocated memory per simulation
            'gmsh_time':'00:10:00',     # <-- Maximum time per simulation
        }
    # fmt: on

else:
    if wave_equation:
        export_parameters_ansys = {
            "path": path,
            "frequency": [8, 10, 12],
            "max_delta_s": 0.001,
            "sweep_start": 0,
            "sweep_end": 30,
            "sweep_count": 1001,
            "maximum_passes": 20,
            "exit_after_run": True,
            "mesh_size": {"1t1_gap": 5},
        }
    else:
        export_parameters_ansys = {
            "path": path,
            "ansys_tool": "q3d",
            "post_process": PostProcess("produce_cmatrix_table.py"),
            "percent_error": 0.2,
            "minimum_converged_passes": 2,
            "maximum_passes": 40,
            "exit_after_run": True,
        }
# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

simulations = [sim_class(layout, **sim_parameters)]

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, path))

if use_elmer:
    export_elmer(simulations, **export_parameters_elmer, mesh_size=mesh_size, workflow=workflow)
else:
    export_ansys(simulations, **export_parameters_ansys)
