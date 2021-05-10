# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from autologging import logged, traced

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.fluxlines.fluxline import Fluxline


@traced
@logged
class FluxlineStraight(Fluxline):
    """Fluxline variant "straight vertical"."""

    def produce_impl(self):

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
