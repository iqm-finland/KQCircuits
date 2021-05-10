# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import math

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.elements.element import Element
from kqcircuits.defaults import default_layers
from math import ceil


class WaveguideCoplanarTaper(Element):
    """The PCell declaration of a taper segment of a coplanar waveguide."""

    taper_length = Param(pdt.TypeDouble, "Taper length", 10 * math.pi, unit="μm")
    a1 = Param(pdt.TypeDouble, "Width of left waveguide center conductor", Element.a, unit="μm")
    b1 = Param(pdt.TypeDouble, "Width of left waveguide gap", Element.b, unit="μm")
    m1 = Param(pdt.TypeDouble, "Margin of left waveguide protection layer", 5, unit="μm")
    a2 = Param(pdt.TypeDouble, "Width of right waveguide center conductor", Element.a * 2, unit="μm")
    b2 = Param(pdt.TypeDouble, "Width of right waveguide gap", Element.b * 2, unit="μm")
    m2 = Param(pdt.TypeDouble, "Margin of right waveguide protection layer", 5 * 2, unit="μm")

    def produce_impl(self):
        #
        # gap 1
        pts = [
            pya.DPoint(0, self.a1 / 2 + 0),
            pya.DPoint(self.taper_length, self.a2 / 2 + 0),
            pya.DPoint(self.taper_length, self.a2 / 2 + self.b2),
            pya.DPoint(0, self.a1 / 2 + self.b1)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)
        # gap 2
        pts = [
            pya.DPoint(0, -self.a1 / 2 + 0),
            pya.DPoint(self.taper_length, -self.a2 / 2 + 0),
            pya.DPoint(self.taper_length, -self.a2 / 2 - self.b2),
            pya.DPoint(0, -self.a1 / 2 - self.b1)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)
        # Protection layer
        pts = [
            pya.DPoint(0, -self.a1 / 2 - self.b1 - self.m1),
            pya.DPoint(self.taper_length, -self.a2 / 2 - self.b2 - self.m2),
            pya.DPoint(self.taper_length, self.a2 / 2 + self.b2 + self.m2),
            pya.DPoint(0, self.a1 / 2 + self.b1 + self.m1)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(shape)
        # Annotation
        pts = [
            pya.DPoint(0, 0),
            pya.DPoint(self.taper_length, 0),
        ]
        shape = pya.DPath(pts, ceil(self.a1 + 2 * self.b1))
        self.cell.shapes(self.get_layer("waveguide_length")).insert(shape)
        # refpoints for connecting to waveguides
        self.add_port("a", pya.DPoint(0, 0))
        self.add_port("b", pya.DPoint(self.taper_length, 0))
        # adds annotation based on refpoints calculated above
        super().produce_impl()

