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


from autologging import logged

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.fluxlines.fluxline import Fluxline


@logged
class FluxlineStandard(Fluxline):
    """Fluxline variant "standard".

     .. MARKERS_FOR_PNG 9,-21 11,-17 -10,-9.7
    """

    def build(self):
        # shorthands
        a = self.a  # waveguide center width
        b = self.b  # waveguide gap width
        fb = self.fluxline_gap_width  # fluxline gap width
        fa = self.fluxline_gap_width * (self.a / self.b)  # fluxline center width
        w = self.fluxline_width
        l1 = 30  # length of straight down section
        l2 = 50  # length of taper to waveguide port

        # origin at edge of the qubit gap
        right_gap = pya.DPolygon([
            pya.DPoint(-w / 2 - fa / 2, -fa),
            pya.DPoint(w / 2 + fa / 2 + fb, -fa),
            pya.DPoint(w / 2 + fa / 2 + fb, -fa - l1),
            pya.DPoint(a / 2 + b, -fa - l1 - l2),
            pya.DPoint(a / 2, -fa - l1 - l2),
            pya.DPoint(w / 2 + fa / 2, -fa - l1),
            pya.DPoint(w / 2 + fa / 2, -fa - fb),
            pya.DPoint(-w / 2 - fa / 2, -fa - fb)
        ])
        left_gap = pya.DPolygon([
            pya.DPoint(-w / 2 - fa / 2, -2 * fa - fb),
            pya.DPoint(w / 2 - fa / 2, -2 * fa - fb),
            pya.DPoint(w / 2 - fa / 2, -fa - l1),
            pya.DPoint(-a / 2, -fa - l1 - l2),
            pya.DPoint(-a / 2 - b, -fa - l1 - l2),
            pya.DPoint(w / 2 - fa / 2 - fb, -fa - l1),
            pya.DPoint(w / 2 - fa / 2 - fb, -2 * fa - 2 * fb),
            pya.DPoint(-w / 2 - fa / 2, -2 * fa - 2 * fb)
        ])

        self._insert_fluxline_shapes(left_gap, right_gap)
        self._add_fluxline_refpoints(pya.DPoint(0, -fa - l1 - l2))
