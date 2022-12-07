# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
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
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.simulation_export import export_simulation_oas

from kqcircuits.simulations.finger_capacitor_sim import FingerCapacitorSim
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout, \
    open_with_klayout_or_default_application

sim_class = FingerCapacitorSim  # pylint: disable=invalid-name

use_elmer = True
with_grid = True
with_grid_str = '_with_grid' if with_grid else ''
# Prepare output directory
if use_elmer:
    path = create_or_empty_tmp_directory(Path(__file__).stem.replace('_with_grid', '') + with_grid_str + "_elmer")
else:
    path = create_or_empty_tmp_directory(Path(__file__).stem.replace('_with_grid', '') + with_grid_str + "_q3d")

# Simulation parameters, using multiface interdigital as starting point
sim_parameters = {
    'name': 'capacitor',
    'use_internal_ports': True,
    'use_ports': True,
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(1000, 1000)),
    'ground_grid_box': pya.DBox(pya.DPoint(350, 450), pya.DPoint(650, 550)),
    "finger_number": 4,
    "finger_width": 10,
    "finger_gap_end": 9.5,
    "finger_length": 0,
    "finger_gap": 0,
    "a": 3.5,
    "b": 32,
    "a2": 3.5,
    "b2": 32,
    "ground_padding": 10,
    'port_size': 200,
    'wafer_stack_type': "multiface",
    'corner_r': 2,
    'chip_distance': 8,
    'with_grid': with_grid,
    'face_ids': ['2b1', '1t1', '2t1'],
}

if use_elmer:
    mesh_parameters = {
        'default_mesh_size': 100.,
        'ground_min_mesh_size': 100,
        'ground_min_dist': 4.,
        'ground_max_dist': 100.,
        'ground_grid_min_mesh_size': 10,
        'ground_grid_min_dist': 4.,
        'ground_grid_max_dist': 100.,
        'gap_min_mesh_size': 1,
        'gap_min_dist': 4.,
        'gap_max_dist': 100.,
        'port_min_mesh_size': 1.,
        'port_min_dist': 4.,
        'port_max_dist': 100.,
        'algorithm': 5,
    }

    export_parameters_elmer = {
        'path': path,
        'tool': 'capacitance',
    }

    workflow = {
        'run_gmsh_gui': True,  # For GMSH: if true, the mesh is shown after it is done
                               # (for large meshes this can take a long time)
        'run_elmergrid': True,
        'run_elmer': True,
        'run_paraview': True,  # this is visual view of the results which can be removed to speed up the process
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

sim_param_list = [sim_parameters]
simulations = [sim_class(layout, **param) for param in sim_param_list]

# Export Ansys files
# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, path))

if use_elmer:
    export_elmer(simulations, **export_parameters_elmer, gmsh_params=mesh_parameters, workflow=workflow)
else:
    export_ansys(simulations, **export_parameters_ansys)
