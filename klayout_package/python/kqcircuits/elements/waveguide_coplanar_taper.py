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

from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare


@add_parameters_from(FingerCapacitorSquare, a2=Element.a*2, b2=Element.b*2)
class WaveguideCoplanarTaper(Element):
    """The PCell declaration of a taper segment of a coplanar waveguide.

    .. MARKERS_FOR_PNG 0,0,31.2,0 0,5,0,-5 31.2,-10,31.2,10
    """

    taper_length = Param(pdt.TypeDouble, "Taper length", 10 * math.pi, unit="μm")
    m2 = Param(pdt.TypeDouble, "Margin of right waveguide protection layer", 5 * 2, unit="μm")

    def build(self):
        #
        # gap 1
        pts = [
            pya.DPoint(0, self.a / 2 + 0),
            pya.DPoint(self.taper_length, self.a2 / 2 + 0),
            pya.DPoint(self.taper_length, self.a2 / 2 + self.b2),
            pya.DPoint(0, self.a / 2 + self.b)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)
        # gap 2
        pts = [
            pya.DPoint(0, -self.a / 2 + 0),
            pya.DPoint(self.taper_length, -self.a2 / 2 + 0),
            pya.DPoint(self.taper_length, -self.a2 / 2 - self.b2),
            pya.DPoint(0, -self.a / 2 - self.b)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)
        # Protection layer
        pts = [
            pya.DPoint(0, -self.a / 2 - self.b - self.margin),
            pya.DPoint(self.taper_length, -self.a2 / 2 - self.b2 - self.m2),
            pya.DPoint(self.taper_length, self.a2 / 2 + self.b2 + self.m2),
            pya.DPoint(0, self.a / 2 + self.b + self.margin)
        ]
        self.add_protection(pya.DPolygon(pts))
        # Waveguide layer
        pts = [
            pya.DPoint(0, self.a / 2),
            pya.DPoint(self.taper_length, self.a2 / 2),
            pya.DPoint(self.taper_length, -self.a2 / 2),
            pya.DPoint(0, -self.a / 2)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("waveguide_path")).insert(shape)
        pts = [
            pya.DPoint(0, 0),
            pya.DPoint(self.taper_length, 0),
        ]
        shape = pya.DPath(pts, min(self.a, self.a2))
        self.cell.shapes(self.get_layer("waveguide_path")).insert(shape)
        # refpoints for connecting to waveguides
        self.add_port("a", pya.DPoint(0, 0), pya.DVector(-1, 0))
        self.add_port("b", pya.DPoint(self.taper_length, 0), pya.DVector(1, 0))
