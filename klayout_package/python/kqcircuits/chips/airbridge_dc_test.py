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


from kqcircuits.chips.chip import Chip
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.test_structures.airbridge_dc import AirbridgeDC


class AirbridgeDcTest(Chip):
    """Chip full of airbridge 4-point dc tests."""

    n_step = Param(pdt.TypeInt, "Increment step for number of airbridges", 1)
    test_width = Param(pdt.TypeDouble, "Width of a single test", 2000, unit="μm")

    def build(self):

        d1 = float(self.frames_dice_width[0]) + self.dice_grid_margin # smaller distance of test area from chip edge
        d2 = 2000  # larger distance of test area from chip edge
        chip_size = self.box.width()

        n_ab = self.n_step
        test_id = 0

        n_ab, test_id = self._produce_tests_within_box(pya.DBox(d2, chip_size - d2, chip_size - d2, chip_size - d1),
                                                       n_ab, test_id)
        n_ab, test_id = self._produce_tests_within_box(pya.DBox(d1, d2, chip_size - d1, chip_size - d2), n_ab, test_id)
        n_ab, test_id = self._produce_tests_within_box(pya.DBox(d2, d1, chip_size - d2, d2), n_ab, test_id)

    def _produce_tests_within_box(self, box, n_ab, test_id):

        num_horizontal = int(box.width()//self.test_width)
        x_start = box.left + (box.width() - self.test_width*num_horizontal)/2  # to make them horizontally centered
        x = x_start
        y = box.top

        while y > box.bottom:

            while x < box.right:

                cell = self.add_element(AirbridgeDC, n_ab=n_ab, width=self.test_width)
                test_height = cell.dbbox_per_layer(self.get_layer("base_metal_gap_wo_grid")).height()
                num_vertical = int(box.height()//test_height)  # assuming test_height same for all tests
                y_offset = (box.height() - test_height*num_vertical)/2  # to make them vertically centered

                trans = pya.DTrans(pya.DVector(x + self.test_width/2, y - y_offset - test_height/2))

                x += self.test_width
                if x > box.right or y - test_height < box.bottom:
                    break

                label_trans = pya.DCplxTrans(0.8, 0, False, -self.test_width/2, 0)
                self.insert_cell(cell, trans, "test_{}".format(test_id), label_trans)

                n_ab += self.n_step
                test_id += 1

            x = x_start
            y -= test_height

        return n_ab, test_id
