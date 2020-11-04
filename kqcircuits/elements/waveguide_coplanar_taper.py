# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import math

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element
from kqcircuits.defaults import default_circuit_params, default_layers
from math import ceil


class WaveguideCoplanarTaper(Element):
    """The PCell declaration of a taper segment of a coplanar waveguide."""

    PARAMETERS_SCHEMA = {
        "taper_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Taper length [μm]",
            "default": 10 * math.pi
        },
        "a1": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Width of left waveguide center conductor [μm]",
            "default": default_circuit_params["a"]
        },
        "b1": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Width of left waveguide gap [μm]",
            "default": default_circuit_params["b"]
        },
        "m1": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Margin of left waveguide protection layer [μm]",
            "default": 5
        },
        "a2": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Width of right waveguide center conductor [μm]",
            "default": default_circuit_params["a"] * 2
        },
        "b2": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Width of right waveguide gap [μm]",
            "default": default_circuit_params["b"] * 2
        },
        "m2": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Margin of right waveguide protection layer [μm]",
            "default": 5 * 2
        },
    }

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
        self.cell.shapes(self.get_layer("base metal gap wo grid")).insert(shape)
        # gap 2
        pts = [
            pya.DPoint(0, -self.a1 / 2 + 0),
            pya.DPoint(self.taper_length, -self.a2 / 2 + 0),
            pya.DPoint(self.taper_length, -self.a2 / 2 - self.b2),
            pya.DPoint(0, -self.a1 / 2 - self.b1)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("base metal gap wo grid")).insert(shape)
        # Protection layer
        pts = [
            pya.DPoint(0, -self.a1 / 2 - self.b1 - self.m1),
            pya.DPoint(self.taper_length, -self.a2 / 2 - self.b2 - self.m2),
            pya.DPoint(self.taper_length, self.a2 / 2 + self.b2 + self.m2),
            pya.DPoint(0, self.a1 / 2 + self.b1 + self.m1)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("ground grid avoidance")).insert(shape)
        # Annotation
        pts = [
            pya.DPoint(0, 0),
            pya.DPoint(self.taper_length, 0),
        ]
        shape = pya.DPath(pts, ceil(self.a1 + 2 * self.b1))
        self.cell.shapes(self.get_layer("annotations")).insert(shape)
        # refpoints for connecting to waveguides
        self.add_port("a", pya.DPoint(0, 0))
        self.add_port("b", pya.DPoint(self.taper_length, 0))
        # adds annotation based on refpoints calculated above
        super().produce_impl()

