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
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.elements.element import Element
from kqcircuits.elements.finger_capacitor_taper import FingerCapacitorTaper


@add_parameters_from(FingerCapacitorTaper, "*", "taper_length")
class FingerCapacitorSquare(Element):
    """The PCell declaration for a square finger capacitor.

    Two ports with reference points. The arm leading to the finger has the same width as fingers. The feedline has
    the same length as the width of the ground gap around the coupler.

    .. MARKERS_FOR_PNG 20,-10 0,17 0,5
    """

    a2 = Param(pdt.TypeDouble, "Width of center conductor on the other end", -1, unit="μm",
               docstring="Non-physical value '-1' means that the default size 'a' is used.")
    b2 = Param(pdt.TypeDouble, "Width of gap on the other end", -1, unit="μm",
               docstring="Non-physical value '-1' means that the default size 'b' is used.")
    finger_gap_end = Param(pdt.TypeDouble, "Gap between the finger and other pad", 3, unit="μm")
    ground_padding = Param(pdt.TypeDouble, "Ground plane padding", 20, unit="μm")
    fixed_length = Param(pdt.TypeDouble, "Fixed length of element, 0 for auto-length", 0, unit="μm")
    ground_gap_ratio = Param(pdt.TypeDouble, "Ground connection width per gap ratio", 0, unit="μm")

    def can_create_from_shape_impl(self):
        return self.shape.is_path()

    def build(self):
        y_mid = self.finger_area_width() / 2
        y_left = self.a / 2
        y_right = (self.a if self.a2 < 0 else self.a2) / 2
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
            y = i * (self.finger_width + self.finger_gap) - y_mid
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
        region_protection = region_ground.size(self.margin / self.layout.dbu, self.margin / self.layout.dbu, 2).merged()
        self.add_protection(region_protection)

        # ports
        x_port = max(x_end, self.fixed_length / 2)
        self.add_port("a", pya.DPoint(-x_port, 0), pya.DVector(-1, 0))
        self.add_port("b", pya.DPoint(x_port, 0), pya.DVector(1, 0))

        # adds annotation based on refpoints calculated above

    def get_ground_region(self):
        """Returns the ground region for the finger capacitor."""
        finger_area_width = self.finger_area_width()
        y_mid = finger_area_width / 2 + self.ground_padding
        y_left = self.a / 2 + self.b
        y_right = (self.a if self.a2 < 0 else self.a2) / 2 + (self.b if self.b2 < 0 else self.b2)
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

        if self.ground_gap_ratio > 0:
            x_conn = self.ground_gap_ratio * self.finger_gap_end / 2
            left_pts = []
            right_pts = []
            for i in range(self.finger_number):
                sign = 2 * (i % 2) - 1
                x = -sign * self.finger_length / 2
                y0 = i * (self.finger_width + self.finger_gap) - (finger_area_width + self.finger_gap) / 2
                y1 = y0 + self.finger_width + self.finger_gap
                y_conn = sign * self.ground_gap_ratio * self.finger_gap / 2
                left_pts += [pya.DPoint(x - x_conn, y0 - y_conn if i > 0 else -y_mid),
                             pya.DPoint(x - x_conn, y1 + y_conn if i + 1 < self.finger_number else y_mid)]
                right_pts += [pya.DPoint(x + x_conn, y0 + y_conn if i > 0 else -y_mid),
                              pya.DPoint(x + x_conn, y1 - y_conn if i + 1 < self.finger_number else y_mid)]
            region_ground -= pya.Region([pya.DPolygon(left_pts + right_pts[::-1]).to_itype(self.layout.dbu)])

        region_ground.round_corners(self.corner_r / self.layout.dbu, self.corner_r / self.layout.dbu, self.n)
        self.cut_region(region_ground, x_end, max(y_mid, y_left, y_right))
        self.add_waveguides(region_ground, x_end, y_left, y_right)

        return region_ground

    def finger_area_width(self):
        return self.finger_number * self.finger_width + (self.finger_number - 1) * self.finger_gap

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
