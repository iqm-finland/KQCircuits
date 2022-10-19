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

from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import add_parameters_from


@add_parameters_from(FlipChipConnectorRf)
@add_parameters_from(Simulation, face_stack=['1t1', '2b1'])
class FlipChipConnectorSim(Simulation):

    def build(self):
        fcc_cell = self.add_element(FlipChipConnectorRf, **self.get_parameters())

        transf = pya.DTrans(0, False, (self.box.left + self.box.right) / 2, (self.box.bottom + self.box.top) / 2)
        _, refp = self.insert_cell(fcc_cell, transf)

        self.produce_waveguide_to_port(refp["1t1_port"], refp["1t1_port_corner"], 1, 'left', face=0)
        diff_to_rotation = lambda x: abs(x - (self.output_rotation % 360))
        port_dir = {0: 'left', 90: 'bottom', 180: 'right', 270: 'top', 360: 'left'}\
            .get(min([0, 90, 180, 270, 360], key=diff_to_rotation))
        self.produce_waveguide_to_port(refp["2b1_port"], refp["2b1_port_corner"], 2, port_dir, face=1)
