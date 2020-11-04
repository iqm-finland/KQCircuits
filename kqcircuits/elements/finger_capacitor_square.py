# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element


class FingerCapacitorSquare(Element):
    """The PCell declaration for a square finger capacitor.

    Two ports with reference points. The arm leading to the finger has the same width as fingers. The feedline has
    the same length as the width of the ground gap around the coupler.
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
        "finger_gap_side": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Gap between the fingers [μm]",
            "default": 3
        },
        "finger_gap_end": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Gap between the finger and other pad [μm]",
            "default": 3
        },
        "finger_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Length of the fingers [μm]",
            "default": 20
        },
        "ground_padding": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Ground plane padding [μm]",
            "default": 20
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
        g = self.finger_gap_side
        e = self.finger_gap_end
        p = self.ground_padding
        W = max(float(n) * (w + g) - g, self.a)  # total width
        a = self.a
        b = self.b

        region_ground = self.get_ground_region()

        region_taper_right = pya.Region([pya.DPolygon([
            pya.DPoint((l + e) / 2, W / 2),
            pya.DPoint((l + e) / 2 + w, W / 2),
            pya.DPoint((l + e) / 2 + w, a / 2),
            pya.DPoint((l + e) / 2 + w + p + self.corner_r, a / 2),
            pya.DPoint((l + e) / 2 + w + p + self.corner_r, -a / 2),
            pya.DPoint((l + e) / 2 + w, -a / 2),
            pya.DPoint((l + e) / 2 + w, -W / 2),
            pya.DPoint((l + e) / 2, -W / 2)
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
            trans = pya.DTrans(pya.DVector(e / 2, i * (g + w) - W / 2)) if i % 2 else pya.DTrans(
                pya.DVector(-e / 2, i * (g + w) - W / 2))
            polys_fingers.append(trans * poly_finger)

        region_fingers = pya.Region([
            poly.to_itype(self.layout.dbu) for poly in polys_fingers
        ])
        region_etch = region_taper_left + region_taper_right + region_fingers
        region_etch.round_corners(self.corner_r / self.layout.dbu, self.corner_r / self.layout.dbu, self.n)

        region = region_ground - region_etch

        self.cell.shapes(self.get_layer("base metal gap wo grid")).insert(region)

        # protection
        region_protection = pya.Region(region_ground.bbox()).size(self.margin / self.layout.dbu,
                                                                  self.margin / self.layout.dbu, 2)
        self.cell.shapes(self.get_layer("ground grid avoidance")).insert(region_protection)

        # ports
        port_a = pya.DPoint(-(l + e) / 2 - w - p, 0)
        self.add_port("a", port_a, pya.DVector(-1, 0))
        port_b = pya.DPoint((l + e) / 2 + w + p, 0)
        self.add_port("b", port_b, pya.DVector(1, 0))

        # adds annotation based on refpoints calculated above
        super().produce_impl()

    def get_ground_region(self):
        """Returns the ground region for the finger capacitor."""
        W = max(float(self.finger_number)*(self.finger_width + self.finger_gap_side) - self.finger_gap_side, self.a)
        region_ground = pya.Region([pya.DPolygon([
            pya.DPoint((self.finger_length + self.finger_gap_end)/2 + self.finger_width + self.ground_padding,
                       W/2 + self.ground_padding),
            pya.DPoint((self.finger_length + self.finger_gap_end)/2 + self.finger_width + self.ground_padding,
                       -W/2 - self.ground_padding),
            pya.DPoint(-(self.finger_length + self.finger_gap_end)/2 - self.finger_width - self.ground_padding,
                       -W/2 - self.ground_padding),
            pya.DPoint(-(self.finger_length + self.finger_gap_end)/2 - self.finger_width - self.ground_padding,
                       W/2 + self.ground_padding),
        ]).to_itype(self.layout.dbu)])
        region_ground.round_corners(self.corner_r/self.layout.dbu, self.corner_r/self.layout.dbu, self.n)
        return region_ground
