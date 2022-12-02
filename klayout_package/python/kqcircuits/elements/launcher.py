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


class Launcher(Element):
    """The PCell declaration for a launcher for connecting wirebonds.

    Default wirebond direction to west, waveguide to east. Uses default ratio ``a`` and ``b`` for
    scaling the gap if ``a_launcher`` and ``b_launcher`` are not specified. Taper length is from
    waveguide port to the rectangular part of the launcher pad. Pad width is also used for the
    length of the launcher pad.

     .. MARKERS_FOR_PNG 460,54 410,200 677,46 0,0,300,0
    """

    s = Param(pdt.TypeDouble, "Pad width", 300, unit="μm")
    l = Param(pdt.TypeDouble, "Tapering length", 300, unit="μm")
    a_launcher = Param(pdt.TypeDouble, "Outer trace width", 240, unit="μm")
    b_launcher = Param(pdt.TypeDouble, "Outer gap width", 144, unit="μm")
    launcher_frame_gap = Param(pdt.TypeDouble, "Gap at chip frame", 144, unit="μm")

    def build(self):
        # optical layer

        # shape for the inner conductor
        pts = [
            pya.DPoint(0, self.a / 2 + 0),
            pya.DPoint(self.l, self.a_launcher / 2),
            pya.DPoint(self.l + self.s, self.a_launcher / 2),
            pya.DPoint(self.l + self.s, -self.a_launcher / 2),
            pya.DPoint(self.l, -self.a_launcher / 2),
            pya.DPoint(0, -self.a / 2 + 0)
        ]

        shifts = [
            pya.DVector(0, self.b),
            pya.DVector(0, self.b_launcher),
            pya.DVector(self.launcher_frame_gap, self.b_launcher),
            pya.DVector(self.launcher_frame_gap, -self.b_launcher),
            pya.DVector(0, -self.b_launcher),
            pya.DVector(0, -self.b),
        ]
        pts2 = [p + s for p, s in zip(pts, shifts)]
        pts.reverse()
        shape = pya.DPolygon(pts + pts2)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)

        # protection layer
        shifts = [
            pya.DVector(0, self.margin),
            pya.DVector(0, self.margin),
            pya.DVector(self.margin, self.margin),
            pya.DVector(self.margin, -self.margin),
            pya.DVector(0, -self.margin),
            pya.DVector(0, -self.margin),
        ]
        pts2 = [p + s for p, s in zip(pts2, shifts)]
        shape = pya.DPolygon(pts2)
        self.add_protection(shape)

        # add reference point
        self.add_port("", pya.DPoint(0, 0), pya.DVector(-1, 0))
