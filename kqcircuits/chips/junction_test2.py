# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import sys
from importlib import reload

from kqcircuits.pya_resolver import pya

from kqcircuits.chips.chip import Chip
from kqcircuits.test_structures.junction_test_pads import JunctionTestPads

reload(sys.modules[Chip.__module__])

version = 1


class JunctionTest2(Chip):
    """The PCell declaration for a JunctionTest2 chip."""

    PARAMETERS_SCHEMA = {
        "pad_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Pad Width (um)",
            "default": 500
        },
        "junctions_horizontal": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Horizontal (True) or vertical (False) junctions",
            "default": True
        },
        "squid_name": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "SQUID Type",
            "default": "QCD1"
        },
        "pad_spacing": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Spacing between different pad pairs (um)",
            "default": 100
        },
    }

    def __init__(self):
        super().__init__()

    def produce_impl(self):
        left = self.box.left
        right = self.box.right
        top = self.box.top

        junction_test_side = JunctionTestPads.create_cell(self.layout, {
            "pad_width": self.pad_width,
            "area_height": 6000,
            "area_width": 1700,
            "junctions_horizontal": self.junctions_horizontal,
            "squid_name": self.squid_name,
            "pad_spacing": self.pad_spacing,
        })
        junction_test_center = JunctionTestPads.create_cell(self.layout, {
            "pad_width": self.pad_width,
            "area_height": 9400,
            "area_width": 6000,
            "junctions_horizontal": self.junctions_horizontal,
            "squid_name": self.squid_name,
            "pad_spacing": self.pad_spacing,
        })

        self.insert_cell(junction_test_side, pya.DTrans(0, False, left + 300, top - 2000 - 6000), "testarray_1")
        self.insert_cell(junction_test_side, pya.DTrans(0, False, right - 300 - 1700, top - 2000 - 6000), "testarray_2")
        self.insert_cell(junction_test_center, pya.DTrans(0, False, left + 2000, top - 300 - 9400), "testarray_3")

        super().produce_impl()
