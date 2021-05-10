# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import math
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from autologging import logged, traced

from kqcircuits.elements.element import Element

@traced
@logged
class FlipChipConnector(Element):
    """Connector between matching faces of two chips.

    The connector makes a galvanic contact between the flipped over top chip and the bottom chip.
    Origin is at the geometric center.
    """

    ubm_box = Param(pdt.TypeDouble, "Under-bump metallization width", 40, unit="μm",
        docstring="Length of the side of the under-bump metallization box [μm]")
    bump_diameter = Param(pdt.TypeDouble, "Bump diameter", 25, unit="μm",
        docstring="Indium bump diameter [μm]")

    def produce_impl(self):
        super().produce_impl()

    def create_bump_connector(self):
        # origin: geometric center
        # direction: from top to bottom

        # shorthand
        w = self.ubm_box
        r = self.bump_diameter/2

        # under-bump metallization
        # TODO: replace UBM square with circle
        pts = [
            pya.DPoint(-w/2, -w/2),
            pya.DPoint(-w/2, w/2),
            pya.DPoint(w/2, w/2),
            pya.DPoint(w/2, -w/2),
        ]
        shape = pya.DPolygon(pts)

        # bottom under-bump metallization
        self.cell.shapes(self.get_layer("underbump_metallization")).insert(shape)
        # top under-bump metallization
        self.cell.shapes(self.get_layer("underbump_metallization", 1)).insert(shape)

        # Protection layer
        m = self.margin
        pts = [
            pya.DPoint(-w/2 - m, -w/2 - m),
            pya.DPoint(-w/2 - m, w/2 + m),
            pya.DPoint(w/2 + m, w/2 + m),
            pya.DPoint(w/2 + m, -w/2 - m),
        ]
        shape = pya.DPolygon(pts)

        # ground avoidance layer bottom
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(shape)
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(pya.DTrans.M0*shape)

        # ground avoidance layer top
        self.cell.shapes(self.get_layer("ground_grid_avoidance", 1)).insert(shape)
        self.cell.shapes(self.get_layer("ground_grid_avoidance", 1)).insert(pya.DTrans.M0*shape)

        # bump geometry
        circle_pts = [pya.DPoint(math.cos(a/32 * math.pi) * r,
                      math.sin(a/32 * math.pi) * r) for a in range(0, 64 + 1)]
        shape = pya.DPolygon(circle_pts)
        self.cell.shapes(self.get_layer("indium_bump")).insert(shape)  # bottom In bump
        self.cell.shapes(self.get_layer("indium_bump", 1)).insert(shape)  # top In bump
        super().produce_impl()

