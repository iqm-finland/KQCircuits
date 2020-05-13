# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import math

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element


class WaveguideCoplanarStraight(Element):
    """
  The PCell declaration of a straight segment of a coplanar waveguide
  """

    PARAMETERS_SCHEMA = {
        "l": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Length",
            "default": math.pi
        }
    }

    def __init__(self):
        super().__init__()

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "WaveguideCopStraight(a=" + ('%.1f' % self.a) + ",b=" + ('%.1f' % self.b) + ")"

    def coerce_parameters_impl(self):
        None

    def can_create_from_shape_impl(self):
        return False

    def parameters_from_shape_impl(self):
        None

    def produce_impl(self):
        # Refpoint in the first end
        # Left gap
        pts = [
            pya.DPoint(0, self.a / 2 + 0),
            pya.DPoint(self.l, self.a / 2 + 0),
            pya.DPoint(self.l, self.a / 2 + self.b),
            pya.DPoint(0, self.a / 2 + self.b)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(shape)
        # Right gap
        pts = [
            pya.DPoint(0, -self.a / 2 + 0),
            pya.DPoint(self.l, -self.a / 2 + 0),
            pya.DPoint(self.l, -self.a / 2 - self.b),
            pya.DPoint(0, -self.a / 2 - self.b)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(shape)
        # Protection layer
        w = self.a / 2 + self.b + self.margin
        pts = [
            pya.DPoint(0, -w),
            pya.DPoint(self.l, -w),
            pya.DPoint(self.l, w),
            pya.DPoint(0, w)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.layout.layer(self.face()["ground grid avoidance"])).insert(shape)
        # Annotation
        pts = [
            pya.DPoint(0, 0),
            pya.DPoint(self.l, 0),
        ]
        shape = pya.DPath(pts, self.a + 2 * self.b)
        self.cell.shapes(self.layout.layer(self.la)).insert(shape)
