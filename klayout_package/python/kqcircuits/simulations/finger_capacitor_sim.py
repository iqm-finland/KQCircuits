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
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.util.parameters import add_parameters_from


@add_parameters_from(FingerCapacitorSquare)
class FingerCapacitorSim(Simulation):

    def build(self):
        capacitor_cell = self.add_element(FingerCapacitorSquare)

        cap_trans = pya.DTrans(0, False, (self.box.left + self.box.right) / 2, (self.box.bottom + self.box.top) / 2)
        _, refp = self.insert_cell(capacitor_cell, cap_trans)

        a2 = self.a if self.a2 < 0 else self.a2
        b2 = self.b if self.b2 < 0 else self.b2
        self.produce_waveguide_to_port(refp["port_a"], refp["port_a_corner"], 1, 'left', a=self.a, b=self.b)
        self.produce_waveguide_to_port(refp["port_b"], refp["port_b_corner"], 2, 'right', a=a2, b=b2)
