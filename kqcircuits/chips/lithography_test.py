# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import sys
import numpy

from kqcircuits.pya_resolver import pya

from kqcircuits.chips.chip import Chip
from kqcircuits.test_structures.stripes_test import StripesTest


class LithographyTest(Chip):
    """Optical lithography test chip.

    Consists of StripesTest cells with different parameters.
    """

    def produce_impl(self):
        cell_horizontal_1, cell_vertical_1, cell_diagonal_1 = self.create_pattern(num_stripes=20, length=100,
                                                                                  min_width=1,
                                                                                  max_width=15, step=1, spacing=1,
                                                                                  face_id=['b'])
        cell_horizontal_2, cell_vertical_2, cell_diagonal_2 = self.create_pattern(num_stripes=20, length=100,
                                                                                  min_width=1,
                                                                                  max_width=15, step=1, spacing=5,
                                                                                  face_id=['b'])
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

        super().produce_impl()

    def create_pattern(self, num_stripes, length, min_width, max_width, step, spacing, face_id):
        first_stripes_width = 2 * num_stripes * min_width
        cell_horizontal = self.layout.create_cell("Stripes")
        cell_vertical = self.layout.create_cell("Stripes")
        cell_diagonal = self.layout.create_cell("Stripes")

        for i, width in enumerate(numpy.arange(min_width, max_width + 0.1 * step, step)):
            stripes_cell = self.add_element(StripesTest, num_stripes=num_stripes, stripe_width=width,
                                            stripe_length=length, stripe_spacing=spacing * width, face_ids=face_id)

            # horizontal
            cell_horizontal.insert(pya.DCellInstArray(stripes_cell.cell_index(),
                                                      pya.DCplxTrans(1, 0, False, 0, 2 * i * length +
                                                                     first_stripes_width)))
            # vertical
            cell_vertical.insert(pya.DCellInstArray(stripes_cell.cell_index(),
                                                    pya.DCplxTrans(1, 90, False, 2 * i * length + length +
                                                                   first_stripes_width, 0)))
            # diagonal
            diag_offset = 0  # 2*num_stripes*width/numpy.sqrt(8)
            cell_diagonal.insert(pya.DCellInstArray(stripes_cell.cell_index(),
                                                    pya.DCplxTrans(1, -45, False, 500 + i * length - diag_offset,
                                                                   500 + i * length + diag_offset)))

        return cell_horizontal, cell_vertical, cell_diagonal
