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


from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.test_structures.test_structure import TestStructure
from kqcircuits.elements.tsvs.tsv import Tsv
from kqcircuits.elements.tsvs.tsv_ellipse import TsvEllipse


@add_parameters_from(TsvEllipse, "*", tsv_diameter=10)
class TsvTestPattern(TestStructure):
    """PCell declaration for TSV test structures which resembles a TSV fencing for a CPW transmission line.

    Contains a given number of TSVs in `through silicon via`-layer with given vertical, horizontal pitch,
    placeholder for CPW, diameter and the lateral profile of the TSV.
    """

    cpw_distance = Param(pdt.TypeDouble, "CPW Placeholder distance", 100, unit="μm")
    hor_distance = Param(pdt.TypeDouble, "Horizontal pitch on TSV", 200, unit="μm")
    ver_distance = Param(pdt.TypeDouble, "Vertical pitch on TSV", 500, unit="μm")
    tsv_array_form = Param(pdt.TypeList, "TSV test layout", [2, 6, 6, 2, 6, 6, 2])

    def build(self):
        tsv_unit = self.add_element(Tsv)
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
