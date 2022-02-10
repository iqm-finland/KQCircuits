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


from math import pi, sin, tan, atan2, degrees
from scipy.optimize import brentq

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.util.geometry_helper import vector_length_and_direction, get_angle


class Meander(Element):
    """The PCell declaration for a meandering waveguide.

    Defined by two points, total length and number of meanders.

    The start and end points can be moved in GUI using the "Move"-tool. Alternatively, if a list of ``[x, y]``
    coordinates is given for ``start`` and ``end``, the GUI markers will not be shown. The latter is useful for
    code-generated cells that cannot be edited in the GUI.

    By default, the number of meanders is automatically chosen to minimize the area taken by bounding box of
    the meander. Uses the same bending radius as the underlying waveguide. Equidistant airbridges can be placed in the
    meander using ``n_bridges`` parameter.
    """
    start = Param(pdt.TypeShape, "Start", pya.DPoint(-600, 0))
    end = Param(pdt.TypeShape, "End", pya.DPoint(600, 0))
    length = Param(pdt.TypeDouble, "Length", 3000, unit="μm")
    meanders = Param(pdt.TypeInt, "Number of meanders (non-positive means automatic)", -1)
    n_bridges = Param(pdt.TypeInt, "Number of bridges", 0)

    def can_create_from_shape_impl(self):
        return self.shape.is_path()

    def parameters_from_shape_impl(self):
        points = [pya.DPoint(point * self.layout.dbu) for point in self.shape.each_point()]
        self.start = points[0]
        self.end = points[-1]

    def build(self):
        if isinstance(self.start, list):
            start = pya.DPoint(self.start[0], self.start[1])
        else:
            start = self.start
        if isinstance(self.end, list):
            end = pya.DPoint(self.end[0], self.end[1])
        else:
            end = self.end

        angle = 180/pi*atan2(end.y - start.y, end.x - start.x)
        transf = pya.DCplxTrans(1, angle, False, pya.DVector(start))

        # parameters needed for bridge creation
        curve_angle = pi/2
        corner_cut_dist = self.r
        curve_angle_2, corner_cut_dist_2 = curve_angle, corner_cut_dist

        l_direct = start.distance(end)
        if l_direct < 4*self.r:
            self.raise_error_on_cell(
                "Cannot create a Meander because start and end points are too close to each other.",
                (start + end)/2)
        if self.meanders < 1:
            self.meanders = int(l_direct/(2*self.r) - 1)  # automatically choose maximum possible number of meanders

        l_min = (self.meanders+1)*pi*self.r + (self.meanders - 1)*2*self.r + (l_direct - (self.meanders+1)*2*self.r)

        if self.length >= l_min:
            # create meander with 90-degree turns
            points = [pya.DPoint(0, 0)]
            l_rest = l_direct - self.meanders*2*self.r
            l_single_meander = (self.length - (l_rest - 2*self.r) - (self.meanders*2 + 2)*(pi/2)*self.r - (
                    self.meanders - 1)*self.r*2)/(2*self.meanders)

            points.append(pya.DPoint(l_rest/2, 0))
            for i in range(self.meanders):
                points.append(pya.DPoint(l_rest/2 + i*2*self.r, ((-1)**(i % 2))*(l_single_meander + 2*self.r)))
                points.append(
                    pya.DPoint(l_rest/2 + (i + 1)*2*self.r, ((-1)**(i % 2))*(l_single_meander + 2*self.r)))
            points.append(pya.DPoint(l_direct - l_rest/2, 0))
            points.append(pya.DPoint(l_direct, 0))

        elif self.length >= l_direct:
            # Create meander with non-90-degree turns.
            # The waveguide path points are in a "sawtooth" shape, with one point per meander (whereas 90-degree
            # meanders have two points per meander) and two points for the straight segments at the ends. In the
            # following, the one point at each meander is called "peak".

            x_increment = (l_direct - 2*self.r)/self.meanders  # x-distance between peaks of two meanders

            def length_diff(a):
                # a is the angle of one peak
                len1 = x_increment/(2*sin(a/2))  # length of diagonal straight line from x-axis to meander peak
                len2 = self.r*(pi - a)  # length of the curved waveguide piece at a peak
                len3 = self.r/tan(a/2)  # length missing from diagonal line due to curve at the peak
                len4 = len2/2  # length of the curved waveguide piece near the straight parts at both ends
                len5 = self.r/tan((a + pi)/4)  # length missing from horizontal and diagonal line due to the curve
                len_total = self.meanders*(2*len1 + len2 - 2*len3) + 2*(self.r + len4 - 2*len5)
                return self.length - len_total

            # find curve angle such that correct length is achieved with maximum number of meanders
            while True:
                min_angle = 1e-16  # smallest possible value for alpha needs to be != 0 to avoid division by zero
                alpha = brentq(length_diff, min_angle, pi)
                if x_increment/(2*sin(alpha/2)) - self.r/tan(alpha/2) - self.r/tan((alpha + pi)/4) \
                        > 0:
                    break
                self.meanders -= 1
                x_increment = (l_direct - 2*self.r)/self.meanders  # x-distance between peaks of two meanders
                if self.meanders < 1:
                    break

            if length_diff(alpha) > 1e-3:
                self.raise_error_on_cell(
                    "Cannot create a Meander with the given parameters. Try setting a different number of meanders.",
                    (start + end)/2)

            y_increment = x_increment/(2*tan(alpha/2))  # half of y-distance between peaks of two meanders

            points = [pya.DPoint(0, 0), pya.DPoint(self.r, 0)] + \
                     [pya.DPoint(self.r + i*x_increment - x_increment/2,
                                 y_increment * (2*(i % 2)-1)) for i in range(1, self.meanders+1)] + \
                     [pya.DPoint(l_direct - self.r, 0), pya.DPoint(l_direct, 0)]

            curve_angle = pi - alpha
            corner_cut_dist = self.r/tan(alpha/2)
            curve_angle_2 = pi - (alpha + pi)/2
            corner_cut_dist_2 = self.r/tan((alpha + pi)/4)

        else:
            self.raise_error_on_cell("Cannot create a Meander with the given parameters. Try increasing the length.",
                                     (start + end)/2)

        if self.n_bridges > 0:
            self._produce_bridges(points, transf, curve_angle, corner_cut_dist, curve_angle_2, corner_cut_dist_2)

        waveguide = self.add_element(WaveguideCoplanar, path=points)
        wg_inst, _ = self.insert_cell(waveguide, transf)
        self.copy_port("a", wg_inst)
        self.copy_port("b", wg_inst)

    def _produce_bridges(self, wg_points, meander_trans, curve_angle, corner_cut_dist, curve_angle_2,
                         corner_cut_dist_2):
        """Produces equally spaced airbridges on top of the meander waveguide.

        Args:
            wg_points: list of points for the waveguide path
            meander_trans: transformation applied to the entire meander
            curve_angle: angle of the curves at each meander
            corner_cut_dist: distance from waveguide path point to curve start for each meander
            curve_angle_2: angle of the curves after straight segments at each end
            corner_cut_dist_2: distance from waveguide path point to curve start for the curves after straight segments
                at each end
        """

        def insert_bridge(position, angle):
            self.insert_cell(Airbridge, meander_trans*pya.DCplxTrans(1, angle, False, position))

        bridge_separation = self.length/(self.n_bridges + 1)
        dist_to_next = bridge_separation
        n_inserted = 0

        for i in range(1, len(wg_points)):

            straight_len, straight_dir = vector_length_and_direction(wg_points[i] - wg_points[i - 1])
            if i in (1, len(wg_points) - 1):  # only one curve for first and last segment
                straight_len -= corner_cut_dist_2
            elif i in (2, len(wg_points) - 2):
                straight_len -= corner_cut_dist + corner_cut_dist_2
            else:
                straight_len -= 2*corner_cut_dist
            straight_len = max(0, straight_len)

            # bridges in the straight part of this segment

            remaining_len = straight_len
            cut_dist = corner_cut_dist if i > 2 else corner_cut_dist_2 if i > 1 else 0
            prev_pos = wg_points[i - 1] + cut_dist*straight_dir
            while dist_to_next < remaining_len and n_inserted < self.n_bridges:

                pos = prev_pos + dist_to_next*straight_dir

                insert_bridge(pos, get_angle(straight_dir))
                n_inserted += 1
                remaining_len -= dist_to_next
                dist_to_next = bridge_separation
                prev_pos = pos

            dist_to_next -= remaining_len

            # bridges in the curve at the end of this segment

            c_angle = curve_angle_2 if i in (1, len(wg_points) - 2) else curve_angle
            remaining_len = self.r*c_angle
            prev_angle = 0

            while dist_to_next < remaining_len and n_inserted < self.n_bridges and i < len(wg_points) - 1:

                v1, v2, angle1, angle2, corner_pos = \
                    WaveguideCoplanar.get_corner_data(wg_points[i - 1], wg_points[i], wg_points[i + 1], self.r)
                _, dir1 = vector_length_and_direction(v1)
                _, dir2 = vector_length_and_direction(v2)
                cut_dist = corner_cut_dist_2 if i in (1, len(wg_points) - 2) else corner_cut_dist
                p1 = wg_points[i] - cut_dist*dir1
                p2 = wg_points[i] + cut_dist*dir2

                angle3 = prev_angle + dist_to_next/self.r
                t = angle3/c_angle
                # interpolation along circular arc from p1 to p2 based on t
                # see https://en.wikipedia.org/wiki/Slerp
                pos = corner_pos + sin((1 - t)*c_angle)*(p1 - corner_pos)/sin(c_angle) \
                    + sin(t*c_angle)*(p2 - corner_pos)/sin(c_angle)
                # linear interpolation between angle1 and angle2 based on t
                angle4 = angle1*(1 - t) + angle2*t

                insert_bridge(pos, degrees(angle4))
                n_inserted += 1
                remaining_len -= dist_to_next
                dist_to_next = bridge_separation
                prev_angle = angle3

            dist_to_next -= remaining_len
