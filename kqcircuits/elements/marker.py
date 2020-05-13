# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element


class Marker(Element):
    """
  The PCell declaration for an arbitrary waveguide
  """

    PARAMETERS_SCHEMA = {
        "window": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "AB Layer windows",
            "default": False
        },
        "diagonal_squares": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Number of diagonal squares in the marker",
            "default": 10
        }
    }

    def __init__(self):
        super().__init__()

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "Marker"

    def coerce_parameters_impl(self):
        None

    def can_create_from_shape_impl(self):
        return False

    def parameters_from_shape_impl(self):
        None

    def transformation_from_shape_impl(self):
        return pya.Trans()

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

        lo = self.layout.layer(self.face()["base metal gap wo grid"])
        lo2 = self.layout.layer(self.face()["airbridge pads"])
        lp = self.layout.layer(self.face()["ground grid avoidance"])

        # center box
        sqr_uni = pya.DBox(
            pya.DPoint(10, 10),
            pya.DPoint(-10, -10),
        )

        self.cell.shapes(lo).insert(sqr_uni)
        self.cell.shapes(lo2).insert(sqr_uni)

        # inner corners
        for alpha in [0, 1, 2, 3]:
            self.cell.shapes(lo).insert(
                (pya.DTrans(alpha, False, pya.DVector()) * corner))

        # outer corners
        for alpha in [0, 1, 2, 3]:
            self.cell.shapes(lo).insert(
                (pya.DCplxTrans(2, alpha * 90., False, pya.DVector()) * corner))

        # protection for the box
        protection = pya.DBox(
            pya.DPoint(220, 220),
            pya.DPoint(-220, -220)
        )
        self.cell.shapes(lp).insert(protection)

        # windows for other opt lit masks
        if self.window:
            for l in [self.face()["airbridge pads"], self.face()["airbridge flyover"]]:
                for alpha in [0, 1, 2, 3]:
                    self.cell.shapes(self.layout.layer(l)).insert(
                        (pya.DTrans(alpha, False, pya.DVector()) * window))

        # marker diagonal
        for i in range(5, 5 + self.diagonal_squares):
            self.cell.shapes(lo).insert(
                (pya.DCplxTrans(3, 0, False, pya.DVector(50 * i - 3 * 6, 50 * i - 3 * 6)) * sqr))
            self.cell.shapes(lp).insert(
                (pya.DCplxTrans(20, 0, False, pya.DVector(50 * i - 20 * 6, 50 * i - 20 * 6)) * sqr))
