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


class JunctionTest(Chip):
    """The PCell declaration for a JunctionTest chip."""

    edge_len = Param(pdt.TypeInt, "Length of square's one edge", 80)
    inter_space = Param(pdt.TypeInt, "Space in between the Squares", 20)

    def build(self):

        # defining the parameters for local use

        left = self.box.left
        right = self.box.right
        top = self.box.top
        bottom = self.box.bottom

        width = right - left
        height = top - bottom
        dice_width = float(self.frames_dice_width[0])

        # create the polygon
        poly = pya.DPolygon([
            pya.DPoint(left + 2000, bottom + 100 + dice_width),
            pya.DPoint(left + 2000, bottom + 2000),
            pya.DPoint(left + 100 + dice_width, bottom + 2000),
            pya.DPoint(left + 100 + dice_width, bottom + 8000),
            pya.DPoint(left + 2000, bottom + 8000),
            pya.DPoint(left + 2000, bottom + height - 100 - dice_width),
            pya.DPoint(left + 8000, bottom + height - 100 - dice_width),
            pya.DPoint(left + 8000, bottom + 8000),
            pya.DPoint(left + width - 100 - dice_width, bottom + 8000),
            pya.DPoint(left + width - 100 - dice_width, bottom + 2000),
            pya.DPoint(left + 8000, bottom + 2000),
            pya.DPoint(left + 8000, bottom + 100 + dice_width)
        ])

        # create the box array
        b_array = []

        for y in numpy.arange(bottom + dice_width + self.inter_space, bottom + height - dice_width,
                              self.edge_len + self.inter_space):
            for x in numpy.arange(left + dice_width + self.inter_space, left + width - dice_width,
                                  self.edge_len + self.inter_space):
                b = pya.DPolygon(pya.DBox(x, y, x + self.edge_len, y + self.edge_len)).to_itype(self.layout.dbu)
                b_array.append(b)

        # substract the box array from the polygon
        reg1 = pya.Region(poly.to_itype(self.layout.dbu))
        reg2 = pya.Region()

        for b in b_array:
            reg2.insert(b)

        result = reg1 - reg2
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(result)
