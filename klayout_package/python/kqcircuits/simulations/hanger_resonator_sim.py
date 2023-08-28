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

from kqcircuits.util.parameters import add_parameters_from
from kqcircuits.elements.hanger_resonator import HangerResonator
from kqcircuits.simulations.simulation import Simulation

@add_parameters_from(HangerResonator)
class HangerResonatorSim(Simulation):

    def build(self):

        resonator_cell = self.add_element(HangerResonator)

        _, refp = self.insert_cell(resonator_cell)

        self.produce_waveguide_to_port(refp["port_pl_a"],
                                       refp["port_pl_a_corner"],
                                       1,
                                       use_internal_ports=False,
                                       a=self.pl_a,
                                       b=self.pl_b,
                                       turn_radius=0) # Ports extend straight to edges
                                                      # Nonzero radius causes div by 0 if box is not very large
        self.produce_waveguide_to_port(refp["port_pl_b"],
                                       refp["port_pl_b_corner"],
                                       2,
                                       use_internal_ports=False,
                                       a=self.pl_a,
                                       b=self.pl_b,
                                       turn_radius=0)

        self.produce_waveguide_to_port(refp["port_a"], refp["port_a_corner"], 3, 'left', a=self.a, b=self.b)
        self.produce_waveguide_to_port(refp["port_b"], refp["port_b_corner"], 4, 'right', a=self.a, b=self.b)
