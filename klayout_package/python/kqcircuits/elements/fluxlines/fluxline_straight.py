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


from autologging import logged

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.elements.fluxlines.fluxline import Fluxline


@logged
@add_parameters_from(Fluxline, fluxline_gap_width=3)
class FluxlineStraight(Fluxline):
    """Fluxline variant "straight vertical".

     .. MARKERS_FOR_PNG -4,-6 0,-7
    """
    fluxline_width = Param(pdt.TypeDouble, "Fluxline width", 0, unit="μm", hidden=True)

    def build(self):

        b = self.fluxline_gap_width
        a = (self.a/self.b)*b  # fluxline center width
        l1 = 2*b  # straight down
        bottom_y = -b - l1

        # origin at edge of the qubit gap

        # Right gap of the fluxline. Points created clockwise starting from top left point.
        x_offset = 0  # a + b
        right_gap_pts = [
            pya.DPoint(-b / 2 + x_offset, -b),
            pya.DPoint(b / 2 + x_offset, -b),
            pya.DPoint(b / 2 + x_offset, bottom_y),
            pya.DPoint(-b / 2 + x_offset, bottom_y),
        ]
        right_gap = pya.DPolygon(right_gap_pts)

        # Left gap of the fluxline. Points created clockwise starting from top left point.
        left_gap_pts = [
            right_gap_pts[0] + pya.DPoint(-a - b, 0),
            right_gap_pts[1] + pya.DPoint(-a - b, 0),
            right_gap_pts[2] + pya.DPoint(-a - b, 0),
            right_gap_pts[3] + pya.DPoint(-a - b, 0),
        ]
        left_gap = pya.DPolygon(left_gap_pts)

        self._insert_fluxline_shapes(left_gap, right_gap)
        self._add_fluxline_refpoints(pya.DPoint(-a/2 - b/2 + x_offset, bottom_y))
