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

from kqcircuits.simulations.simulation import Simulation
from kqcircuits.simulations.port import EdgePort
from kqcircuits.util.parameters import add_parameters_from
from kqcircuits.elements.capacitive_x_coupler import CapacitiveXCoupler


@add_parameters_from(CapacitiveXCoupler)
class CapacitiveXCouplerSim(Simulation):

    def build(self):
        wg_cell = self.add_element(CapacitiveXCoupler)
        _, refp = self.insert_cell(wg_cell)
        self.ports.append(EdgePort(1, refp['p11']))
        self.ports.append(EdgePort(2, refp['p21']))
        self.ports.append(EdgePort(3, refp['p31']))
        self.ports.append(EdgePort(4, refp['p41']))
