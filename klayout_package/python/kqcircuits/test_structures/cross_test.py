# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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


from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.test_structures.test_structure import TestStructure


class CrossTest(TestStructure):
    """PCell declaration for optical lithography test alignment cross markers.

    Contains a given number of alignment cross markers in `base_metal_gap_wo_grid`-layer with given width, length and
     spacing.
    """

    num_crosses = Param(pdt.TypeInt, "Number of crosses", 10)
    cross_width = Param(pdt.TypeDouble, "Width of the crosses arms", 4, unit="μm")
    cross_length = Param(pdt.TypeDouble, "Length of the crosses", 15, unit="μm")
    cross_spacing = Param(pdt.TypeDouble, "Spacing between the crosses", 100, unit="μm")
    cross_box_distance = Param(pdt.TypeDouble, "Distance between crosses and respective boxes", 4, unit="μm")

    def build(self):

        layer_base_metal = self.get_layer("base_metal_gap_wo_grid")

        box = pya.DBox(pya.DPoint(-self.cross_width/2, -self.cross_box_distance), pya.DPoint(self.cross_width/2,
                                                                    -self.cross_box_distance - self.cross_width))
        vertical_tick = pya.DBox(pya.DPoint(-self.cross_width/2, 0), pya.DPoint(self.cross_width/2, self.cross_length))
        horizontal_tick = pya.DBox(pya.DPoint(-self.cross_length/2, self.cross_length/2 - self.cross_width/2),
                                   pya.DPoint(self.cross_length/2, self.cross_length/2 + self.cross_width/2))

        for i in range(self.num_crosses):
            trans = pya.DTrans(0, False, i*self.cross_spacing, 0).to_itype(self.layout.dbu)
            box_trans = pya.Region(trans * box.to_itype(self.layout.dbu))
            vertical_tick_trans = pya.Region(trans * vertical_tick.to_itype(self.layout.dbu))
            horizontal_tick_trans = pya.Region(trans * horizontal_tick.to_itype(self.layout.dbu))

            marker = box_trans + vertical_tick_trans + horizontal_tick_trans

            self.cell.shapes(layer_base_metal).insert(marker)
