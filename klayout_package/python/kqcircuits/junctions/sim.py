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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.junctions.junction import Junction
from kqcircuits.util.symmetric_polygons import polygon_with_vsym


class Sim(Junction):
    """The PCell declaration for a simulation type SQUID.

    Origin at the center of junction layer bottom edge.
    """

    junction_total_length = Param(pdt.TypeDouble, "Simulation junction total length", 33, unit="µm")
    junction_upper_pad_width = Param(pdt.TypeDouble, "Simulation junction upper metal pad width", 8, unit="µm")
    junction_upper_pad_length = Param(pdt.TypeDouble, "Simulation junction upper metal pad length", 13, unit="µm")
    junction_lower_pad_width = Param(pdt.TypeDouble, "Simulation junction lower metal pad width", 8, unit="µm")
    junction_lower_pad_length = Param(pdt.TypeDouble, "Simulation junction lower metal pad length", 12, unit="µm")
    include_background_gap = Param(pdt.TypeBoolean, "Add base metal gap below the junction", True)

    def build(self):

        trans = pya.DTrans(0.0, 0.0)
        self._produce_ground_metal_shapes(trans)
        # refpoints
        self.refpoints["origin_squid"] = pya.DPoint(0, 0)
        self.refpoints["port_squid_a"] = pya.DPoint(0, self.junction_total_length - self.junction_upper_pad_length)
        self.refpoints["port_squid_b"] = pya.DPoint(0, self.junction_lower_pad_length)
        self.refpoints["port_common"] = pya.DPoint(0, self.junction_total_length)

    def _produce_ground_metal_shapes(self, trans):
        """Produces shapes in base metal addition layer."""
        # metal additions bottom
        bottom_half_w = self.junction_lower_pad_width / 2
        bottom_pts = [
            pya.DPoint(-bottom_half_w, 0),
            pya.DPoint(-bottom_half_w, self.junction_lower_pad_length),
            pya.DPoint(bottom_half_w, self.junction_lower_pad_length),
            pya.DPoint(bottom_half_w, 0),
        ]
        shape = polygon_with_vsym(bottom_pts)
        self.cell.shapes(self.get_layer("base_metal_addition")).insert(trans * shape)
        # metal additions top
        top_half_w = self.junction_upper_pad_width / 2
        top_pts = [
            pya.DPoint(-top_half_w, self.junction_total_length - self.junction_upper_pad_length),
            pya.DPoint(-top_half_w, self.junction_total_length),
            pya.DPoint(top_half_w, self.junction_total_length),
            pya.DPoint(top_half_w, self.junction_total_length - self.junction_upper_pad_length),
        ]
        shape = polygon_with_vsym(top_pts)
        self.cell.shapes(self.get_layer("base_metal_addition")).insert(trans * shape)
        # add ground grid avoidance
        w = self.cell.dbbox().width()
        h = self.cell.dbbox().height()
        protection = pya.DBox(-w / 2 - self.margin, -self.margin, w / 2 + self.margin, h + self.margin)
        self.add_protection(trans * protection)
        if self.include_background_gap:
            ground_gap = pya.DBox(-w / 2 - self.margin, 0, w / 2 + self.margin, h)
            self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(trans * ground_gap)
