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

from kqcircuits.simulations.simulation import Simulation
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import point_shift_along_vector
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.elements.airbridges.airbridge import Airbridge


class AirbridgesSim(Simulation):

    n_bridges = Param(pdt.TypeInt, "Number of bridges in series", 5)

    def build(self):
        ab_cell = self.add_element(Airbridge, bridge_length=2*self.b + self.a + 24)
        line_length = 800
        bridge_spacing = (line_length) / (self.n_bridges+1)
        for n in range(self.n_bridges):
            self.insert_cell(ab_cell, pya.DTrans(2, False,
                                                 point_shift_along_vector(pya.DPoint(100, 250), pya.DPoint(150, 250),
                                                                          (n+1) * bridge_spacing)))
        self.produce_waveguide_to_port(pya.DPoint(100, 250), pya.DPoint(150, 250), 1, use_internal_ports=True,
                                       waveguide_length=line_length, term1=6)
