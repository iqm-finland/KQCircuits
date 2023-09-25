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

import logging
import sys
from pathlib import Path

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.simulation_export import sweep_simulation, export_simulation_oas

from kqcircuits.simulations.xmons_direct_coupling_sim import XMonsDirectCouplingSim
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout, \
    open_with_klayout_or_default_application

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
# This is the same as `xmons_direct_coupling` but computes the capacitance matrix using Elmer
sim_class = XMonsDirectCouplingSim  # pylint: disable=invalid-name
sim_parameters = {
    'name': 'three_coupled_xmons',
    'use_internal_ports': True,
    'box': pya.DBox(pya.DPoint(3500, 3500), pya.DPoint(6500, 6500))
}

export_parameters = {
    'path': dir_path,
    'tool': 'capacitance',  # Selected Elmer tool
}

# Gmsh meshing parameters
mesh_size = {
    'global_max': 400.,
    '1t1_gap': 16.,
    '1t1_signal&1t1_gap': 8,
}

# Here we select to use up to 4*2=8 cores with two levels of parallelisation
# That is, we have 4 simulations running at the same time, each using 2 cores.
# NB that mesh_parameters also has a gmsh_n_threads parameter that may be different.
workflow = {
    'run_elmergrid': True,
    'run_gmsh_gui': True,
    'run_elmer': True,
    'run_paraview': False,  # don't open field solution between simulations
    'n_workers': 4,  # workers for first-level parallelisation, using Slurm would override this
    'gmsh_n_threads': 2,
    'elmer_n_processes': 2,  # processes for second-level parallelisation
    'elmer_n_threads': 1,  # number of omp threads per process
    'python_executable': 'python' # use 'kqclib' when using singularity image (you can also put a full path)
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Sweep simulations
simulations = sweep_simulation(layout, sim_class, sim_parameters, {
    'cpl_width': [5, 10, 15, 20]
})

# Export Elmer files
export_elmer(simulations, **export_parameters, mesh_size=mesh_size, workflow=workflow)

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
