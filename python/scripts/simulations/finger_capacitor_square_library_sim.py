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
import subprocess

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import cross_sweep_simulation, export_simulation_oas

from kqcircuits.simulations.finger_capacitor_sim import FingerCapacitorSim
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

sim_class = FingerCapacitorSim  # pylint: disable=invalid-name

# Simulation parameters, using multiface interdigital as starting point
sim_parameters = {
    'name': 'finger_capacitor',
    'use_internal_ports': True,
    'use_ports': True,
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(1000, 1000)),
    "finger_number": 5,
    "finger_width": 15,
    "finger_gap_side": 5,
    "finger_gap_end": 5,
    "finger_length": 20,
    "ground_padding": 10,
    'port_width': 200,
    'wafer_stack_type': "multiface",
    'corner_r': 2,
    'chip_distance': 8
}
# Parameters that differ from sim_parameters for gap type
gap_parameters = {
    'finger_number': 4,
    'finger_length': 0,
    'finger_gap_side': 0,
    'finger_width': 10,
}
export_parameters = {
    'path': dir_path,
    'ansys_tool': 'q3d',
    'exit_after_run': True,
    'percent_error': 0.3,
    'minimum_converged_passes': 2,
    'maximum_passes': 20,
}

# Sweep ranges
chip_distances = [4, 5, 6, 7, 8, 9, 10, 12, 14, 18, 22]
finger_numbers = [2, 4, 8]
finger_lengths = [0, 2, 6, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
gap_lengths = [1, 2, 4, 6, 10, 13, 16, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100]

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Cross sweep number of fingers and finger length
simulations = []

# Multi face finger (interdigital) capacitor sweeps
simulations += cross_sweep_simulation(layout, sim_class, sim_parameters, {
    'chip_distance': chip_distances,
    'finger_number': finger_numbers,
    'finger_length': finger_lengths,
})

# Multi face gap capacitor sweeps
simulations += cross_sweep_simulation(
    layout, sim_class,
    {
        **sim_parameters,
        'name': sim_parameters['name'] + '_gap',
        **gap_parameters,
    },
    {
        'chip_distance': chip_distances,
        'finger_gap_end': gap_lengths,
    })


# Single face finger (interdigital) capacitor sweeps
simulations += cross_sweep_simulation(
    layout, sim_class,
    {
        **sim_parameters,
        'name': sim_parameters['name'] + '_singleface',
        'wafer_stack_type': 'planar',
    }, {
        'finger_number': finger_numbers,
        'finger_length': finger_lengths,
    })

# Single face gap capacitor sweeps
simulations += cross_sweep_simulation(
    layout, sim_class,
    {
        **sim_parameters,
        'name': sim_parameters['name'] + '_singleface_gap',
        'wafer_stack_type': 'planar',
        **gap_parameters,
    },
    {
        'finger_gap_end': gap_lengths,
    })

# Export Ansys files
export_ansys(simulations, **export_parameters)

# Write and open oas file
subprocess.call(export_simulation_oas(simulations, dir_path), shell=True)
