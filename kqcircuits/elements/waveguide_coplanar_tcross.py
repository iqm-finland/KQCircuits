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
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.elements.element import Element
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridges import airbridge_type_choices


class WaveguideCoplanarTCross(Element):
    """The PCell declaration of T-crossing of waveguides."""

    a2 = Param(pdt.TypeDouble, "Width of the side waveguide", Element.a)
    b2 = Param(pdt.TypeDouble, "Gap of the side waveguide", Element.b)
    length_extra = Param(pdt.TypeDouble, "Extra length", 0)
    length_extra_side = Param(pdt.TypeDouble, "Extra length of the side waveguide", 0)
    use_airbridges = Param(pdt.TypeBoolean, "Use airbridges at a distance from the centre", False)
    bridge_distance = Param(pdt.TypeDouble, "Bridges distance from centre", 80)
    bridge_type = Param(pdt.TypeString, "Airbridge type", Airbridge.default_type, choices=airbridge_type_choices)

    def produce_impl(self):
        # Origin: Crossing of centers of the center conductors
        # Direction: Ports from left, right and bottom
        # Top gap

        l = self.length_extra
        l2 = self.length_extra_side
        a2 = self.a2
        b2 = self.b2
        a = self.a
        b = self.b

        # airbridge
        pad_length = 14
        pad_extra = 2
        self.ab_params = {
            "pad_length": pad_length,
            "pad_extra": pad_extra,
            "airbridge_type": self.bridge_type
        }

        port_l_location_x = -l - b2 - a2 / 2
        port_r_location_x = l + b2 + a2 / 2
        pts = [
            pya.DPoint(port_l_location_x, a / 2 + 0),
            pya.DPoint(port_r_location_x, a / 2 + 0),
            pya.DPoint(port_r_location_x, a / 2 + b),
            pya.DPoint(port_l_location_x, a / 2 + b)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)
        # Left gap
        port_bottom_location_y = -a / 2 - b - l2
        pts = [
            pya.DPoint(port_l_location_x, -a / 2 + 0),
            pya.DPoint(-a2 / 2, -a / 2 + 0),
            pya.DPoint(-a2 / 2, port_bottom_location_y),
            pya.DPoint(-b2 - a2 / 2, port_bottom_location_y),
            pya.DPoint(-b2 - a2 / 2, -a / 2 - b),
            pya.DPoint(port_l_location_x, -a / 2 - b)
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)
        # Right gap
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(pya.DTrans.M90 * shape)
        #Airbridges
        if self.use_airbridges:
            ab_trans1 = pya.DCplxTrans(1, 90, False, 0, -self.bridge_distance)
            ab_cell = self.add_element(Airbridge, **self.ab_params)
            self.insert_cell(ab_cell,ab_trans1)
            ab_trans2 = pya.DCplxTrans(1, 0, False, -self.bridge_distance, 0)
            ab_cell = self.add_element(Airbridge, **self.ab_params)
            self.insert_cell(ab_cell, ab_trans2)
            ab_trans3 = pya.DCplxTrans(1, 0, False, self.bridge_distance, 0)
            ab_cell = self.add_element(Airbridge, **self.ab_params)
            self.insert_cell(ab_cell, ab_trans3)
        # Protection layer
        m = self.margin
        pts = [
            pya.DPoint(port_l_location_x - m, a / 2 + b + m),
            pya.DPoint(port_r_location_x + m, a / 2 + b + m),
            pya.DPoint(port_r_location_x + m, port_bottom_location_y - m),
            pya.DPoint(port_l_location_x - m, port_bottom_location_y - m),
        ]
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(shape)

        # refpoints text
        self.add_port("left", pya.DPoint(port_l_location_x, 0), pya.DVector(-1, 0))
        self.add_port("right", pya.DPoint(port_r_location_x, 0), pya.DVector(1, 0))
        self.add_port("bottom", pya.DPoint(0, port_bottom_location_y), pya.DVector(0, -1))

        # annotation path
        self.cell.shapes(self.get_layer("waveguide_length")).insert(
            pya.DPath([self.refpoints["port_left"], self.refpoints["base"]], self.a)
        )
        self.cell.shapes(self.get_layer("waveguide_length")).insert(
            pya.DPath([self.refpoints["port_right"], self.refpoints["base"]], self.a)
        )
        self.cell.shapes(self.get_layer("waveguide_length")).insert(
            pya.DPath([self.refpoints["port_bottom"], self.refpoints["base"]], self.a)
        )

        super().produce_impl()  # adds refpoints
