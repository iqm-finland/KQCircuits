# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.test_structures.test_structure import TestStructure
from kqcircuits.elements.f2f_connectors.tsvs.tsv import Tsv


class TsvTestPattern(TestStructure):
    """PCell declaration for TSV test structures which resembles a TSV fencing for a CPW transmission line.

    Contains a given number of TSVs in `through silioon via`-layer with given vertical, horizontal pitch,
    placeholder for CPW, diameter and the lateral profile of the TSV.
    """

    cpw_distance = Param(pdt.TypeDouble, "CPW Placeholder distance", 100, unit="μm")
    hor_distance = Param(pdt.TypeDouble, "Horizontal pitch on TSV", 200, unit="μm")
    ver_distance = Param(pdt.TypeDouble, "Vertical pitch on TSV", 500, unit="μm")
    tsv_diameter = Param(pdt.TypeDouble, "TSV diameter", 10, unit="μm")
    tsv_type = Param(pdt.TypeString, "TSV type", "circular", choices=[["circular", "circular"], ["oval", "oval"]])
    tsv_ellipse_width = Param(pdt.TypeDouble, "Oval TSV width", 30, unit="μm")
    tsv_array_form = Param(pdt.TypeList, "TSV test layout", [2, 6, 6, 2, 6, 6, 2])

    def produce_impl(self):
        tsv_unit = self.add_element(Tsv, tsv_diameter=self.tsv_diameter, tsv_type=self.tsv_type,
                                    tsv_elliptical_width=self.tsv_ellipse_width)
        for i, ind in enumerate(self.tsv_array_form):
            index_at_cpw_pos = int(ind) / 2
            for j in range(int(ind)):
                if j >= index_at_cpw_pos:
                    y_pos = (j - (index_at_cpw_pos - 1 / 2)) * self.hor_distance + self.cpw_distance / 2 + 100
                else:
                    y_pos = (j - (index_at_cpw_pos - 1 / 2)) * self.hor_distance - self.cpw_distance / 2 - 100
                x_pos = (i - (len(self.tsv_array_form) - 1) / 2) * self.ver_distance
                trans = pya.DTrans(x_pos, y_pos)
                self.insert_cell(tsv_unit, trans)

        super().produce_impl()
