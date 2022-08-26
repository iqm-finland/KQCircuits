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

from kqcircuits.chips.chip import Chip
from kqcircuits.test_structures.stripes_test import StripesTest
from kqcircuits.test_structures.cross_test import CrossTest


class LithographyTest(Chip):
    """Optical lithography test chip.

    Consists of StripesTest cells with different parameters.
    """

    def build(self):
        cell_horizontal_1, cell_vertical_1, cell_diagonal_1 = self.create_pattern(num_stripes=20, length=100,
                                                                                  min_width=1,
                                                                                  max_width=15, step=1, spacing=1,
                                                                                  face_id=self.face_ids[0])
        cell_horizontal_2, cell_vertical_2, cell_diagonal_2 = self.create_pattern(num_stripes=20, length=100,
                                                                                  min_width=1,
                                                                                  max_width=15, step=1, spacing=5,
                                                                                  face_id=self.face_ids[0])
        self.insert_cell(cell_horizontal_1, pya.DCplxTrans(1, 0, False, 2000, 6500))
        self.insert_cell(cell_horizontal_1, pya.DCplxTrans(1, 0, False, 3000, 6500))
        self.insert_cell(cell_horizontal_2, pya.DCplxTrans(1, 0, False, 4000, 6500))
        self.insert_cell(cell_horizontal_2, pya.DCplxTrans(1, 0, False, 6000, 6500))
        self.insert_cell(cell_vertical_1, pya.DCplxTrans(1, 0, False, 1500, 5700))
        self.insert_cell(cell_vertical_1, pya.DCplxTrans(1, 0, False, 5500, 5700))
        self.insert_cell(cell_vertical_2, pya.DCplxTrans(1, 0, False, 1500, 3800))
        self.insert_cell(cell_vertical_2, pya.DCplxTrans(1, 0, False, 5500, 3800))
        self.insert_cell(cell_diagonal_1, pya.DCplxTrans(1, 0, False, 400, 1500))
        self.insert_cell(cell_diagonal_1, pya.DCplxTrans(1, 0, False, 1500, 1500))
        self.insert_cell(cell_diagonal_2, pya.DCplxTrans(1, 0, False, 3100, 1500))
        self.insert_cell(cell_diagonal_2, pya.DCplxTrans(1, 0, False, 6100, 1500))

    def create_pattern(self, num_stripes, length, min_width, max_width, step, spacing, face_id):
        first_stripes_width = 2 * num_stripes * min_width
        cell_horizontal = self.layout.create_cell("Stripes")
        cell_vertical = self.layout.create_cell("Stripes")
        cell_diagonal = self.layout.create_cell("Stripes")

        for i, width in enumerate(numpy.arange(min_width, max_width + 0.1 * step, step)):
            stripes_cell = self.add_element(StripesTest, num_stripes=num_stripes, stripe_width=width,
                                            stripe_length=length, stripe_spacing=spacing * width, face_ids=[face_id])

            # calculate the number of cross alignment marker
            if (num_stripes*(width + spacing * width) - spacing * width - 45) % 100 < 50:
                num_crosses = (num_stripes * (width + spacing * width) - spacing * width - 45)//100 + 1
            else:
                num_crosses = (num_stripes * (width + spacing * width) - spacing * width - 45)//100 + 2

            cross_cell = self.add_element(CrossTest, num_crosses=int(num_crosses), cross_spacing=100,
                                          face_ids=[face_id])

            # horizontal
            cell_horizontal.insert(pya.DCellInstArray(stripes_cell.cell_index(),
                                                      pya.DCplxTrans(1, 0, False, 0, 2 * i * length +
                                                            first_stripes_width)))
            cell_horizontal.insert(pya.DCellInstArray(cross_cell.cell_index(),
                                                      pya.DCplxTrans(1, 0, False, 45, 2 * i * length +
                                                            first_stripes_width - CrossTest.cross_length*5/2)))
            # vertical
            cell_vertical.insert(pya.DCellInstArray(stripes_cell.cell_index(),
                                                      pya.DCplxTrans(1, 90, False, 2 * i * length + length +
                                                            first_stripes_width, 0)))
            cell_vertical.insert(pya.DCellInstArray(cross_cell.cell_index(),
                                                      pya.DCplxTrans(1, 90, True, 2 * i * length + length +
                                                    first_stripes_width - length - CrossTest.cross_length*5/2, +45)))
            # diagonal
            diag_offset = 0  # 2*num_stripes*width/numpy.sqrt(8)
            cell_diagonal.insert(pya.DCellInstArray(stripes_cell.cell_index(),
                                                      pya.DCplxTrans(1, -45, False, 500 + i * length - diag_offset,
                                                            500 + i * length + diag_offset)))

        return cell_horizontal, cell_vertical, cell_diagonal
