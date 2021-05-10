# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.test_structures.test_structure import TestStructure


class StripesTest(TestStructure):
    """PCell declaration for optical lithography test stripes.

    Contains a given number of lines in `base_metal_gap_wo_grid`-layer with given width, length and spacing.
    There is also a text in `base_metal_gap_wo_grid`-layer next to the lines, which shows the line width.
    """

    num_stripes = Param(pdt.TypeInt, "Number of stripes", 20)
    stripe_width = Param(pdt.TypeDouble, "Width of the stripes", 1, unit="μm")
    stripe_length = Param(pdt.TypeDouble, "Length of the stripes", 100, unit="μm")
    stripe_spacing = Param(pdt.TypeDouble, "Spacing between the stripes", 1, unit="μm")

    def produce_impl(self):

        layer_base_metal = self.get_layer("base_metal_gap_wo_grid")

        width = float(self.stripe_width)
        stripe = pya.DBox(0, 0, width, self.stripe_length)

        for i in range(self.num_stripes):
            trans = pya.DTrans(i*(width + self.stripe_spacing), 0)
            self.cell.shapes(layer_base_metal).insert(trans * stripe)

        width_str = int(width) if width.is_integer() else width
        text_cell = self.layout.create_cell("TEXT", "Basic", {
            "layer": self.face()["base_metal_gap_wo_grid"],
            "text": "{}".format(width_str),
            "mag": 40,
        })
        text_x = self.num_stripes*(width + self.stripe_spacing) + width
        text_y = self.stripe_length/2
        self.insert_cell(text_cell, pya.DTrans(text_x, text_y))

        super().produce_impl()
