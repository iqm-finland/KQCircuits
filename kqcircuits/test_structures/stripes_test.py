# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

from kqcircuits.test_structures.test_structure import TestStructure


class StripesTest(TestStructure):
    """PCell declaration for optical lithography test stripes.

    Contains a given number of lines in `base metal gap wo grid`-layer with given width, length and spacing.
    There is also a text in `base metal gap wo grid`-layer next to the lines, which shows the line width.
    """

    PARAMETERS_SCHEMA = {
        "num_stripes": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Number of stripes",
            "default": 20
        },
        "stripe_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Width of the stripes [μm]",
            "default": 1
        },
        "stripe_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Length of the stripes [μm]",
            "default": 100
        },
        "stripe_spacing": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Spacing between the stripes [μm]",
            "default": 1
        }
    }

    def produce_impl(self):

        layer_base_metal = self.get_layer("base metal gap wo grid")

        stripe = pya.DBox(0, 0, self.stripe_width, self.stripe_length)

        for i in range(self.num_stripes):
            trans = pya.DTrans(i*(self.stripe_width + self.stripe_spacing), 0)
            self.cell.shapes(layer_base_metal).insert(trans * stripe)

        width_str = int(self.stripe_width) if self.stripe_width.is_integer() else self.stripe_width
        text_cell = self.layout.create_cell("TEXT", "Basic", {
            "layer": self.face()["base metal gap wo grid"],
            "text": "{}".format(width_str),
            "mag": 40,
        })
        text_x = self.num_stripes*(self.stripe_width + self.stripe_spacing) + self.stripe_width
        text_y = self.stripe_length/2
        self.insert_cell(text_cell, pya.DTrans(text_x, text_y))

        super().produce_impl()
