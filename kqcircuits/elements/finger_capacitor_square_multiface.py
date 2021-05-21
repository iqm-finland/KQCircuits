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


from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt


class FingerCapacitorSquareMultiface(FingerCapacitorSquare):
    """The PCell declaration for a square finger capacitor with opened ground plane on opposite face.

    Two ports with reference points. The arm leading to the finger has the same width as fingers. The feedline has
    the same length as the width of the ground gap around the coupler. Ground avoidance layer around the capacitor also
    on face 1.
    """

    margin_other_face = Param(pdt.TypeDouble, "Margin for the opening on the other face", 20, unit="μm")

    def produce_impl(self):

        region_ground = self.get_ground_region()
        region_gap = pya.Region(region_ground.bbox()).size(self.margin_other_face/self.layout.dbu,
                                                           self.margin_other_face/self.layout.dbu, 2)
        region_protection = pya.Region(region_gap.bbox()).size(self.margin/self.layout.dbu,
                                                               self.margin/self.layout.dbu, 2)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid", 1)).insert(region_gap)
        self.cell.shapes(self.get_layer("ground_grid_avoidance", 1)).insert(region_protection)

        super().produce_impl()
