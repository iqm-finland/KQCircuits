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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).

import sys
import logging

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.simulation_export import export_simulation_oas, sweep_simulation
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.waveguides_sim import WaveGuidesSim
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout, \
    open_with_klayout_or_default_application


# This testcase is the first proof of concept for Gmsh.
# There are equal length parallel waveguides with open termination build with KQC.
# There is also a possibility to produce wave guides with so called wave ports
# (set edge_ports True).
# The quides are at the top face of a flip chip type structure.
# The number of guides and length can be altered.
#
# The model mesh and physics definitions added using Gmsh. The mesh is exported to Elmer format
# and a sanity check is done by running an Elmer model that computes the electrostatic model
# and capacitance matrix. The outcome of the simulation can be visualized in Paraview that
# is launched after the simulation at the simulation path directory. The Paraview data for
# visual results is in "simulation" folder.
#
# The mesh is shown in Gmsh before the model export if mesh_parameters['show']. For large meshes
# it is better to not view the mesh in Gmsh but in Paraview together with the results.
#
# Simulation parameters
sim_class = WaveGuidesSim  # pylint: disable=invalid-name

edge_ports = True
use_elmer = True
use_sbatch = False
wave_equation = False
multiface = True
sweep_parameters = {
    'n_guides': range(1, 3)
}

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

if edge_ports:
    box_size_x = 100
    box_size_y = 1000
else:
    box_size_x = 1000
    box_size_y = 1000

sim_parameters = {
    'name': 'waveguides',
    'use_internal_ports': True,
    'use_edge_ports': edge_ports,
    'port_termination_end': False,
    'use_ports': True,
    'box': pya.DBox(pya.DPoint(-box_size_x/2., -box_size_y/2.), pya.DPoint(box_size_x/2., box_size_y/2.)),
    'cpw_length': 100,  # if edge_ports then this has to be box_size_x
    'a': 10,
    'b': 6,
    'add_bumps': False,
    'wafer_stack_type': "multiface" if multiface else "planar",
    'n_guides': 1,
    'chip_distance': 8,
    'port_size': 50,
    'permittivity': 11.45
}

if use_elmer:
    elmer_n_processes = -1
    mesh_parameters = {
        'default_mesh_size': 100.,
        'gap_min_mesh_size': 2.,
        'gap_min_dist': 4.,
        'gap_max_dist': 200.,
        'port_min_mesh_size': 1.,
        'port_min_dist': 4.,
        'port_max_dist': 200.,
        'algorithm': 5,
        'gmsh_n_threads': -1,  # <---------- This defines the number of processes in the
                               #             second level of parallelization. -1 uses all
                               #             the physical cores (based on the machine which
                               #             was used to prepare the simulation).
        'show': True,  # For GMSH: if true, the mesh is shown after it is done
                       # (for large meshes this can take a long time)
    }

    if wave_equation:
        elmer_n_processes = 1 # multi-core coming soon
        export_parameters_elmer = {
            'path': path,
            'tool': 'wave_equation',
            'frequency': 10,
        }
    else:
        elmer_n_processes = -1
        export_parameters_elmer = {
            'path': path,
            'tool': 'capacitance',
        }

    workflow = {
        'run_elmergrid': True,
        'run_elmer': True,
        'run_paraview': True,  # this is visual view of the results
                               # which can be removed to speed up the process
        'python_executable': 'python', # use 'kqclib' when using singularity
                                       # image (you can also put a full path)
        'elmer_n_processes': elmer_n_processes,  # <------ This defines the number of
                                                 #         processes in the second level
                                                 #         of parallelization. -1 uses all
                                                 #         the physical cores (based on
                                                 #         the machine which was used to
                                                 #         prepare the simulation)
        'n_workers': 2, # <--------- This defines the number of
                        #            parallel independent processes.
                        #            Moreover, adding this line activates
                        #            the use of the simple workload manager.
    }
    if use_sbatch:  # if simulation is run in a HPC system, sbatch_parameters can be given here
        workflow['sbatch_parameters'] = {
            '--job-name':sim_parameters['name'],
            '--account':'project_0',
            '--partition':'test',
            '--time':'00:10:00',
            '--ntasks':'40',
            '--cpus-per-task':'1',
            '--mem-per-cpu':'4000',
        }

else:
    if wave_equation:
        export_parameters_ansys = {
            'path': path,
            'frequency': [5, 10, 20],
            'max_delta_s': 0.001,
            'sweep_start': 0,
            'sweep_end': 30,
            'sweep_count': 1001,
            'maximum_passes': 20,
            'exit_after_run': True
        }
    else:
        export_parameters_ansys = {
            'path': path,
            'ansys_tool': 'q3d',
            'percent_error': 0.2,
            'minimum_converged_passes': 2,
            'maximum_passes': 40,
            'exit_after_run': True,
        }


# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

simulations = sweep_simulation(layout, sim_class, sim_parameters, sweep_parameters)

# Create simulation
open_with_klayout_or_default_application(export_simulation_oas(simulations, path))

if use_elmer:
    export_elmer(simulations, **export_parameters_elmer, gmsh_params=mesh_parameters, workflow=workflow)
else:
    export_ansys(simulations, **export_parameters_ansys)
