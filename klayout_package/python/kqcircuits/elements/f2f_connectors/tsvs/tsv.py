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

import numpy as np
from autologging import logged, traced

from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt


@traced
@logged
class Tsv(Element):
    """Connector between faces of two sides of a substrate..
    Origin is at the geometric center.
    """

    tsv_diameter = Param(pdt.TypeDouble, "TSV diameter", 25, unit="μm")
    tsv_type = Param(pdt.TypeString, "TSV type", "circular", choices=[["circular", "circular"], ["oval", "oval"]])
    tsv_elliptical_width = Param(pdt.TypeDouble, "Oval TSV width", 30, unit="μm")

    def produce_impl(self):
        self.create_tsv_connector()
        super().produce_impl()

    def create_tsv_connector(self):
        # shorthand
        r = self.tsv_diameter / 2
        w = self.tsv_elliptical_width / 2
        m = self.margin

        if self.tsv_type == "circular":
            # Protection layer
            tsv_pts_avoidance = [pya.DPoint(math.cos(a) * (r + m),
                                            math.sin(a) * (r + m)) for a in (x/32*math.pi for x in range(0, 65))]
            # TSV geometry
            tsv_pts = [pya.DPoint(math.cos(a) * r,
                                  math.sin(a) * r) for a in (x/32*math.pi for x in range(0, 65))]

        elif self.tsv_type == "oval":
            # parametric representation is taken from https://en.wikipedia.org/wiki/Superellipse
            p1 = 6
            p2 = 2
            # Protection layer
            tsv_pts_avoidance = [pya.DPoint(
                np.abs(math.cos(a)) ** (2 / p1) * (w + m) * np.sign(math.cos(a)),
                np.abs(math.sin(a)) ** (2 / p2) * (r + m) * np.sign(math.sin(a))) for a in
                                 (x/32*math.pi for x in range(0, 65))]

            tsv_pts = [
                pya.DPoint(np.abs(math.cos(a)) ** (2 / p1) * w * np.sign(math.cos(a)),
                           np.abs(math.sin(a)) ** (2 / p2) * r * np.sign(math.sin(a))) for
                a in (x/32*math.pi for x in range(0, 65))]

        shape = pya.DPolygon(tsv_pts_avoidance)
        # ground avoidance layer b face
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(shape)

        # ground avoidance layer c face
        self.cell.shapes(self.get_layer("ground_grid_avoidance", 2)).insert(shape)

        self.cell.shapes(self.get_layer("through_silicon_via")).insert(pya.DPolygon(tsv_pts))  # TSV only on b face
        super().produce_impl()
