# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element


class FingerCapacitorTaper(Element):
    """The PCell declaration for a tapered finger capacitor.

    Two ports with reference points. Ground plane gap is automatically adjusted to maintain the a/b ratio.
    """

    PARAMETERS_SCHEMA = {
        "finger_number": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Number of fingers",
            "default": 5
        },
        "finger_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Width of a finger [μm]",
            "default": 5
        },
        "finger_gap": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Gap between the fingers [μm]",
            "default": 3
        },
        "finger_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Length of the fingers [μm]",
            "default": 20
        },
        "taper_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Length of the taper [μm]",
            "default": 60
        },
        "corner_r": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Corner radius [μm]",
            "default": 2
        }
    }

    def can_create_from_shape_impl(self):
        return self.shape.is_path()

    def produce_impl(self):
        # shorthand
        n = self.finger_number
        w = self.finger_width
        l = self.finger_length
        g = self.finger_gap
        t = self.taper_length
        W = float(n) * (w + g) - g  # total width
        a = self.a
        b = self.b

        region_ground = pya.Region([pya.DPolygon([
            pya.DPoint((l + g) / 2, W * (b / a) + W / 2),
            pya.DPoint((l + g) / 2 + t, b + a / 2),
            pya.DPoint((l + g) / 2 + t, -b - a / 2),
            pya.DPoint((l + g) / 2, -W * (b / a) - W / 2),
            pya.DPoint(-(l + g) / 2, -W * (b / a) - W / 2),
            pya.DPoint(-(l + g) / 2 - t, -b - a / 2),
            pya.DPoint(-(l + g) / 2 - t, b + a / 2),
            pya.DPoint(-(l + g) / 2, W * (b / a) + W / 2),

        ]).to_itype(self.layout.dbu)])

        region_taper_right = pya.Region([pya.DPolygon([
            pya.DPoint((l + g) / 2, W / 2),
            pya.DPoint((l + g) / 2 + t, a / 2),
            pya.DPoint((l + g) / 2 + t, -a / 2),
            pya.DPoint((l + g) / 2, -W / 2)
        ]).to_itype(self.layout.dbu)])
        region_taper_left = region_taper_right.transformed(pya.Trans().M90)

        polys_fingers = []
        poly_finger = pya.DPolygon([
            pya.DPoint(l / 2, w),
            pya.DPoint(l / 2, 0),
            pya.DPoint(-l / 2, 0),
            pya.DPoint(-l / 2, w)
        ])
        for i in range(0, n):
            trans = pya.DTrans(pya.DVector(g / 2, i * (g + w) - W / 2)) if i % 2 else pya.DTrans(
                pya.DVector(-g / 2, i * (g + w) - W / 2))
            polys_fingers.append(trans * poly_finger)

        region_fingers = pya.Region([
            poly.to_itype(self.layout.dbu) for poly in polys_fingers
        ])
        region_etch = region_taper_left + region_taper_right + region_fingers
        region_etch.round_corners(self.corner_r / self.layout.dbu, self.corner_r / self.layout.dbu, self.n)

        region_taper_right_small = pya.Region([pya.DPolygon([
            pya.DPoint((l + g) / 2 + self.corner_r, (W / 2 - a / 2) * (t - 2 * self.corner_r) / t + a / 2),
            pya.DPoint((l + g) / 2 + t, a / 2),
            pya.DPoint((l + g) / 2 + t, -a / 2),
            pya.DPoint((l + g) / 2 + self.corner_r, -(W / 2 - a / 2) * (t - 2 * self.corner_r) / t - a / 2)
        ]).to_itype(self.layout.dbu)])
        region_taper_left_small = region_taper_right_small.transformed(pya.Trans().M90)

        region = (region_ground - region_etch) - region_taper_right_small - region_taper_left_small

        self.cell.shapes(self.get_layer("base metal gap wo grid")).insert(region)

        # protection
        region_protection = region_ground.size(0, self.margin / self.layout.dbu, 2)
        self.cell.shapes(self.get_layer("ground grid avoidance")).insert(region_protection)

        # ports
        port_a = pya.DPoint(-(l + g) / 2 - t, 0)
        self.add_port("a", port_a, pya.DVector(-1, 0))
        port_b = pya.DPoint((l + g) / 2 + t, 0)
        self.add_port("b", port_b, pya.DVector(1, 0))

        # adds annotation based on refpoints calculated above
        super().produce_impl()
