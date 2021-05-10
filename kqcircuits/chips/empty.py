# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.chips.chip import Chip
from kqcircuits.pya_resolver import pya


class Empty(Chip):
    """Chip with almost all ground metal removed, used for EBL tests."""

    def produce_impl(self):

        d1 = self.dice_width + self.dice_grid_margin
        d2 = 2000

        empty_area = pya.DPolygon([
            pya.DPoint(d1, d2),
            pya.DPoint(d1, 10000 - d2),
            pya.DPoint(d2, 10000 - d2),
            pya.DPoint(d2, 10000 - d1),
            pya.DPoint(10000-d2, 10000 - d1),
            pya.DPoint(10000-d2, 10000 - d2),
            pya.DPoint(10000-d1, 10000 - d2),
            pya.DPoint(10000-d1, d2),
            pya.DPoint(10000-d2, d2),
            pya.DPoint(10000-d2, d1),
            pya.DPoint(d2, d1),
            pya.DPoint(d2, d2),
        ])

        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(empty_area)
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(empty_area)

        super().produce_impl()
