# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element


class Launcher(Element):
    """The PCell declaration for an arbitrary waveguide

    Launcher for connecting wirebonds. Default wirebond direction to west, waveguide to east. Uses default ratio a
    and b for scaling the gap.
    """

    PARAMETERS_SCHEMA = {
        "s": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Pad width (um)",
            "default": 300
        },
        "l": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Tapering length (um)",
            "default": 300
        },
        "name": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Name shown on annotation layer",
            "default": ""
        }
    }

    def __init__(self):
        super().__init__()

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "Launcher(%s)".format(self.name)

    def coerce_parameters_impl(self):
        None

    def can_create_from_shape_impl(self):
        return False

    def parameters_from_shape_impl(self):
        None

    def transformation_from_shape_impl(self):
        return pya.Trans()

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
        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(shape)

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
        self.cell.shapes(self.layout.layer(self.face()["ground grid avoidance"])).insert(shape)

        # annotation text
        if self.name:
            label = pya.DText(self.name, 1.5 * self.l, 0)
            self.cell.shapes(self.layout.layer(self.la)).insert(label)
