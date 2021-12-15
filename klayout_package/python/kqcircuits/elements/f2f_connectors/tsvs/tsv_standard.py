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

import math
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.elements.f2f_connectors.tsvs.tsv import Tsv
from kqcircuits.defaults import default_tsv_parameters


class TsvStandard(Tsv):
    """Connector between faces of two sides of a substrate..
    Origin is at the geometric center. Geometry es circular.
    """

    tsv_diameter = Param(pdt.TypeDouble, "TSV diameter", default_tsv_parameters['tsv_diameter'], unit="μm")

    def produce_impl(self):
        self.create_tsv_connector()

    def create_tsv_connector(self):
        """
        Generate circular TSV
        """
        # shorthand
        r = self.tsv_diameter / 2
        m = self.margin

        # Protection layer
        tsv_pts_avoidance = [pya.DPoint(math.cos(a) * (r + m),
                                        math.sin(a) * (r + m)) for a in (x/32*math.pi for x in range(0, 65))]
        # TSV geometry
        tsv_pts = [pya.DPoint(math.cos(a) * r,
                              math.sin(a) * r) for a in (x/32*math.pi for x in range(0, 65))]

        shape = pya.DPolygon(tsv_pts_avoidance)
        # ground avoidance layer b face
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(shape)
        self.cell.shapes(self.get_layer("through_silicon_via")).insert(pya.DPolygon(tsv_pts))  # TSV only on b face
