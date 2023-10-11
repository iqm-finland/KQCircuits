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

import numpy

from kqcircuits.elements.tsvs.tsv import Tsv
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt


class TsvEllipse(Tsv):
    """Connector between faces of two sides of a substrate.

    Origin is at the geometric center. Geometry is elliptical.

   .. MARKERS_FOR_PNG -0.2,0
    """

    tsv_elliptical_width = Param(pdt.TypeDouble, "TSV elliptical width", 30, unit="μm")

    def produce_impl(self):
        self.create_tsv_connector()

    def create_tsv_connector(self):
        """
        Generate elliptical TSV
        """
        # shorthand
        r = self.tsv_diameter / 2
        w = self.tsv_elliptical_width / 2
        n = self.n

        # parametric representation is taken from https://en.wikipedia.org/wiki/Superellipse
        p1 = 6
        p2 = 2
        tsv_pts = [
            pya.DPoint(numpy.abs(math.cos(a)) ** (2 / p1) * w * numpy.sign(math.cos(a)),
                       numpy.abs(math.sin(a)) ** (2 / p2) * r * numpy.sign(math.sin(a))) for
            a in (x / n * 2 * math.pi for x in range(0, n + 1))]

        tsv_region = pya.Region(pya.DPolygon(tsv_pts).to_itype(self.layout.dbu))

        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(
            tsv_region.sized(self.tsv_margin / self.layout.dbu, self.tsv_margin / self.layout.dbu, 2))
        self.cell.shapes(self.get_layer("ground_grid_avoidance", 1)).insert(
            tsv_region.sized(self.tsv_margin / self.layout.dbu, self.tsv_margin / self.layout.dbu, 2))
        self.cell.shapes(self.get_layer("through_silicon_via")).insert(tsv_region)
        self.cell.shapes(self.get_layer("through_silicon_via", 1)).insert(tsv_region)
