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
import subprocess

from math import inf
import numpy as np
from kqcircuits.elements.smooth_capacitor import SmoothCapacitor
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import cross_sweep_simulation, export_simulation_oas

from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout
from kqcircuits.util.parameters import add_parameters_from


@add_parameters_from(SmoothCapacitor)
class SmoothCapacitorSim(Simulation):

    def build(self):
        if self.chip_distance == inf:
            self.wafer_stack_type = 'planar'
            self.chip_distance = 1e30
        else:
            self.wafer_stack_type = 'multiface'
        capacitor_cell = self.add_element(SmoothCapacitor, **{**self.get_parameters()})

        cap_trans = pya.DTrans(0, False, (self.box.left + self.box.right) / 2, (self.box.bottom + self.box.top) / 2)
        _, refp = self.insert_cell(capacitor_cell, cap_trans)

        a2 = self.a if self.a2 < 0 else self.a2
        b2 = self.b if self.b2 < 0 else self.b2
        self.produce_waveguide_to_port(refp["port_a"], refp["port_a_corner"], 1, 'left', a=self.a, b=self.b)
        self.produce_waveguide_to_port(refp["port_b"], refp["port_b_corner"], 2, 'right', a=a2, b=b2)

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

sim_class = SmoothCapacitorSim  # pylint: disable=invalid-name

# Simulation parameters, using multiface interdigital as starting point
sim_parameters = {
    'name': 'smooth_capacitor',
    'use_internal_ports': True,
    'use_ports': True,
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(1000, 1000)),
    "finger_number": 1,
    "finger_width": 10,
    "gap": 5,
    "ground_gap": 10,
}
# Parameters that differ from sim_parameters for gap type
export_parameters = {
    'path': dir_path,
    'ansys_tool': 'q3d',
    'exit_after_run': True,
    'percent_error': 0.1,
    'minimum_converged_passes': 1,
    'maximum_passes': 20,
    'minimum_passes': 15
}

# Sweep ranges
finger_numbers = [round(v, 5) for v in np.linspace(0.2, 5, 49)]
chip_distances = [4, 5.5, 8, 16, inf]
a_def = [10]
b_def = [6]

num = 4
finger_numbers_comp = [round((5**(1/num))**i, 1) for i in range(-num,num+1)]
print(finger_numbers_comp)
chip_distances_comp = [4, 8, inf]
as_comp = [2,10,20]
bs_comp = [2,6,18,32]

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Cross sweep number of fingers
simulations = []

# Default sweep
simulations += cross_sweep_simulation(layout, sim_class, sim_parameters, {
    'finger_number': finger_numbers,
    'chip_distance': chip_distances,
    'a': a_def,
    'b': b_def,
    'a2': a_def,
    'b2': b_def
})

# Compensation
for n in finger_numbers_comp:
    for d in chip_distances_comp:
        for a in as_comp:
            for b in bs_comp:
                for a2 in as_comp:
                    for b2 in bs_comp:
                        if a in a_def and b in b_def and a2 in a_def and b2 in b_def:
                            continue  # do not create defaults again
                        if a + b > a2 + b2:
                            continue  # due to symmetry, we can skip almost half of the simulations
                        simulations += cross_sweep_simulation(layout, sim_class, sim_parameters, {
                            'finger_number': [n],
                            'chip_distance': [d],
                            'a': [a],
                            'b': [b],
                            'a2': [a2],
                            'b2': [b2]
                        })

# Export Ansys files
export_ansys(simulations, **export_parameters)

# Write and open oas file
subprocess.call(export_simulation_oas(simulations, dir_path), shell=True)
