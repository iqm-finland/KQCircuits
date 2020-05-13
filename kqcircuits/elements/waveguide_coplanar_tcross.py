# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element
from kqcircuits.defaults import default_circuit_params


class WaveguideCoplanarTCross(Element):
    """
  The PCell declaration of T-crossing of waveguides
  """

    PARAMETERS_SCHEMA = {
        "a2": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Width of the side waveguide",
            "default": default_circuit_params["a"]
        },
        "b2": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Gap of the side waveguide",
            "default": default_circuit_params["b"]
        },
        "length_extra": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Extra length",
            "default": 0
        },
        "length_extra_side": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Extra length of the side waveguide",
            "default": 0
        }
    }

    def __init__(self):
        super().__init__()

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "WaveguideT"

    def coerce_parameters_impl(self):
        None

    def can_create_from_shape_impl(self):
        return False

    def parameters_from_shape_impl(self):
        None

    def produce_impl(self):
        # Origin: Crossing of centers of the center conductors
        # Direction: Ports from left, right and bottom
        # Top gap

        l = self.length_extra
        l2 = self.length_extra_side
        a2 = self.a2
        b2 = self.b2
        a = self.a
        b = self.b

        pts = [
            pya.DPoint(-l - b2 - a2 / 2, a / 2 + 0),
            pya.DPoint(l + b2 + a2 / 2, a / 2 + 0),
            pya.DPoint(l + b2 + a2 / 2, a / 2 + b),
            pya.DPoint(-l - b2 - a2 / 2, a / 2 + b)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(shape)
        # Left gap
        pts = [
            pya.DPoint(-l - b2 - a2 / 2, -a / 2 + 0),
            pya.DPoint(-a2 / 2, -a / 2 + 0),
            pya.DPoint(-a2 / 2, -a / 2 - b - l2),
            pya.DPoint(-b2 - a2 / 2, -a / 2 - b - l2),
            pya.DPoint(-b2 - a2 / 2, -a / 2 - b),
            pya.DPoint(-l - b2 - a2 / 2, -a / 2 - b)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(shape)
        # Right gap
        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(pya.DTrans.M90 * shape)
        # Protection layer
        m = self.margin
        pts = [
            pya.DPoint(-l - b2 - a2 / 2 - m, a / 2 + b + m),
            pya.DPoint(l + b2 + a2 / 2 + m, a / 2 + b + m),
            pya.DPoint(l + b2 + a2 / 2 + m, -a / 2 - b - l2 - m),
            pya.DPoint(-l - b2 - a2 / 2 - m, -a / 2 - b - l2 - m),
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.layout.layer(self.face()["ground grid avoidance"])).insert(shape)

        # annotation text
        self.refpoints["port_left"] = pya.DPoint(-l - b2 - a2 / 2, 0)
        self.refpoints["port_right"] = pya.DPoint(l + b2 + a2 / 2, 0)
        self.refpoints["port_bottom"] = pya.DPoint(0, -a / 2 - b - l2)
        super().produce_impl()  # adds refpoints
