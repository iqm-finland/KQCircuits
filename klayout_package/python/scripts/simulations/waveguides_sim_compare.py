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
import argparse

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.simulation_export import export_simulation_oas, sweep_simulation
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.simulations.waveguides_sim import WaveGuidesSim
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)


# This testcase is the first proof of concept for Gmsh.
# There are equal length parallel waveguides with open termination build with KQC.
# There is also a possibility to produce wave guides with so called wave ports
# (set edge_ports True).
# The guides are at the top face of a flip chip type structure.
# The number of guides and length can be altered.
#
# The model mesh and physics definitions added using Gmsh. The mesh is exported to Elmer format
# and a sanity check is done by running an Elmer model that computes the electrostatic model
# and capacitance matrix. The outcome of the simulation can be visualized in Paraview that
# is launched after the simulation at the simulation path directory. The Paraview data for
# visual results is in "simulation" folder.
#
# The mesh is shown in Gmsh before the model export if workflow['run_gmsh_gui']. For large meshes
# it is better to not view the mesh in Gmsh but in Paraview together with the results.
#
# Simulation parameters
parser = argparse.ArgumentParser()

parser.add_argument("--no-edge-ports", action="store_true", help="Do not use edge_ports")
parser.add_argument("--flip-chip", action="store_true", help="Make a flip chip")
parser.add_argument("--ansys", action="store_true", help="Use Ansys (otherwise Elmer)")
parser.add_argument("--use-sbatch", action="store_true", help="Use sbatch (Slurm)")
parser.add_argument("--adaptive-remeshing", action="store_true", help="Use adaptive remeshing")
parser.add_argument("--port-termination", action="store_true", help="Port termination")
parser.add_argument("--wave-equation", action="store_true", help="Compute wave equation (otherwise electrostatics)")
parser.add_argument(
    "--n-guides-range",
    nargs=2,
    default=[1, 2],
    type=int,
    help="number of guides in first case and last \
        simulation: all the cases in between with an increment of one \
        will be simulated as well",
)
parser.add_argument("--cpw-length", default=100.0, type=float, help="Length of cpws in the model")
parser.add_argument("--p-element-order", default=3, type=int, help="Order of p-elements in the FEM computation")
parser.add_argument(
    "--elmer-n-processes",
    default=-1,
    type=int,
    help="Number of processes in Elmer simulations, -1 means all physical cores",
)
parser.add_argument("--elmer-n-threads", default=1, type=int, help="Number of threads per process in Elmer simulations")
parser.add_argument(
    "--gmsh-n-threads",
    default=-1,
    type=int,
    help="Number of threads in Gmsh simulations, \
        -1 means all physical cores",
)

parser.add_argument("--port-mesh-size", default=1.0, type=float, help="Element size at ports")
parser.add_argument("--gap-mesh-size", default=2.0, type=float, help="Element size at gaps")
parser.add_argument("--global-mesh-size", default=100.0, type=float, help="Global element size")
args, unknown = parser.parse_known_args()

sim_class = WaveGuidesSim  # pylint: disable=invalid-name

edge_ports = not args.no_edge_ports
use_elmer = not args.ansys
use_sbatch = args.use_sbatch
wave_equation = args.wave_equation
flip_chip = args.flip_chip
sweep_parameters = {"n_guides": range(args.n_guides_range[0], args.n_guides_range[1] + 1)}

cpw_length = args.cpw_length

if edge_ports:
    box_size_x = cpw_length
    box_size_y = 1000
    cpw_length = box_size_x
else:
    box_size_x = 1000
    box_size_y = 1000

if use_elmer:
    if wave_equation:
        path = create_or_empty_tmp_directory("waveguides_sim_elmer_wave")
    else:
        path = create_or_empty_tmp_directory("waveguides_sim_elmer")

else:
    if wave_equation:
        path = create_or_empty_tmp_directory("waveguides_sim_hfss")
    else:
        path = create_or_empty_tmp_directory("waveguides_sim_q3d")

