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

from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.elements.chip_frame import ChipFrame
from kqcircuits.chips.chip import Chip
from kqcircuits.pya_resolver import pya
from kqcircuits.test_structures.junction_test_pads.junction_test_pads import JunctionTestPads
from kqcircuits.junctions.junction import Junction


@add_parameters_from(JunctionTestPads, "*", "loop_area", "junction_width", pad_spacing=200)
@add_parameters_from(Junction, "junction_type")
@add_parameters_from(ChipFrame, "marker_types")
class JunctionTest2(Chip):
    """The PCell declaration for a JunctionTest2 chip."""

    pad_width = Param(pdt.TypeDouble, "Pad Width", 500, unit="μm")
    junctions_horizontal = Param(pdt.TypeBoolean, "Horizontal (True) or vertical (False) junctions", True)
    small_loop_area = Param(pdt.TypeDouble, "Test SQUIDs small loop area",
                                 default=80, unit="μm")
    large_loop_area = Param(pdt.TypeDouble, "Test SQUIDs large loop area",
                                 default=130, unit="μm")
    junction_width_small = Param(pdt.TypeDouble, "Test SQUIDs Junction finger width starting value (small loop)",
                                      default=0.15, unit="μm")
    junction_width_large = Param(pdt.TypeDouble, "Test SQUIDs Junction finger width starting value (large loop)",
                                      default=0.08, unit="μm")
    junction_width_step_increment_small = Param(pdt.TypeDouble, "Junction finger width step increment (small loop)",
                                                default=0.01, unit="μm")
    junction_width_step_increment_large = Param(pdt.TypeDouble, "Junction finger width step increment (large loop)",
                                                default=0.03, unit="μm")
    pads_loop = Param(pdt.TypeList, "Select large or small loop area for each central test pad",
                      default=["large", "large", "small", "small", "small", "large"])

    def coerce_parameters_impl(self):
        self.sync_parameters(JunctionTestPads)

    def build(self):
        left = self.box.left
        right = self.box.right
        top = self.box.top

        arrays_coordinates = [(left + 300, top - 2000 - 6000), (left + 2000, top - 300 - 9400),
                                   (left + 2000 + 2*(self.pad_spacing+ self.pad_width), top - 300 - 9400),
                                   (left + 2000 + 4*(self.pad_spacing + self.pad_width),
                                    top - 300 - 9400), (left + 2000 + 6*(self.pad_spacing + self.pad_width), top - 300
                                    - 9400), (right - 300 - 1700, top - 2000 - 6000)]
        area_height = [6000, 9400, 9400, 9400, 9400, 6000]
        squid_indexing_small = 0
        squid_indexing_large = 0
        name = "testarray"

        for j,array_coordinates in enumerate(arrays_coordinates):

            squids_per_test_array = area_height[j] // (self.pad_spacing + self.pad_width)

            if self.pads_loop[j] == "small":
                junction_width_starting_value = self.junction_width_small + squid_indexing_small * \
                                                self.junction_width_step_increment_small

                squid_indexing_small += squids_per_test_array
                junction_width_steps = [junction_width_starting_value, self.junction_width_step_increment_small]
                loop_area = self.small_loop_area

            else:
                junction_width_starting_value = self.junction_width_large + squid_indexing_large * \
                                                self.junction_width_step_increment_large

                squid_indexing_large += squids_per_test_array
                junction_width_steps = [junction_width_starting_value, self.junction_width_step_increment_large]
                loop_area = self.large_loop_area

            cell = self.add_element(JunctionTestPads,
                                margin=20,
                                area_height=area_height[j],
                                area_width=3*self.pad_spacing + 2*self.pad_width,
                                pad_width=self.pad_width,
                                junction_width_steps=junction_width_steps,
                                loop_area =loop_area,
                                only_arms=True,
                                )
            self.insert_cell(cell, pya.DTrans(0, False, array_coordinates[0], array_coordinates[1]),
                             name + "_{}".format(j+1))
