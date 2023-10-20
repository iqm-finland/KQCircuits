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
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.util.refpoints import WaveguideToSimPort


class HangerResonator(Element):
    """
    Hanger Resonator
    """
    coupling_length = Param(pdt.TypeDouble, "Length of the resonator center part (coupling)", 500, unit="μm")
    head_length = Param(pdt.TypeDouble, "Length of the resonator left waveguide (head) ", 300, unit="μm")
    resonator_length = Param(pdt.TypeDouble, "Total length of the resonator", 1000, unit="μm")

    res_a = Param(pdt.TypeDouble, "Trace width of resonator line", 10, unit="μm")
    res_b = Param(pdt.TypeDouble, "Gap width of resonator line", 6, unit="μm")

    ground_width = Param(pdt.TypeDouble, "Trace width of middle ground", 10, unit="μm")

    def build(self):

        # If turn radius is smaller than half of the trace width it will create some overlapping masks and sharp angles
        if self.r < self.res_a / 2:
            self.raise_error_on_cell(f'Turn radius must be at least res_a/2, now r={self.r}, res_a/2={self.res_a/2}')

        # probe line, origin at the center of the trace
        points_pl = [pya.DPoint(0, 0)]
        points_pl.append(pya.DPoint(self.coupling_length, 0))

        # distance from origin to start of the wg trace
        wg_start_height = -self.a / 2 - self.b - self.ground_width - self.res_b
        # x distance from pl port to center trace of vertical waveguides
        corner_x = self.r
        # corner arc length
        corner_length = pi * self.r/2
        head_length_down = self.head_length - corner_length

        points = []

        if head_length_down > 0:
            # left side, head
            # left leg
            p1 = pya.DPoint(-corner_x, wg_start_height - self.res_a / 2 - self.r - head_length_down)
            points.append(p1)
            # corner
            p2 = pya.DPoint(-corner_x, wg_start_height - self.res_a / 2)

            length_without_tail = self.head_length + self.coupling_length + corner_length

        # If head lenght is too small don't create the curve on left side
        else:
            # Add a stub corresponding to head length if head length is shorter than the corner
            p2 = pya.DPoint(-max(self.head_length, 0), wg_start_height - self.res_a/2)

            length_without_tail = self.coupling_length + corner_length

        points.append(p2)


        # If given resonator length is too small, don't create downwards tail
        if length_without_tail >= self.resonator_length:

            # Add a stub corresponding to tail length if head length is shorter than the corner
            x_tail_offset = max(0, self.resonator_length - (length_without_tail - corner_length))

            p3 = pya.DPoint(self.coupling_length + x_tail_offset, wg_start_height - self.res_a / 2)

            points.append(p3)

        else:
            tail_length = self.resonator_length - length_without_tail
            # right leg (tail)
            p3 = pya.DPoint(self.coupling_length + corner_x, wg_start_height - self.res_a / 2)
            p4 = pya.DPoint(self.coupling_length + corner_x, wg_start_height - self.res_a / 2 - self.r - tail_length)

            points.append(p3)
            points.append(p4)

        cells_pl, _ = self.insert_cell(WaveguideCoplanar, path=points_pl)
        cells_resonator, _ = self.insert_cell(WaveguideCoplanar, path=points, a=self.res_a, b=self.res_b)

        self.copy_port("a", cells_pl)
        self.copy_port("b", cells_pl)
        self.copy_port("a", cells_resonator, "resonator_a")
        self.copy_port("b", cells_resonator, "resonator_b")
        # these are needed for simulations
        self.copy_port("a", cells_pl, "sim_a")
        self.copy_port("b", cells_pl, "sim_b")

    @classmethod
    def get_sim_ports(cls, simulation):
        return [WaveguideToSimPort("port_sim_a", use_internal_ports=False, a=simulation.a, b=simulation.b),
                WaveguideToSimPort("port_sim_b", use_internal_ports=False, a=simulation.a, b=simulation.b),
                WaveguideToSimPort("port_resonator_a", a=simulation.res_a, b=simulation.res_b),
                WaveguideToSimPort("port_resonator_b", a=simulation.res_a, b=simulation.res_b)]
