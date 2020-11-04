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
    """The PCell declaration of T-crossing of waveguides."""

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

        port_l_location_x = -l - b2 - a2 / 2
        port_r_location_x = l + b2 + a2 / 2
        pts = [
            pya.DPoint(port_l_location_x, a / 2 + 0),
            pya.DPoint(port_r_location_x, a / 2 + 0),
            pya.DPoint(port_r_location_x, a / 2 + b),
            pya.DPoint(port_l_location_x, a / 2 + b)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("base metal gap wo grid")).insert(shape)
        # Left gap
        port_bottom_location_y = -a / 2 - b - l2
        pts = [
            pya.DPoint(port_l_location_x, -a / 2 + 0),
            pya.DPoint(-a2 / 2, -a / 2 + 0),
            pya.DPoint(-a2 / 2, port_bottom_location_y),
            pya.DPoint(-b2 - a2 / 2, port_bottom_location_y),
            pya.DPoint(-b2 - a2 / 2, -a / 2 - b),
            pya.DPoint(port_l_location_x, -a / 2 - b)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("base metal gap wo grid")).insert(shape)
        # Right gap
        self.cell.shapes(self.get_layer("base metal gap wo grid")).insert(pya.DTrans.M90 * shape)
        # Protection layer
        m = self.margin
        pts = [
            pya.DPoint(port_l_location_x - m, a / 2 + b + m),
            pya.DPoint(port_r_location_x + m, a / 2 + b + m),
            pya.DPoint(port_r_location_x + m, port_bottom_location_y - m),
            pya.DPoint(port_l_location_x - m, port_bottom_location_y - m),
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("ground grid avoidance")).insert(shape)

        # refpoints text
        self.add_port("left", pya.DPoint(port_l_location_x, 0), pya.DVector(-1, 0))
        self.add_port("right", pya.DPoint(port_r_location_x, 0), pya.DVector(1, 0))
        self.add_port("bottom", pya.DPoint(0, port_bottom_location_y), pya.DVector(0, -1))

        # annotation path
        self.cell.shapes(self.get_layer("annotations")).insert(
            pya.DPath([self.refpoints["port_left"], self.refpoints["base"]], self.a)
        )
        self.cell.shapes(self.get_layer("annotations")).insert(
            pya.DPath([self.refpoints["port_right"], self.refpoints["base"]], self.a)
        )
        self.cell.shapes(self.get_layer("annotations")).insert(
            pya.DPath([self.refpoints["port_bottom"], self.refpoints["base"]], self.a)
        )

        super().produce_impl()  # adds refpoints
