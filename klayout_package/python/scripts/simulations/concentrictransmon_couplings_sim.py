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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).

import logging
import sys
from pathlib import Path

import numpy as np

from kqcircuits.qubits.concentric_transmon import ConcentricTransmon
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.simulation_export import cross_sweep_simulation, export_simulation_oas, \
    sweep_simulation
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout, \
    open_with_klayout_or_default_application
from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
sim_class = get_single_element_sim_class(ConcentricTransmon)  # pylint: disable=invalid-name
sim_parameters = {
    # Arguments for the base Simulation class
    'name': 'concentrictransmon',
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(2000, 2000)),  # total area for simulation
    'use_ports': True,
    'use_internal_ports': True,  # wave ports are actually internal (lumped) ports instead of at the edge
    'separate_island_internal_ports': True,
    'waveguide_length': 100,  # wave port length before terminating with InternalPort in this case

    # Nominal qubit parameters for the inherited ConcentricTransmon
    'r_inner': 110,
    'r_outer': 280,
    'outer_island_width': 80,
    'ground_gap': 40,
    'squid_angle': 90,
    'drive_angle': 110,
    'couplers_r': 300,
    'couplers_a': [10],
    'couplers_b': [6],
    'couplers_angle': [225],
    'couplers_width': [10],
    'couplers_arc_amplitude': [35]
}


elmer_export_parameters = {
    'path': dir_path,
    'tool': 'capacitance',
    'workflow': {
        'run_gmsh_gui': False,  # open gmsh gui after meshing
        'run_elmergrid': True,
        'run_elmer': True,
        'run_paraview': False,  # opens results in ParaView after finishing
        'n_workers': 1,  # workers for first-level parallelisation
        'gmsh_n_threads': 4,  # -1 means all the physical cores
        'elmer_n_processes': 4,  # processes for second-level parallelisation
        'elmer_n_threads': 1,  # the number of omp threads per process
        'python_executable': 'python' # use 'kqclib' when using singularity image (you can also put a full path)
    },
    'linear_system_method': 'mg',  # Multigrid solver in Elmer, details in Elmer docs
    'p_element_order': 2,  # Polynomial order of FEM basis functions, computationally more expensive but more accurate.
    'mesh_size': {  # check implementation of `export_gmsh_msh` for detais. Employs 'mesh size fields'.
        'global_max': 80.,
        '1t1_gap&1t1_signal': [4., 8.],
        '1t1_gap&1t1_ground': [4., 8.],
    }
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()
simulations = [sim_class(layout, **sim_parameters)]

# Sweep given parameters independently
simulations += sweep_simulation(
    layout,
    sim_class,
    sim_parameters,
    {
        # The nominal `sim_parameters` are overwritten with these
        'r_inner': [70, 90, 100],
        'r_outer': np.linspace(270, 290, 3),
    }
)

# Full ND sweep of given parameters
simulations += cross_sweep_simulation(
    layout, sim_class, sim_parameters, {
        'r_inner': [100, 110, 120],
        'r_outer': np.linspace(270, 290, 3),
    }
)

# Export simulation files
export_elmer(simulations, **elmer_export_parameters)

# Write and open OAS file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
