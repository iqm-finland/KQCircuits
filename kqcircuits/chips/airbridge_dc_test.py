# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.chips.chip import Chip
from kqcircuits.pya_resolver import pya
from kqcircuits.test_structures.airbridge_dc import AirbridgeDC


class AirbridgeDcTest(Chip):
    """Chip full of airbridge 4-point dc tests."""

    PARAMETERS_SCHEMA = {
        "n_step": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Increment step for number of airbridges",
            "default": 1
        },
        "test_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Width of a single test [μm]",
            "default": 2000
        },
    }

    def produce_impl(self):

        d1 = self.dice_width + self.dice_grid_margin  # smaller distance of test area from chip edge
        d2 = 2000  # larger distance of test area from chip edge
        chip_size = self.box.width()

        n_ab = self.n_step
        test_id = 0

        n_ab, test_id = self._produce_tests_within_box(pya.DBox(d2, chip_size - d2, chip_size - d2, chip_size - d1),
                                                       n_ab, test_id)
        n_ab, test_id = self._produce_tests_within_box(pya.DBox(d1, d2, chip_size - d1, chip_size - d2), n_ab, test_id)
        n_ab, test_id = self._produce_tests_within_box(pya.DBox(d2, d1, chip_size - d2, d2), n_ab, test_id)

        super().produce_impl()

    def _produce_tests_within_box(self, box, n_ab, test_id):

        num_horizontal = int(box.width()//self.test_width)
        x_start = box.left + (box.width() - self.test_width*num_horizontal)/2  # to make them horizontally centered
        x = x_start
        y = box.top

        while y > box.bottom:

            while x < box.right:

                cell = self.add_element(AirbridgeDC, n_ab=n_ab, width=self.test_width)
                test_height = cell.dbbox_per_layer(self.get_layer("base metal gap wo grid")).height()
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
