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
import subprocess
import sys
from pathlib import Path

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import export_simulation_oas, sweep_simulation
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout


class InternalPortCalibration(Simulation):
    """ Left half of the ground plane is etched away, and a waveguide is added from the center towards the right. """

    def build(self):
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(
            pya.DBox(pya.DPoint(self.box.left + 10, self.box.bottom + 10),
                     pya.DPoint(self.box.center().x, self.box.top - 10)))
        self.produce_waveguide_to_port(self.box.center(), pya.DPoint(self.box.right, self.box.center().y), 1, 'right')


# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
sim_class = InternalPortCalibration  # pylint: disable=invalid-name
sim_parameters = {
    'name': 'port_sim',
    'use_internal_ports': True,
    'use_ports': True,
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(500, 500)),
    'waveguide_length': 10,
    'wafer_stack_type': "multiface",  # chip distance default at 8um
    'a': 3.5, #readout structure a in flip chip
    'b': 32  #readout structure b in flip chip
}
export_parameters = {
    'path': dir_path,
    'max_delta_s': 0.0001,
    'maximum_passes': 40,
    'frequency': 5,
    'sweep_start': 1,
    'sweep_end': 5,
    'sweep_count': 4,
    'exit_after_run': True
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# # Sweep simulations for variable geometry
# simulations = cross_sweep_simulation(layout, sim_class, sim_parameters, {
#     'a': [2, 4, 6, 8, 10, 12, 16, 20],
#     'b': [2, 4, 6, 10, 14, 18, 22, 30],
#     'waveguide_length': [1, 10, 20, 50, 100]
# })

#Fixed geometry simulation
simulations = sweep_simulation(layout, sim_class, sim_parameters, {
    'waveguide_length': [1, 10, 20, 50, 100]
})

# Export Ansys files
export_ansys(simulations, **export_parameters)

# Write and open oas file
subprocess.call(export_simulation_oas(simulations, dir_path), shell=True)
