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

from math import pi
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_composite import WaveguideComposite
from kqcircuits.elements.waveguide_composite import Node
from kqcircuits.util.refpoints import WaveguideToSimPort


class HangerResonator(Element):
    """
    Hanger Resonator
    """
    coupling_length = Param(pdt.TypeDouble, "Length of the resonator center part (coupling)", 500, unit="μm")
    head_length = Param(pdt.TypeDouble, "Length of the resonator left waveguide (head) ", 300, unit="μm")
    resonator_length = Param(pdt.TypeDouble, "Total length of the resonator", 1000, unit="μm")

    pl_a = Param(pdt.TypeDouble, "Trace width of probe line", 10, unit="μm")
    pl_b = Param(pdt.TypeDouble, "Gap width of probe line", 6, unit="μm")

    ground_width = Param(pdt.TypeDouble, "Trace width of middle ground", 10, unit="μm")

    def build(self):

        # If turn radius is smaller than half of the trace width it will create some overlapping masks and sharp angles
        if self.r < self.a/2:
            self.raise_error_on_cell(f'Turn radius must be at least a/2, now given r={self.r}, a/2={self.a/2}')

        # probe line, origin at the center of the trace
        pl_p1 = (0, 0)
        pl_p2 = (self.coupling_length, 0)
        nodes_pl = [Node(pl_p1), Node(pl_p2)]

        # distance from origin to start of the wg trace
        wg_start_height = -self.pl_a/2-self.pl_b-self.ground_width-self.b
        # x distance from pl port to center trace of vertical waveguides
        corner_x = self.r
        # corner arc length
        corner_length = pi*self.r/2
        head_length_down = self.head_length - corner_length

        nodes = []

        if head_length_down > 0:
            # left side, head
            # left leg
            p1 = (-corner_x, wg_start_height - self.a/2 - self.r - head_length_down)
            nodes.append(Node(p1))
            # corner
            p2 = (-corner_x, wg_start_height-self.a/2)

            length_without_tail = self.head_length + self.coupling_length + corner_length

        # If head lenght is too small don't create the curve on left side
        else:
            # Add a stub corresponding to head length if head length is shorter than the corner
            p2 = (-max(self.head_length,0), wg_start_height-self.a/2)

            length_without_tail = self.coupling_length + corner_length


        nodes.append(Node(p2))


        # If given resonator length is too small, don't create downwards tail
        if length_without_tail >= self.resonator_length:

            # Add a stub corresponding to tail length if head length is shorter than the corner
            x_tail_offset = max(0, self.resonator_length - (length_without_tail - corner_length))

            p3 = (self.coupling_length + x_tail_offset, wg_start_height-self.a/2)

            nodes.append(Node(p3))

        else:
            tail_length = self.resonator_length - length_without_tail
            # right leg (tail)
            p3 = (self.coupling_length + corner_x, wg_start_height - self.a/2)
            p4 = (self.coupling_length + corner_x, wg_start_height - self.a/2 - self.r - tail_length)

            nodes.append(Node(p3))
            nodes.append(Node(p4))

        cells_pl, _ = self.insert_cell(WaveguideComposite, nodes=nodes_pl, a=self.pl_a, b=self.pl_b, r=self.r)
        cells_resonator, _ = self.insert_cell(WaveguideComposite, nodes=nodes, a=self.a, b=self.b, r=self.r)

        self.copy_port("a", cells_pl, "pl_a")
        self.copy_port("b", cells_pl, "pl_b")
        self.copy_port("a", cells_resonator)
        self.copy_port("b", cells_resonator)

    @classmethod
    def get_sim_ports(cls, simulation):
        return [WaveguideToSimPort("port_pl_a", use_internal_ports=False,
                                   a=simulation.pl_a, b=simulation.pl_b, turn_radius=0),
                WaveguideToSimPort("port_pl_b", use_internal_ports=False,
                                   a=simulation.pl_a, b=simulation.pl_b, turn_radius=0),
                WaveguideToSimPort("port_a", side="left", a=simulation.a, b=simulation.b),
                WaveguideToSimPort("port_b", side="right", a=simulation.a, b=simulation.b)]
