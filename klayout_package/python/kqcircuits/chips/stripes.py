# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not, see
# https://www.gnu.org/licenses/gpl-3.0.html.
#
# The software distribution should follow IQM trademark policy for open-source software
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).


import numpy

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.chips.chip import Chip


class Stripes(Chip):
    """The PCell declaration for a Stripes chip."""

    edge_len = Param(pdt.TypeInt, "Length of square's one edge", 80)
    inter_space = Param(pdt.TypeInt, "Space in between the Squares", 20)
    axis = Param(pdt.TypeString, "The axis of the stripes", "Vertical")

    def build(self):

        # defining the dimensions for creating the polygonal area of test
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
        dice_width = float(self.frames_dice_width[0])

        # create the test area polygon
        poly = pya.DPolygon([
            pya.DPoint(left + p_left, bottom + 100 + dice_width),
            pya.DPoint(left + p_left, bottom + p_bottom),
            pya.DPoint(left + 100 + dice_width, bottom + p_bottom),
            pya.DPoint(left + 100 + dice_width, bottom + p_top),
            pya.DPoint(left + p_left, bottom + p_top),
            pya.DPoint(left + p_left, bottom + height - 100 - dice_width),
            pya.DPoint(left + p_right, bottom + height - 100 - dice_width),
            pya.DPoint(left + p_right, bottom + p_top),
            pya.DPoint(left + width - 100 - dice_width, bottom + p_top),
            pya.DPoint(left + width - 100 - dice_width, bottom + p_bottom),
            pya.DPoint(left + p_right, bottom + p_bottom),
            pya.DPoint(left + p_right, bottom + 100 + dice_width)
        ])

        # create the box array
        b_array = []

        square_y_reach = bottom + height
        square_x_start = left + 120
        square_x_reach = left + width - dice_width

        step = self.edge_len + self.inter_space
        stripe_step = step * 2

        if self.axis == "Vertical":
            stripe_start = left + dice_width + self.inter_space
            stripe_reach = left + width

            stripe_top_right_y = top - 20
            stripe_bottom_left_y = bottom + 20

            square_y_start = bottom + dice_width + self.inter_space

            square_y_step = step
            square_x_step = step * 2

        elif self.axis == "Horizontal":
            stripe_start = bottom + dice_width + self.inter_space
            stripe_reach = bottom + height

            stripe_top_right_x = right - 20
            stripe_bottom_left_x = left + 20

            square_y_start = bottom - 80

            square_y_step = step * 2
            square_x_step = step

        # creating the stripes for all of the ground grid
        for c in numpy.arange(stripe_start, stripe_reach, stripe_step):
            if self.axis == "Vertical":
                stripe_top_right_x = c + self.edge_len
                stripe_bottom_left_x = c

            elif self.axis == "Horizontal":
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

        for b in b_array:
            reg2.insert(b)

        result = reg1 - reg2
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(result)
