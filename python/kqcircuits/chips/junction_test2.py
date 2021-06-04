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



from kqcircuits.util.parameters import Param, pdt

from kqcircuits.chips.chip import Chip
from kqcircuits.defaults import default_squid_type
from kqcircuits.pya_resolver import pya
from kqcircuits.squids import squid_type_choices
from kqcircuits.test_structures.junction_test_pads import JunctionTestPads


version = 1


class JunctionTest2(Chip):
    """The PCell declaration for a JunctionTest2 chip."""

    pad_width = Param(pdt.TypeDouble, "Pad Width", 500, unit="[μm]")
    junctions_horizontal = Param(pdt.TypeBoolean, "Horizontal (True) or vertical (False) junctions", True)
    squid_type = Param(pdt.TypeString, "SQUID Type", default_squid_type, choices=squid_type_choices)
    pad_spacing = Param(pdt.TypeDouble, "Spacing between different pad pairs", 100, unit="[μm]")

    def produce_impl(self):
        left = self.box.left
        right = self.box.right
        top = self.box.top

        junction_test_side = self.add_element(JunctionTestPads,
            pad_width=self.pad_width,
            area_height=6000,
            area_width=1700,
            junctions_horizontal=self.junctions_horizontal,
            junction_type="both",
            squid_type=self.squid_type,
            pad_spacing=self.pad_spacing,
        )
        junction_test_center = self.add_element(JunctionTestPads,
            pad_width=self.pad_width,
            area_height=9400,
            area_width=6000,
            junctions_horizontal=self.junctions_horizontal,
            junction_type="both",
            squid_type=self.squid_type,
            pad_spacing=self.pad_spacing,
        )

        self.insert_cell(junction_test_side, pya.DTrans(0, False, left + 300, top - 2000 - 6000), "testarray_1")
        self.insert_cell(junction_test_side, pya.DTrans(0, False, right - 300 - 1700, top - 2000 - 6000), "testarray_2")
        self.insert_cell(junction_test_center, pya.DTrans(0, False, left + 2000, top - 300 - 9400), "testarray_3")

        super().produce_impl()
