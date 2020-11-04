# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import sys
import numpy
from importlib import reload

from kqcircuits.pya_resolver import pya

from kqcircuits.chips.chip import Chip

reload(sys.modules[Chip.__module__])

version = 1


class Stripes(Chip):
    """The PCell declaration for a Stripes chip."""

    PARAMETERS_SCHEMA = {
        "edge_len": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Length of square's one edge",
            "default": 80
        },
        "inter_space": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Space in between the Squares",
            "default": 20
        },
        "axis": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "The axis of the stripes",
            "default": "Vertical"
        }
    }

    def produce_impl(self):

        # defining the dimensions for creating the polygonal area of test
        edge_len = self.edge_len
        inter_space = self.inter_space

        left = self.box.left
        right = self.box.right
        top = self.box.top
        bottom = self.box.bottom

        # dimensions for the hole on the ground plane
        p_top = 8000
        p_bottom = 2000
        p_left = 2000
        p_right = 8000

        width = right - left
        height = top - bottom

        p_width = p_right - p_left
        p_height = p_top - p_bottom

        # create the test area polygon
        poly = pya.DPolygon([
            pya.DPoint(left + p_left, bottom + 100 + self.dice_width),
            pya.DPoint(left + p_left, bottom + p_bottom),
            pya.DPoint(left + 100 + self.dice_width, bottom + p_bottom),
            pya.DPoint(left + 100 + self.dice_width, bottom + p_top),
            pya.DPoint(left + p_left, bottom + p_top),
            pya.DPoint(left + p_left, bottom + height - 100 - self.dice_width),
            pya.DPoint(left + p_right, bottom + height - 100 - self.dice_width),
            pya.DPoint(left + p_right, bottom + p_top),
            pya.DPoint(left + width - 100 - self.dice_width, bottom + p_top),
            pya.DPoint(left + width - 100 - self.dice_width, bottom + p_bottom),
            pya.DPoint(left + p_right, bottom + p_bottom),
            pya.DPoint(left + p_right, bottom + 100 + self.dice_width)
        ])

        # create the box array
        b_array = []
        t = 0

        square_y_reach = bottom + height
        square_x_start = left + 120
        square_x_reach = left + width - self.dice_width

        step = self.edge_len + self.inter_space
        stripe_step = step * 2

        if (self.axis == "Vertical"):
            stripe_start = left + self.dice_width + self.inter_space
            stripe_reach = left + width

            stripe_top_right_y = top - 20
            stripe_bottom_left_y = bottom + 20

            square_y_start = bottom + self.dice_width + self.inter_space

            square_y_step = step
            square_x_step = step * 2

        elif (self.axis == "Horizontal"):
            stripe_start = bottom + self.dice_width + self.inter_space
            stripe_reach = bottom + height

            stripe_top_right_x = right - 20
            stripe_bottom_left_x = left + 20

            square_y_start = bottom - 80

            square_y_step = step * 2
            square_x_step = step

        # creating the stripes for all of the ground grid
        for c in numpy.arange(stripe_start, stripe_reach, stripe_step):
            if (self.axis == "Vertical"):
                stripe_top_right_x = c + self.edge_len
                stripe_bottom_left_x = c

            elif (self.axis == "Horizontal"):
                stripe_top_right_y = c + self.edge_len
                stripe_bottom_left_y = c

            r = pya.DPolygon(
                pya.DBox(stripe_bottom_left_x, stripe_bottom_left_y, stripe_top_right_x, stripe_top_right_y)).to_itype(
                self.layout.dbu)
            b_array.append(r)

        # creating the squares for all of the ground grid
        for y in numpy.arange(square_y_start, square_y_reach, square_y_step):
            for x in numpy.arange(square_x_start, square_x_reach, square_x_step):
                b = pya.DPolygon(pya.DBox(x, y, x + self.edge_len, y + self.edge_len)).to_itype(self.layout.dbu)
                b_array.append(b)

        # substract the box array from the polygon
        reg1 = pya.Region(poly.to_itype(self.layout.dbu))
        reg2 = pya.Region()

        for i in range(0, len(b_array)):
            reg2.insert(b_array[i])

        result = reg1 - reg2
        self.cell.shapes(self.get_layer("base metal gap wo grid")).insert(result)

        super().produce_impl()
