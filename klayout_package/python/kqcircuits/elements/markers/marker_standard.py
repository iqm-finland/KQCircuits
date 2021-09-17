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
from kqcircuits.elements.markers.marker import Marker


class MarkerStandard(Marker):
    """The PCell declaration for the Standard Marker."""

    diagonal_squares = Param(pdt.TypeInt, "Number of diagonal squares in the marker", 10)
    window = Param(pdt.TypeBoolean, "Window in airbridge flyover and UBM layer", False)

    def produce_impl(self):
        self.produce_geometry()

    def produce_geometry(self, extra_layer=None):
        """Produce common marker geometry.

        Args:
            extra_layer : specify an extra layer to add shapes to
        """

        layer_gap = self.get_layer("base_metal_gap_wo_grid")
        layer_pads = self.get_layer("airbridge_pads")
        layer_flyover = self.get_layer("airbridge_flyover")
        layer_ubm = self.get_layer("underbump_metallization")
        layer_gap_for_ebl = self.get_layer("base_metal_gap_for_EBL")
        layer_protection = self.get_layer("ground_grid_avoidance")

        def insert_to_main_layers(shape):
            self.cell.shapes(layer_gap).insert(shape)
            self.cell.shapes(layer_gap_for_ebl).insert(shape)
            if not self.window:
                self.cell.shapes(layer_flyover).insert(shape)

        # protection for the box
        protection_box = pya.DBox(
            pya.DPoint(220, 220),
            pya.DPoint(-220, -220)
        )
        self.cell.shapes(layer_protection).insert(protection_box)
        ubm_region = pya.Region([protection_box.to_itype(self.layout.dbu)])

        # make corners
        corner = pya.DPolygon([
            pya.DPoint(100, 100),
            pya.DPoint(10, 100),
            pya.DPoint(10, 80),
            pya.DPoint(80, 80),
            pya.DPoint(80, 10),
            pya.DPoint(100, 10),
        ])
        for alpha in [0, 1, 2, 3]:
            inner_corner_shape = pya.DTrans(alpha, False, pya.DVector()) * corner
            outer_corner_shape = pya.DCplxTrans(2, alpha * 90., False, pya.DVector()) * corner
            insert_to_main_layers(inner_corner_shape)
            insert_to_main_layers(outer_corner_shape)
            ubm_region -= pya.Region([inner_corner_shape.to_itype(self.layout.dbu)])
            ubm_region -= pya.Region([outer_corner_shape.to_itype(self.layout.dbu)])

        # center box
        sqr_uni = pya.DBox(
            pya.DPoint(10, 10),
            pya.DPoint(-10, -10),
        )
        insert_to_main_layers(sqr_uni)
        pads_region = ubm_region - pya.Region([sqr_uni.to_itype(self.layout.dbu)])
        if self.window:
            ubm_region = pads_region
        if extra_layer:
            self.cell.shapes(extra_layer).insert(ubm_region)
        self.cell.shapes(layer_pads).insert(pads_region)
        self.cell.shapes(layer_ubm).insert(pads_region)

        # window for airbridge flyover layer
        aflw = pya.DPolygon([
            pya.DPoint(800, 800),
            pya.DPoint(800, 10),
            pya.DPoint(80, 10),
            pya.DPoint(80, 2),
            pya.DPoint(2, 2),
            pya.DPoint(2, 80),
            pya.DPoint(10, 80),
            pya.DPoint(10, 800)
        ])
        if self.window:
            for alpha in [0, 1, 2, 3]:
                self.cell.shapes(layer_flyover).insert((pya.DTrans(alpha, False, pya.DVector()) * aflw))

        # marker diagonal
        sqr = pya.DBox(
            pya.DPoint(10, 10),
            pya.DPoint(2, 2),
        )
        square_array = range(5, 5 + self.diagonal_squares)
        for i in square_array:
            diag_square_shape = pya.DCplxTrans(3, 0, False, pya.DVector(50 * i - 3 * 6, 50 * i - 3 * 6)) * sqr
            insert_to_main_layers(diag_square_shape)
            self.cell.shapes(layer_pads).insert(diag_square_shape)
            self.cell.shapes(layer_ubm).insert(diag_square_shape)
            if extra_layer:
                self.cell.shapes(extra_layer).insert(diag_square_shape)
            self.cell.shapes(layer_protection).insert(
                (pya.DCplxTrans(20, 0, False, pya.DVector(50 * i - 20 * 6, 50 * i - 20 * 6)) * sqr))
