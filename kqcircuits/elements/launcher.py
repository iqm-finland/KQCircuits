# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.elements.element import Element
from kqcircuits.defaults import default_layers


class Launcher(Element):
    """The PCell declaration for a launcher for connecting wirebonds.

    Default wirebond direction to west, waveguide to east. Uses default ratio a
    and b for scaling the gap.
    """

    s = Param(pdt.TypeDouble, "Pad width", 300, unit="μm")
    l = Param(pdt.TypeDouble, "Tapering length", 300, unit="μm")

    def produce_impl(self):
        # optical layer

        # keep the a/b ratio the same, but scale up a and b
        f = self.s / float(self.a)

        # shape for the inner conductor
        pts = [
            pya.DPoint(0, self.a / 2 + 0),
            pya.DPoint(self.l, f * (self.a / 2)),
            pya.DPoint(self.l + self.s, f * (self.a / 2)),
            pya.DPoint(self.l + self.s, -f * (self.a / 2)),
            pya.DPoint(self.l, -f * (self.a / 2)),
            pya.DPoint(0, -self.a / 2 + 0)
        ]

        shifts = [
            pya.DVector(0, self.b),
            pya.DVector(0, self.b * f),
            pya.DVector(self.b * f, self.b * f),
            pya.DVector(self.b * f, -self.b * f),
            pya.DVector(0, -self.b * f),
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
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(shape)

        # add reference point
        self.add_port("", pya.DPoint(0, 0), pya.DVector(-1, 0))

        super().produce_impl()
