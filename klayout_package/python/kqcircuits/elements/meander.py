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


import math

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.util.geometry_helper import vector_length_and_direction, get_angle


class Meander(Element):
    """The PCell declaration for a meandering waveguide.

    Defined by two points, total length and number of meanders. Uses the same bending radius as the underling waveguide.
    Equidistant airbridges can be placed in the meander using ``n_bridges`` parameter.
    """

    # TODO Remove coordinates from PCell parameters.
    start = Param(pdt.TypeShape, "Start", pya.DPoint(-600, 0))
    end = Param(pdt.TypeShape, "End", pya.DPoint(600, 0))
    length = Param(pdt.TypeDouble, "Length", 3000, unit="μm")
    meanders = Param(pdt.TypeInt, "Number of meanders (at least 1)", 4)
    n_bridges = Param(pdt.TypeInt, "Number of bridges", 0)

    def coerce_parameters_impl(self):
        self.meanders = max(self.meanders, 1)

    def can_create_from_shape_impl(self):
        return self.shape.is_path()

    def parameters_from_shape_impl(self):
        points = [pya.DPoint(point * self.layout.dbu) for point in self.shape.each_point()]
        self.start = points[0]
        self.end = points[-1]

    def produce_impl(self):
        points = [pya.DPoint(0, 0)]
        l_direct = self.start.distance(self.end)
        l_rest = l_direct - self.meanders * 2 * self.r
        l_single_meander = (self.length - (l_rest - 2 * self.r) - (self.meanders * 2 + 2) * (math.pi / 2) * self.r - (
                    self.meanders - 1) * self.r * 2) / (2 * self.meanders)

        points.append(pya.DPoint(l_rest / 2, 0))
        for i in range(self.meanders):
            points.append(pya.DPoint(l_rest / 2 + i * 2 * self.r, ((-1) ** (i % 2)) * (l_single_meander + 2 * self.r)))
            points.append(
                pya.DPoint(l_rest / 2 + (i + 1) * 2 * self.r, ((-1) ** (i % 2)) * (l_single_meander + 2 * self.r)))
        points.append(pya.DPoint(l_direct - l_rest / 2, 0))
        points.append(pya.DPoint(l_direct, 0))
        # print(set(points))
        waveguide = self.add_element(WaveguideCoplanar,
            path=pya.DPath(points, 1.),
            r=self.r,
            face_ids=self.face_ids,
            n=self.n,
            a=self.a,
            b=self.b
        )

        angle = 180 / math.pi * math.atan2(self.end.y - self.start.y, self.end.x - self.start.x)
        transf = pya.DCplxTrans(1, angle, False, pya.DVector(self.start))
        self.insert_cell(waveguide, transf)

        if self.n_bridges > 0:
            self._produce_bridges(points, transf)

    def _produce_bridges(self, wg_points, meander_trans):

        def insert_bridge(position, angle):
            self.insert_cell(Airbridge, meander_trans*pya.DCplxTrans(1, angle, False, position))

        bridge_separation = self.length/(self.n_bridges + 1)
        curve_len = self.r*math.pi/2
        dist_to_next = bridge_separation
        n_inserted = 0

        for i in range(1, len(wg_points)):

            straight_len, straight_dir = vector_length_and_direction(wg_points[i] - wg_points[i - 1])
            if i in (1, len(wg_points) - 1):  # only one curve for first and last segment
                straight_len -= self.r
            else:
                straight_len -= 2*self.r

            # bridges in the straight part of this segment
            remaining_len = straight_len
            prev_pos = wg_points[i - 1] + (self.r*straight_dir if i > 1 else pya.DVector(0, 0))
            while dist_to_next < remaining_len and n_inserted < self.n_bridges:
                pos = prev_pos + dist_to_next*straight_dir
                insert_bridge(pos, get_angle(straight_dir))
                n_inserted += 1
                remaining_len -= dist_to_next
                dist_to_next = bridge_separation
                prev_pos = pos
            dist_to_next -= remaining_len

            # bridges in the curve at the end of this segment
            remaining_len = curve_len
            prev_angle = 0
            while dist_to_next < remaining_len and n_inserted < self.n_bridges and i < len(wg_points) - 1:
                v1, v2, angle1, angle2, corner_pos = \
                    WaveguideCoplanar.get_corner_data(wg_points[i - 1], wg_points[i], wg_points[i + 1], self.r)
                angle3 = prev_angle + dist_to_next/self.r
                _, dir1 = vector_length_and_direction(v1)
                _, dir2 = vector_length_and_direction(v2)
                p1 = wg_points[i] - self.r*dir1
                p2 = wg_points[i] + self.r*dir2
                # interpolation along circular arc from p1 to p2 based on angle 3
                pos = corner_pos + (p1 - corner_pos)*math.cos(angle3) + (p2 - corner_pos)*math.sin(angle3)
                # linear interpolation between angle1 and angle2 based on angle 3
                angle4 = angle1*(1 - 2*angle3/math.pi) + angle2*(2*angle3/math.pi)
                insert_bridge(pos, math.degrees(angle4))
                n_inserted += 1
                remaining_len -= dist_to_next
                dist_to_next = bridge_separation
                prev_angle = angle3
            dist_to_next -= remaining_len
