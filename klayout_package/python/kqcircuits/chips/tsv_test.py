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
from kqcircuits.chips.chip import Chip
from kqcircuits.test_structures.tsv_test_pattern import TsvTestPattern
from kqcircuits.elements.tsvs.tsv import Tsv
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.elements.tsvs.tsv_ellipse import TsvEllipse


@add_parameters_from(TsvEllipse, "*", tsv_diameter=10)
class TsvTest(Chip):
    """Through silicon via test chip.

    Consists of arrays of TSVs and metrology segment for crossectional analysis.
    """

    array_layout = Param(pdt.TypeList, "Array layout for TSV in center",
                         [2, 2, 2, 6, 14, 2, 14, 14, 2, 2, 14, 14, 2, 14, 6, 2, 2, 2])
    metrology_pitch = Param(pdt.TypeDouble, "Pitch in the metrology", 50, unit="μm")
    cpw_distance = Param(pdt.TypeDouble, "CPW Placeholder distance", 100, unit="μm")
    hor_distance = Param(pdt.TypeDouble, "Horizontal pitch on TSV", 200, unit="μm")
    ver_distance = Param(pdt.TypeDouble, "Vertical pitch on TSV", 500, unit="μm")

    def build(self):
        # create cell pattern in the center
        cell_pattern = self.add_element(TsvTestPattern, tsv_array_form=self.array_layout)
        self.insert_cell(cell_pattern, pya.DCplxTrans(1, 0, False, 5000, 5000))

        # metrology cell for crossectional analysis
        min_spacing = self.tsv_diameter if self.tsv_type == "standard" else max([self.tsv_diameter,
                                                                                 self.tsv_elliptical_width])
        self.create_xsection(position=pya.DPoint(1250, 1250), array_form=[10, 10],
                             pitch=self.metrology_pitch + min_spacing)
        self.create_xsection(position=pya.DPoint(1250, 8750), array_form=[8, 8],
                             pitch=self.metrology_pitch + 2 * min_spacing)
        self.create_xsection(position=pya.DPoint(8750, 1250), array_form=[6, 6], pitch=self.metrology_pitch + 2.5 *
                                                                                       min_spacing)

    def create_xsection(self, position, array_form, pitch):
        tsv_unit = self.add_element(Tsv)

        for i in range(array_form[0]):
            for j in range(array_form[1]):
                x_position = (i - array_form[0] / 2) * pitch + position.x
                y_position = (j - array_form[0] / 2) * pitch + position.y
                self.insert_cell(tsv_unit, pya.DCplxTrans(1, 0, False, x_position, y_position))
