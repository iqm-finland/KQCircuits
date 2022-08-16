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


from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt


class WaveguideCoplanarStraight(Element):
    """The PCell declaration of a straight segment of a coplanar waveguide.

   .. MARKERS_FOR_PNG 15,8 15,0
    """

    l = Param(pdt.TypeDouble, "Length", 30)

    def build(self):
        # Refpoint in the first end
        # Left gap
        pts = [
            pya.DPoint(0, self.a / 2 + 0),
            pya.DPoint(self.l, self.a / 2 + 0),
            pya.DPoint(self.l, self.a / 2 + self.b),
            pya.DPoint(0, self.a / 2 + self.b)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)
        # Right gap
        pts = [
            pya.DPoint(0, -self.a / 2 + 0),
            pya.DPoint(self.l, -self.a / 2 + 0),
            pya.DPoint(self.l, -self.a / 2 - self.b),
            pya.DPoint(0, -self.a / 2 - self.b)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)
        # Protection layer
        w = self.a / 2 + self.b + self.margin
        pts = [
            pya.DPoint(0, -w),
            pya.DPoint(self.l, -w),
            pya.DPoint(self.l, w),
            pya.DPoint(0, w)
        ]
        self.add_protection(pya.DPolygon(pts))
        # Waveguide length
        pts = [
            pya.DPoint(0, 0),
            pya.DPoint(self.l, 0),
        ]
        shape = pya.DPath(pts, self.a)
        self.cell.shapes(self.get_layer("waveguide_path")).insert(shape)
