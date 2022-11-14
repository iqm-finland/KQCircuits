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


class Empty(Chip):
    """Chip with almost all ground metal removed, used for EBL tests."""

    def make_empty_area(self):
        d1 = float(self.frames_dice_width[0]) + self.dice_grid_margin
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

        return empty_area

    def build(self):
        empty_area = self.make_empty_area()
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(empty_area)
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(empty_area)
