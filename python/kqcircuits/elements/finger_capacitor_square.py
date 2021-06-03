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


class FingerCapacitorSquare(Element):
    """The PCell declaration for a square finger capacitor.

    Two ports with reference points. The arm leading to the finger has the same width as fingers. The feedline has
    the same length as the width of the ground gap around the coupler.
    """

    a2 = Param(pdt.TypeDouble, "Width of center conductor on the other end", Element.a, unit="μm")
    b2 = Param(pdt.TypeDouble, "Width of gap on the other end", Element.b, unit="μm")
    finger_number = Param(pdt.TypeInt, "Number of fingers", 5)
    finger_width = Param(pdt.TypeDouble, "Width of a finger", 5, unit="μm")
    finger_gap_side = Param(pdt.TypeDouble, "Gap between the fingers", 3, unit="μm")
    finger_gap_end = Param(pdt.TypeDouble, "Gap between the finger and other pad", 3, unit="μm")
    finger_length = Param(pdt.TypeDouble, "Length of the fingers", 20, unit="μm")
    ground_padding = Param(pdt.TypeDouble, "Ground plane padding", 20, unit="μm")
    corner_r = Param(pdt.TypeDouble, "Corner radius", 2, unit="μm")
    fixed_length = Param(pdt.TypeDouble, "Fixed length of element, 0 for auto-length", 0, unit="μm")

    def can_create_from_shape_impl(self):
        return self.shape.is_path()

    def produce_impl(self):
        y_mid = self.finger_area_width() / 2
        y_left = self.a / 2
        y_right = self.a2 / 2
        x_mid = self.finger_area_length() / 2
        x_left = x_mid + self.finger_width + (self.ground_padding if y_left > y_mid else 0.0)
        x_right = x_mid + self.finger_width + (self.ground_padding if y_right > y_mid else 0.0)
        x_end = x_mid + self.finger_width + self.ground_padding
        x_max = x_end + self.corner_r

        region_ground = self.get_ground_region()

        region_taper_right = pya.Region([pya.DPolygon([
            pya.DPoint(x_mid, y_mid),
            pya.DPoint(x_right, y_mid),
            pya.DPoint(x_right, y_right),
            pya.DPoint(x_max, y_right),
            pya.DPoint(x_max, -y_right),
            pya.DPoint(x_right, -y_right),
            pya.DPoint(x_right, -y_mid),
            pya.DPoint(x_mid, -y_mid)
        ]).to_itype(self.layout.dbu)])
        region_taper_left = pya.Region([pya.DPolygon([
            pya.DPoint(-x_mid, y_mid),
            pya.DPoint(-x_left, y_mid),
            pya.DPoint(-x_left, y_left),
            pya.DPoint(-x_max, y_left),
            pya.DPoint(-x_max, -y_left),
            pya.DPoint(-x_left, -y_left),
            pya.DPoint(-x_left, -y_mid),
            pya.DPoint(-x_mid, -y_mid)
        ]).to_itype(self.layout.dbu)])

        polys_fingers = []
        for i in range(self.finger_number):
            x = (i % 2) * self.finger_gap_end - x_mid
            y = i * (self.finger_width + self.finger_gap_side) - y_mid
            polys_fingers.append(pya.DPolygon([
                pya.DPoint(x + self.finger_length, y + self.finger_width),
                pya.DPoint(x + self.finger_length, y),
                pya.DPoint(x, y),
                pya.DPoint(x, y + self.finger_width)
            ]))

        region_fingers = pya.Region([
            poly.to_itype(self.layout.dbu) for poly in polys_fingers
        ])
        region_etch = region_taper_left + region_taper_right + region_fingers
        region_etch.round_corners(self.corner_r / self.layout.dbu, self.corner_r / self.layout.dbu, self.n)
        self.cut_region(region_etch, x_end, max(y_mid, y_left, y_right))
        self.add_waveguides(region_etch, x_end, y_left, y_right)

        region = region_ground - region_etch

        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(region)

        # protection
        region_protection = region_ground.size(self.margin / self.layout.dbu, self.margin / self.layout.dbu, 2)
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(region_protection)

        # ports
        x_port = max(x_end, self.fixed_length / 2)
        self.add_port("a", pya.DPoint(-x_port, 0), pya.DVector(-1, 0))
        self.add_port("b", pya.DPoint(x_port, 0), pya.DVector(1, 0))

        # adds annotation based on refpoints calculated above
        super().produce_impl()

    def get_ground_region(self):
        """Returns the ground region for the finger capacitor."""
        y_mid = self.finger_area_width() / 2 + self.ground_padding
        y_left = self.a / 2 + self.b
        y_right = self.a2 / 2 + self.b2
        x_mid = self.finger_area_length() / 2 + self.finger_width
        x_left = x_mid + (self.ground_padding if y_left < y_mid else 0.0)
        x_right = x_mid + (self.ground_padding if y_right < y_mid else 0.0)
        x_end = x_mid + self.ground_padding
        x_max = x_end + self.corner_r

        region_ground = pya.Region([pya.DPolygon([
            pya.DPoint(-x_left, -y_mid),
            pya.DPoint(-x_left, -y_left),
            pya.DPoint(-x_max, -y_left),
            pya.DPoint(-x_max, y_left),
            pya.DPoint(-x_left, y_left),
            pya.DPoint(-x_left, y_mid),
            pya.DPoint(x_right, y_mid),
            pya.DPoint(x_right, y_right),
            pya.DPoint(x_max, y_right),
            pya.DPoint(x_max, -y_right),
            pya.DPoint(x_right, -y_right),
            pya.DPoint(x_right, -y_mid),
        ]).to_itype(self.layout.dbu)])
        region_ground.round_corners(self.corner_r / self.layout.dbu, self.corner_r / self.layout.dbu, self.n)
        self.cut_region(region_ground, x_end, max(y_mid, y_left, y_right))
        self.add_waveguides(region_ground, x_end, y_left, y_right)

        return region_ground

    def finger_area_width(self):
        return self.finger_number * self.finger_width + (self.finger_number - 1) * self.finger_gap_side

    def finger_area_length(self):
        return self.finger_length + self.finger_gap_end

    def cut_region(self, region, x_max, y_max):
        cutter = pya.Region([pya.DPolygon([
            pya.DPoint(x_max, -y_max),
            pya.DPoint(x_max, y_max),
            pya.DPoint(-x_max, y_max),
            pya.DPoint(-x_max, -y_max)
        ]).to_itype(self.layout.dbu)])
        region &= cutter

    def add_waveguides(self, region, x_end, y_left, y_right):
        x_guide = self.fixed_length / 2
        if self.fixed_length != 0 and x_guide < x_end:
            raise ValueError(f"FingerCapacitorSquare parameters not compatible with fixed_length={self.fixed_length}")
        if x_guide > x_end:
            region += pya.Region([pya.DPolygon([
                pya.DPoint(-x_end, -y_left),
                pya.DPoint(-x_guide, -y_left),
                pya.DPoint(-x_guide, y_left),
                pya.DPoint(-x_end, y_left),
            ]).to_itype(self.layout.dbu)]) + pya.Region([pya.DPolygon([
                pya.DPoint(x_end, y_right),
                pya.DPoint(x_guide, y_right),
                pya.DPoint(x_guide, -y_right),
                pya.DPoint(x_end, -y_right),
            ]).to_itype(self.layout.dbu)])
