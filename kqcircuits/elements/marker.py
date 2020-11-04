# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element


class Marker(Element):
    """The PCell declaration for a Marker."""

    PARAMETERS_SCHEMA = {
        "window": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Window in airbridge flyover and UBM layer",
            "default": False
        },
        "diagonal_squares": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Number of diagonal squares in the marker",
            "default": 10
        }
    }

    def produce_impl(self):
        corner = pya.DPolygon([
            pya.DPoint(100, 100),
            pya.DPoint(10, 100),
            pya.DPoint(10, 80),
            pya.DPoint(80, 80),
            pya.DPoint(80, 10),
            pya.DPoint(100, 10),
        ])

        sqr = pya.DBox(
            pya.DPoint(10, 10),
            pya.DPoint(2, 2),
        )

        window = pya.DPolygon([
            pya.DPoint(800, 800),
            pya.DPoint(800, 10),
            pya.DPoint(80, 10),
            pya.DPoint(80, 2),
            pya.DPoint(2, 2),
            pya.DPoint(2, 80),
            pya.DPoint(10, 80),
            pya.DPoint(10, 800)
        ])

        layer_gap = self.get_layer("base metal gap wo grid")
        layer_pads = self.get_layer("airbridge pads")
        layer_flyover = self.get_layer("airbridge flyover")
        layer_ubm = self.get_layer("underbump metallization")
        layer_gap_for_ebl = self.get_layer("base metal gap for EBL")
        layer_protection = self.get_layer("ground grid avoidance")

        def insert_to_main_layers(shape):
            self.cell.shapes(layer_gap).insert(shape)
            self.cell.shapes(layer_gap_for_ebl).insert(shape)
            if not self.window:
                self.cell.shapes(layer_flyover).insert(shape)
                self.cell.shapes(layer_ubm).insert(shape)

        # protection for the box
        protection_box = pya.DBox(
            pya.DPoint(220, 220),
            pya.DPoint(-220, -220)
        )
        self.cell.shapes(layer_protection).insert(protection_box)

        # inner corners
        for alpha in [0, 1, 2, 3]:
            inner_corner_shape = pya.DTrans(alpha, False, pya.DVector()) * corner
            insert_to_main_layers(inner_corner_shape)

        # outer corners
        for alpha in [0, 1, 2, 3]:
            outer_corner_shape = pya.DCplxTrans(2, alpha * 90., False, pya.DVector()) * corner
            insert_to_main_layers(outer_corner_shape)

        # center box
        sqr_uni = pya.DBox(
            pya.DPoint(10, 10),
            pya.DPoint(-10, -10),
        )
        insert_to_main_layers(sqr_uni)

        # window for airbridge flyover layer
        if self.window:
            for alpha in [0, 1, 2, 3]:
                self.cell.shapes(layer_flyover).insert((pya.DTrans(alpha, False, pya.DVector()) * window))

        # marker diagonal
        square_array = range(5, 5 + self.diagonal_squares)
        for i in square_array:
            diag_square_shape = pya.DCplxTrans(3, 0, False, pya.DVector(50 * i - 3 * 6, 50 * i - 3 * 6))*sqr
            insert_to_main_layers(diag_square_shape)
            self.cell.shapes(layer_pads).insert(diag_square_shape)
            self.cell.shapes(layer_protection).insert(
                (pya.DCplxTrans(20, 0, False, pya.DVector(50 * i - 20 * 6, 50 * i - 20 * 6)) * sqr))
