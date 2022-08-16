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

from kqcircuits.elements.tsvs.tsv import Tsv
from kqcircuits.util.geometry_helper import circle_polygon


class TsvStandard(Tsv):
    """Connector between faces of two sides of a substrate.

    Origin is at the geometric center. Geometry es circular.

    .. MARKERS_FOR_PNG 0,0
    """

    def build(self):
        tsv = circle_polygon(self.tsv_diameter / 2)
        self.cell.shapes(self.get_layer("through_silicon_via")).insert(tsv)
        margin = circle_polygon(self.tsv_diameter / 2 + self.margin)
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(margin)
        del self.refpoints['base']
