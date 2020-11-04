# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import math
from kqcircuits.pya_resolver import pya
from autologging import logged, traced

from kqcircuits.elements.element import Element

@traced
@logged
class FlipChipConnector(Element):
    """Connector between matching faces of two chips.

    The connector makes a galvanic contact between the flipped over top chip and the bottom chip.
    The design is compatible with both indium evaporation and electroplating. Origin is at the
    geometric center.
    """

    PARAMETERS_SCHEMA = {
        "ubm_box": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Under-bump metallization width [μm]",
            "docstring": "Length of the side of the under-bump metallization box [μm]",
            "default": 40
        },
        "bump_diameter": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Bump diameter [μm]",
            "docstring": "Indium bump diameter [μm]",
            "default": 25
        }
    }

    def produce_impl(self):
        super().produce_impl()

    def create_bump_connector(self):
        # origin: geometric center
        # direction: from top to bottom

        # shorthand
        w = self.ubm_box
        r = self.bump_diameter/2

        # under-bump metallization
        pts = [
            pya.DPoint(-w/2, -w/2),
            pya.DPoint(-w/2, w/2),
            pya.DPoint(w/2, w/2),
            pya.DPoint(w/2, -w/2),
        ]
        shape = pya.DPolygon(pts)

        # bottom under-bump metallization
        self.cell.shapes(self.get_layer("underbump metallization")).insert(shape)
        # top under-bump metallization
        self.cell.shapes(self.get_layer("underbump metallization", 1)).insert(shape)

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
        self.cell.shapes(self.get_layer("ground grid avoidance")).insert(shape)
        self.cell.shapes(self.get_layer("ground grid avoidance")).insert(pya.DTrans.M0*shape)

        # ground avoidance layer top
        self.cell.shapes(self.get_layer("ground grid avoidance", 1)).insert(shape)
        self.cell.shapes(self.get_layer("ground grid avoidance", 1)).insert(pya.DTrans.M0*shape)

        # bump geometry
        circle_pts = [pya.DPoint(math.cos(a/32 * math.pi) * r,
                      math.sin(a/32 * math.pi) * r) for a in range(0, 64 + 1)]
        shape = pya.DPolygon(circle_pts)
        self.cell.shapes(self.get_layer("indium bump")).insert(shape)  # bottom In bump
        self.cell.shapes(self.get_layer("indium bump", 1)).insert(shape)  # top In bump


