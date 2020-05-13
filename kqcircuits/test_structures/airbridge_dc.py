# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import sys
from importlib import reload

from kqcircuits.pya_resolver import pya

from kqcircuits.test_structures.test_structure import TestStructure
from kqcircuits.elements.airbridge import Airbridge
from kqcircuits.defaults import default_layers

reload(sys.modules[TestStructure.__module__])


class AirbridgeDC(TestStructure):
    """The PCell declaration for a DC Airbridge."""
    version = 2

    PARAMETERS_SCHEMA = {
        "lo2": {
            "type": pya.PCellParameterDeclaration.TypeLayer,
            "description": "AB bottom layer",
            "default": default_layers["b airbridge pads"]
        },
        "lo3": {
            "type": pya.PCellParameterDeclaration.TypeLayer,
            "description": "AB top layer",
            "default": default_layers["b airbridge flyover"]
        },
        "n": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Number of AB",
            "default": 10
        },
        "pad_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Pad width (um)",
            "default": 30
        },
        "pad_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Pad length (um)",
            "default": 10
        },
        "pad_extra": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Bottom pad extra (um)",
            "default": 1
        },
        "bridge_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Bridge width (um)",
            "default": 8
        },
        "bridge_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Bridge length (from pad to pad) (um)",
            "default": 40
        }
    }

    def __init__(self):
        super().__init__()

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return ("AB_DC_Test")

    def coerce_parameters_impl(self):
        None

    def can_create_from_shape_impl(self):
        return self.shape.is_box()

    def parameters_from_shape_impl(self):
        None

    def transformation_from_shape_impl(self):
        return pya.Trans()

    def produce_impl(self):
        cell_ab = Airbridge.create_cell(self.layout, {
            "pad_width": self.pad_width,
            "pad_length": self.pad_length,
            "bridge_length": self.bridge_length,
            "bridge_width": self.bridge_width,
            "pad_extra": self.pad_extra
        })

        # shorthand
        w = self.pad_width
        h = self.pad_length
        l = self.bridge_length
        b = self.bridge_width
        e = self.pad_extra

        m = 2  # margin for bottom Nb layer
        step = l + 2 * h + 2 * e + m

        island = pya.DPolygon([
            pya.DPoint(-w - m, -h - 2 * m),
            pya.DPoint(w + m, -h - 2 * m),
            pya.DPoint(w + m, 0),
            pya.DPoint(-w - m, 0),
        ])
        lu = self.layout.layer(default_layers["b base metal addition"])
        for i in range(int(self.n)):
            self.cell.shapes(lu).insert(pya.DTrans(2, False, pya.DVector(0, (i - 1) * step)) * island)
            self.cell.shapes(lu).insert(pya.DTrans(0, False, pya.DVector(0, i * step)) * island)
            self.insert_cell(cell_ab, pya.DTrans(0, False, pya.DVector(0, (i - 0.5) * step)))
