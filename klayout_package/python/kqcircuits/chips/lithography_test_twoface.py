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


from kqcircuits.chips.lithography_test import LithographyTest
from kqcircuits.chips.chip import Chip
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import add_parameters_from

@add_parameters_from(Chip, frames_enabled=[0, 1])
class LithographyTestTwoface(Chip):
    """Optical lithography test chip in a flip chip architecture.

    Consists of StripesTest cells with different parameters.
    """
    create_pattern = LithographyTest.create_pattern

    def build(self):
        cell_horizontal_1, cell_vertical_1, cell_diagonal_1 = self.create_pattern(num_stripes=20, length=100,
                                                                                  min_width=1,
                                                                                  max_width=15, step=1, spacing=1,
                                                                                  face_id=self.face_ids[0])
        cell_horizontal_2, cell_vertical_2, cell_diagonal_2 = self.create_pattern(num_stripes=20, length=100,
                                                                                  min_width=1,
                                                                                  max_width=15, step=1, spacing=5,
                                                                                  face_id=self.face_ids[0])
        cell_horizontal_3, cell_vertical_3, cell_diagonal_3 = self.create_pattern(num_stripes=20, length=100,
                                                                                  min_width=1,
                                                                                  max_width=15, step=1, spacing=1,
                                                                                  face_id=self.face_ids[1])
        cell_horizontal_4, cell_vertical_4, cell_diagonal_4 = self.create_pattern(num_stripes=20, length=100,
                                                                                  min_width=1,
                                                                                  max_width=15, step=1, spacing=5,
                                                                                  face_id=self.face_ids[1])
        # bottom patterns
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
        # top patterns
        self.insert_cell(cell_horizontal_3, pya.DCplxTrans(1, 0, False, 5900, 4000) * pya.DCplxTrans.M90)
        self.insert_cell(cell_horizontal_4, pya.DCplxTrans(1, 0, False, 8000, 4000) * pya.DCplxTrans.M90)
        self.insert_cell(cell_vertical_3, pya.DCplxTrans(1, 0, False, 5000, 6200) * pya.DCplxTrans.M90)
        self.insert_cell(cell_vertical_4, pya.DCplxTrans(1, 0, False, 5000, 4000) * pya.DCplxTrans.M90)
        self.insert_cell(cell_diagonal_3, pya.DCplxTrans(1, 0, False, 7500, 1800) * pya.DCplxTrans.M90)
        self.insert_cell(cell_diagonal_4, pya.DCplxTrans(1, 0, False, 6200, 1800) * pya.DCplxTrans.M90)