sim_parameters = {
    "name": "waveguides",
    "use_internal_ports": True,
    "use_edge_ports": edge_ports,
    "port_termination_end": args.port_termination,
    "use_ports": True,
    "box": pya.DBox(pya.DPoint(-box_size_x / 2.0, -box_size_y / 2.0), pya.DPoint(box_size_x / 2.0, box_size_y / 2.0)),
    "cpw_length": cpw_length,  # if edge_ports then this has to be box_size_x
    "a": 10,
    "b": 6,
    "add_bumps": False,
    "face_stack": ["1t1", "2b1"] if flip_chip else ["1t1"],
    "n_guides": 1,
    "chip_distance": 8,
    "port_size": 50,
}

if use_elmer:
    elmer_n_processes = args.elmer_n_processes
    elmer_n_threads = args.elmer_n_threads
    mesh_size = {
        "global_max": args.global_mesh_size,
        "1t1_gap": args.gap_mesh_size,
        **{f"port_{i+1}": args.port_mesh_size for i in range(args.n_guides_range[1])},
    }

    if wave_equation:
        export_parameters_elmer = {
            "path": path,
            "tool": "wave_equation",
            "frequency": 10,
        }
    else:
        export_parameters_elmer = {
            "path": path,
            "tool": "capacitance",
            "linear_system_method": "mg",
            "p_element_order": args.p_element_order,
            "post_process": PostProcess("produce_cmatrix_table.py"),
        }
        if args.adaptive_remeshing:
            export_parameters_elmer.update(
                {
                    "percent_error": 0.001,
                    "max_error_scale": 2,  # allow outlier where error is 2*0.005
                    "max_outlier_fraction": 1e-3,  # allow 0.1% of outliers
                    "maximum_passes": 3,
                    "minimum_passes": 2,
                }
            )

    # fmt: off
    workflow = {
        'run_gmsh_gui': True,  # For GMSH: if true, the mesh is shown after it is done
                               # (for large meshes this can take a long time)
        'run_elmergrid': True,
        'run_elmer': True,
        'run_paraview': True,  # this is visual view of the results
                               # which can be removed to speed up the process
        'python_executable': 'python', # use 'kqclib' when using singularity
                                       # image (you can also put a full path)
        'gmsh_n_threads': args.gmsh_n_threads,  # <---------- This defines the number of processes in the
                               #             second level of parallelization. -1 uses all
                               #             the physical cores (based on the machine which
                               #             was used to prepare the simulation).
        'elmer_n_processes': elmer_n_processes,  # <------ This defines the number of
                                                 #         processes in the second level
                                                 #         of parallelization. -1 uses all
                                                 #         the physical cores (based on
                                                 #         the machine which was used to
                                                 #         prepare the simulation)
        'elmer_n_threads': elmer_n_threads,  # <------ This defines the number of omp threads per task
        'n_workers': 1,               # <--------- This defines the number of
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
            'n_workers': 2,             # <-- Number of parallel simulations, the total amount of resources requested
                                        #     is `n_workers` times the definitions below for single simulation
            'max_threads_per_node': 40, # <-- Max number of tasks allowed on a node. dependent on the used remote host
                                        #     Automatically divides the tasks to as few nodes as possible
            'elmer_n_processes':10,     # <-- Number of tasks per simulation
            'elmer_n_threads':1,        # <-- Number of threads per task
            'elmer_mem':'32G',          # <-- Amount of memory per simulation
            'elmer_time':'00:05:00',    # <-- Maximum time per simulation

            'gmsh_n_threads':10,        # <-- Threads per simulation
            'gmsh_mem':'32G',           # <-- Allocated memory per simulation
            'gmsh_time':'00:05:00',     # <-- Maximum time per simulation
        }
    # fmt: on

else:
    if wave_equation:
        export_parameters_ansys = {
            "path": path,
            "frequency": [5, 10, 20],
            "max_delta_s": 0.001,
            "sweep_start": 0,
            "sweep_end": 30,
            "sweep_count": 1001,
            "maximum_passes": 20,
            "exit_after_run": True,
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

simulations = sweep_simulation(layout, sim_class, sim_parameters, sweep_parameters)

# Create simulation
open_with_klayout_or_default_application(export_simulation_oas(simulations, path))

if use_elmer:
    export_elmer(simulations, **export_parameters_elmer, mesh_size=mesh_size, workflow=workflow)
else:
    export_ansys(simulations, **export_parameters_ansys)
