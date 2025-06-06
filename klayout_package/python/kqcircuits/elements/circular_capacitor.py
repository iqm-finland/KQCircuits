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


import math
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.util.geometry_helper import circle_polygon, arc_points, force_rounded_corners
from kqcircuits.elements.element import Element
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare, eval_a2, eval_b2


@add_parameters_from(FingerCapacitorSquare, "fixed_length", "a2", "b2")
class CircularCapacitor(Element):
    """The PCell declaration for a circular capacitor.

    An outer semi-circular island with an inside circular island. Fixed-length capacitor is supported and different line
    impedance on each side can be used.
    Two ports with reference points. The feedline has the same length as the width of the ground gap around the coupler.

     .. MARKERS_FOR_PNG 30,0 -56,0 86,0
    """

    r_inner = Param(
        pdt.TypeDouble,
        "Internal island radius",
        20,
        unit="μm",
        docstring="Radius of the outer edge of the center island (μm)",
    )
    r_outer = Param(
        pdt.TypeDouble,
        "External island radius, measured at the outer edge",
        80,
        unit="μm",
        docstring="Radius of the external coupler island (μm)",
    )
    swept_angle = Param(pdt.TypeDouble, "Angle covered by the external island in degrees", 180)
    outer_island_width = Param(
        pdt.TypeDouble, "External island width", 40, unit="μm", docstring="Width of the external island (μm)"
    )
    ground_gap = Param(pdt.TypeDouble, "Ground plane padding", 20, unit="μm")

    def build(self):
        y_left = self.a / 2
        y_right = eval_a2(self) / 2
        x_end = self.r_outer + self.ground_gap

        capacitor_region = []
        # generate the inner island
        inner_island = circle_polygon(self.r_inner, self.n)
        capacitor_region.append(inner_island)

        # generate the outer island
        outer_island = self._get_outer_island(self.r_outer, self.outer_island_width, self.swept_angle)
        capacitor_region.append(outer_island)
        capacitor_neg = pya.Region([poly.to_itype(self.layout.dbu) for poly in capacitor_region])

        # add the waveguides inside the ground padding
        capacitor_neg += pya.Region(
            pya.DPolygon(
                [
                    pya.DPoint(-x_end, -y_left),
                    pya.DPoint(-0, -y_left),
                    pya.DPoint(-0, y_left),
                    pya.DPoint(-x_end, y_left),
                ]
            ).to_itype(self.layout.dbu)
        ) + pya.Region(
            pya.DPolygon(
                [
                    pya.DPoint(x_end, y_right),
                    pya.DPoint(self.r_outer - self.outer_island_width / 2, y_right),
                    pya.DPoint(self.r_outer - self.outer_island_width / 2, -y_right),
                    pya.DPoint(x_end, -y_right),
                ]
            ).to_itype(self.layout.dbu)
        )
        capacitor_neg = force_rounded_corners(capacitor_neg, 5 / self.layout.dbu, 5 / self.layout.dbu, self.n // 2)
        self._add_waveguides(capacitor_neg, x_end, y_left, y_right)

        # define the capacitor in the ground
        ground_region = self._add_ground_region(x_end)
        capacitor_region = ground_region - capacitor_neg
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(capacitor_region)

        # protection region
        region_protection = self._get_protection_region(ground_region)
        self.add_protection(region_protection)

        # ports
        x_port = max(x_end, self.fixed_length / 2)
        self.add_port("a", pya.DPoint(-x_port, 0), pya.DVector(-1, 0))
        self.add_port("b", pya.DPoint(x_port, 0), pya.DVector(1, 0))

        # adds annotation based on refpoints calculated above

    def _get_outer_island(self, r_outer, outer_island_width, swept_angle):
        angle_rad = math.radians(swept_angle)
        islands_gap = self.r_outer - self.r_inner - self.outer_island_width
        eff_gap = max(islands_gap, self.b)
        border_angle_1 = 2 * (math.pi - math.asin((self.a / 2 + eff_gap) / (r_outer - outer_island_width)))
        border_angle_2 = 2 * (math.pi - math.asin((self.a / 2 + eff_gap) / (r_outer)))

        if angle_rad < border_angle_1:
            # default behaviour
            inner_angle = angle_rad
        elif angle_rad < border_angle_2:
            # Change the angle of coupler island wrt inner trace to make it stay at least eff_gap away from the trace
            inner_angle = border_angle_1
        else:
            # At this point the coupler is parallel to the trace and approaches uniformly
            inner_angle = math.pi + 2 * math.acos(
                math.cos(angle_rad / 2 - math.pi / 2) * r_outer / (r_outer - outer_island_width)
            )

        points_outside = arc_points(r_outer, -angle_rad / 2, angle_rad / 2, self.n)
        points_inside = arc_points(r_outer - outer_island_width, inner_angle / 2, -inner_angle / 2, self.n)
        self.refpoints["epr_cplr_out"] = points_outside[-1]
        self.refpoints["epr_cplr_in"] = points_inside[0]
        points = points_outside + points_inside
        outer_island = pya.DPolygon(points)

        return outer_island

    def _add_ground_region(self, x_end):
        # generate the ground region
        ground_region = []
        island_ground = circle_polygon(self.r_outer + self.ground_gap, self.n)
        ground_region.append(island_ground)
        ground_region = pya.Region([poly.to_itype(self.layout.dbu) for poly in ground_region])
        self._add_waveguides(ground_region, x_end, self.a / 2 + self.b, eval_a2(self) / 2 + eval_b2(self))

        return ground_region

    def _get_protection_region(self, region):
        protection_region = region.sized(self.margin / self.layout.dbu, self.margin / self.layout.dbu, 2)

        return protection_region

    def _add_waveguides(self, region, x_end, y_left, y_right):
        x_guide = self.fixed_length / 2 if (self.fixed_length > 0) else x_end
        if x_guide < x_end:
            raise ValueError(f"Circular capacitor parameters not compatible with fixed_length={self.fixed_length}")
        region += pya.Region(
            pya.DPolygon(
                [
                    pya.DPoint(-x_end + self.margin, -y_left),
                    pya.DPoint(-x_guide, -y_left),
                    pya.DPoint(-x_guide, y_left),
                    pya.DPoint(-x_end + self.margin, y_left),
                ]
            ).to_itype(self.layout.dbu)
        ) + pya.Region(
            pya.DPolygon(
                [
                    pya.DPoint(x_end - self.margin, y_right),
                    pya.DPoint(x_guide, y_right),
                    pya.DPoint(x_guide, -y_right),
                    pya.DPoint(x_end - self.margin, -y_right),
                ]
            ).to_itype(self.layout.dbu)
        )

    @classmethod
    def get_sim_ports(cls, simulation):
        return FingerCapacitorSquare.get_sim_ports(simulation)
