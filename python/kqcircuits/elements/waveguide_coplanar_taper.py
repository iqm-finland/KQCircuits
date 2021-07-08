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


import math
from math import ceil

from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt


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
