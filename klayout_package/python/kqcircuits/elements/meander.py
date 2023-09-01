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


from math import pi, cos, sin, tan, atan, atan2, degrees, sqrt
from scipy.optimize import brentq
from kqcircuits.util.parameters import add_parameters_from
from kqcircuits.elements.waveguide_coplanar_straight import WaveguideCoplanarStraight

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.util.geometry_helper import vector_length_and_direction, get_angle

@add_parameters_from(WaveguideCoplanarStraight, "ground_grid_in_trace")
class Meander(Element):
    """The PCell declaration for a meandering waveguide.

    Defined by two points, total length and number of meanders.

    The start and end points can be moved in GUI using the "Move"-tool. Alternatively, if a list of ``[x, y]``
    coordinates is given for ``start`` and ``end``, the GUI markers will not be shown. The latter is useful for
    code-generated cells that cannot be edited in the GUI.

    By default, the number of meanders is automatically chosen to minimize the area taken by bounding box of
    the meander. Uses the same bending radius as the underlying waveguide. Equidistant airbridges can be placed in the
    meander using ``n_bridges`` parameter.

       .. MARKERS_FOR_PNG 0,0
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
        l_direct = start.distance(end)
        if l_direct < 4*self.r:
            self.raise_error_on_cell(
                "Cannot create a Meander because start and end points are too close to each other.",
                (start + end)/2)
        if self.meanders < 1:
            self.meanders = int(l_direct/(2*self.r) - 1)  # automatically choose maximum possible number of meanders

        target_increment = self.length - l_direct  # target length increment compared to straight segment
        if target_increment < -1e-3:
            self.raise_error_on_cell("Cannot create a Meander with the given parameters. Try increasing the length.",
                                     (start + end) / 2)

        def bend_corner_displacement(w):
            """Returns x-displacement of corner point as function of bend width w.

            Waveguide starts as straight segment from origin (0,0) and ends with bend pointing towards x at (self.r,w).
            """
            if w >= self.r:
                return 0.0
            return (self.r - w) / (1 - w / (2 * self.r))

        def bend_length_increment(w):
            """Returns amount of waveguide length increment due to a single bend as function of bend width w.

            Waveguide starts as straight segment from origin (0,0) and ends with bend pointing towards x at (self.r,w).
            """
            if w >= self.r:
                return self.r * (pi / 2 - 2) + w
            h = w / self.r
            x = (1 - h) / (1 - h / 2)
            return self.r * (2 * atan(1 - x) + (x + h * (h - 1)) / sqrt(x ** 2 + h ** 2) - 1)

        def meander_length_increment(w):
            """Returns amount of waveguide length increment due to all meander bends as function of meander width w."""
            l0 = bend_length_increment(w / 4)  # starting and ending bend increment
            l1 = bend_length_increment(w / 2)  # middle bend increment
            return 4 * l0 + 2 * (self.meanders - 1) * l1

        # Create meander points
        points = [pya.DPoint(0, 0)]
        if target_increment > 1e-3:
            min_90deg_increment = meander_length_increment(4 * self.r)  # minimal length increment for 90-degree bends
            if target_increment >= min_90deg_increment:  # if all meander bends are 90 degrees
                width = 4 * self.r + (target_increment - min_90deg_increment) / self.meanders
            else:  # computation of meander width is not trivial, so we need to use root finding algorithm
                width = brentq(lambda w: meander_length_increment(w) - target_increment, 0.0, 4 * self.r)

            l_rest = l_direct / 2 - self.r * self.meanders  # distance to first corner
            x0 = bend_corner_displacement(width / 4)  # x-displacement of corner points in both ends
            x1 = bend_corner_displacement(width / 2)  # x-displacement of corner points in the middle of meander

            points.append(pya.DPoint(l_rest - x0, 0))
            points.append(pya.DPoint(l_rest + x0, width/2))
            for i in range(1, self.meanders):
                x = l_rest + 2 * self.r * i
                points.append(pya.DPoint(x - x1, (-1)**(i+1) * width / 2))
                points.append(pya.DPoint(x + x1, (-1)**i * width / 2))
            points.append(pya.DPoint(l_direct - l_rest - x0, (-1)**(self.meanders+1) * width / 2))
            points.append(pya.DPoint(l_direct - l_rest + x0, 0))
        points.append(pya.DPoint(l_direct, 0))

        # Create airbridges
        if self.n_bridges > 0:
            self._produce_bridges(points, transf)

        # Insert waveguide and ports
        waveguide = self.add_element(WaveguideCoplanar, path=points, ground_grid_in_trace=self.ground_grid_in_trace)
        wg_inst, _ = self.insert_cell(waveguide, transf)
        self.copy_port("a", wg_inst)
        self.copy_port("b", wg_inst)

    def _produce_bridges(self, points, trans):
        """Produces equally spaced airbridges on top of the meander waveguide.

        Args:
            points: list of points for the waveguide path
            trans: transformation applied to the entire meander
        """

        def insert_bridge(position, angle):
            self.insert_cell(Airbridge, trans*pya.DCplxTrans(1, angle, False, position))

        bridge_separation = self.length / (self.n_bridges + 1)
        dist_to_next = bridge_separation
        n_inserted = 0

        # Insert airbridges on bends and between bends
        for i in range(1, len(points)-1):
            v1, _, a1, a2, c_pos = WaveguideCoplanar.get_corner_data(points[i - 1], points[i], points[i + 1], self.r)
            alpha = (a2 - a1 + pi) % (2 * pi) - pi  # turn angle (between -pi and pi) in radians
            sign_r = (self.r if alpha > 0 else -self.r)  # positive or negative radius depending on turn signature
            length, direction = vector_length_and_direction(v1)
            cut_dist = self.r * tan(abs(alpha) / 2)  # distance between corner point and beginning of straights

            dist_to_next -= length - cut_dist
            while dist_to_next <= 0.0:  # insert airbridges on straight segment before corner
                insert_bridge(points[i] + (dist_to_next - cut_dist) * direction, degrees(a1))
                dist_to_next += bridge_separation
                n_inserted += 1
                if n_inserted >= self.n_bridges:
                    return
            dist_to_next -= alpha * sign_r
            while dist_to_next <= 0.0:  # insert airbridges on corner segment
                a = a2 + dist_to_next / sign_r
                insert_bridge(c_pos + sign_r * pya.DVector(sin(a), -cos(a)), degrees(a))
                dist_to_next += bridge_separation
                n_inserted += 1
                if n_inserted >= self.n_bridges:
                    return
            dist_to_next += cut_dist

        # Insert airbridges on the last segment
        length, direction = vector_length_and_direction(points[-1] - points[-2])
        dist_to_next -= length
        while dist_to_next <= 0.0:  # insert airbridges on last straight segment
            insert_bridge(points[-1] + dist_to_next * direction, get_angle(direction))
            dist_to_next += bridge_separation
            n_inserted += 1
            if n_inserted >= self.n_bridges:
                return
