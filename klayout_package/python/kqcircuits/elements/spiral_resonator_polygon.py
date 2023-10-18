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


from math import pi, tan, degrees, atan2, sqrt

from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridges.airbridge_multi_face import AirbridgeMultiFace
from kqcircuits.elements.element import Element
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_curved import WaveguideCoplanarCurved
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import vector_length_and_direction, is_clockwise, get_angle
from kqcircuits.util.parameters import Param, pdt, add_parameters_from


@add_parameters_from(AirbridgeMultiFace)
@add_parameters_from(WaveguideCoplanar, "term1", "term2")
class SpiralResonatorPolygon(Element):
    """The PCell declaration for a polygon shaped spiral resonator.

    The resonator waveguide starts at the first point of `self.input_path` and goes through each each of its points. The
    last point of `self.input_path` will connect to the first point of `self.poly_path`, unless the length of
    `self.input_path` is already longer than `self.length`.

    The polygon shape is defined by `self.poly_path`, where each point is a vertex of the polygon. The points should
    either be in clockwise or counter-clockwise order. The waveguide will first continue along the polygon edges, and
    then spiral inside the polygon such that each segment will be parallel to one of the edges defined by
    `self.polygon_path`.

    Note, that if you want the segment from `self.input_path` to `self.poly_path` to be "a part of the spiral"
    (following the polygon shape), you will need to choose the points such that the edge
    `self.input_path[-1] - self.poly_path[0]` is parallel to the edge `self.poly_path[0] - self.poly_path[-1]`.

    The spacing between waveguides in the spiral can either be chosen manually or automatically. The automatic spacing
    attempts to find the largest possible spacing.

    Airbridges can optionally be placed with a given spacing along the resonator waveguide by setting non-zero value to
    `bridge_spacing`. Alternatively, one can independently set number of airbridges on each straight segment of spiral
    polygon by using parameter `n_bridges_pattern`.

    Non-negative value to `connector_dist` inserts face-to-face connector to spiral resonator so that the beginning and
    the end of resonator will be on different faces.
    """

    length = Param(pdt.TypeDouble, "Resonator length", 5000, unit="μm")
    input_path = Param(pdt.TypeShape, "Input waveguide path", pya.DPath([pya.DPoint(-200, 0), pya.DPoint(0, 0)], 10))
    poly_path = Param(pdt.TypeShape, "Polygon path",
                      pya.DPath([pya.DPoint(0, 800), pya.DPoint(1000, 0), pya.DPoint(0, -800)], 10))
    auto_spacing = Param(pdt.TypeBoolean, "Use automatic spacing", True)
    manual_spacing = Param(pdt.TypeList, "Manual spacing pattern", [300], unit="[μm]")
    bridge_spacing = Param(pdt.TypeDouble, "Airbridge spacing", 0, unit="μm")
    n_bridges_pattern = Param(pdt.TypeList, "Pattern for number of airbridges on edges", [0])
    connector_dist = Param(pdt.TypeDouble, "Face to face connector distance from beginning", -1, unit="µm",
                           docstring="Negative value means single face resonator without connector.")

    def build(self):
        if isinstance(self.input_path, list):
            self.input_path = pya.DPath(self.input_path, 1)
        if isinstance(self.poly_path, list):
            self.poly_path = pya.DPath(self.poly_path, 1)

        if self.auto_spacing:
            self._produce_resonator_automatic_spacing()
        else:
            self._produce_resonator_manual_spacing()

    def _produce_resonator_automatic_spacing(self):
        """Produces polygon spiral resonator with automatically determined waveguide spacing.

        This creates resonators with different spacing, until it finds the largest spacing that can be used to create
        a valid resonator. Only the final resonator with optimal spacing is inserted to `self.cell` in the end.
        """
        def polygon_min_diameter(path):
            p = list(path.each_point())
            n = len(p)
            diams = []
            for i in range(n):
                _, v = vector_length_and_direction(p[(i + 1) % n] - p[i])
                diams.append(max([abs(v.vprod(p[j % n] - p[i])) for j in range(i+2, i+n)]))
            return min(diams)

        # find optimal spacing using bisection method
        min_spacing, max_spacing = 0, polygon_min_diameter(self.poly_path) / 2
        optimal_points = self._produce_path_points([min_spacing])
        if optimal_points is None:
            self.raise_error_on_cell("Cannot create a resonator with the given parameters. Try decreasing the turn "
                                     "radius.", (self.input_path.bbox() + self.poly_path.bbox()).center())

        spacing_tolerance = 0.001
        while max_spacing - min_spacing > spacing_tolerance:
            spacing = (min_spacing + max_spacing) / 2
            points = self._produce_path_points([spacing])
            if points is not None:
                optimal_points = points
                min_spacing = spacing
            else:
                max_spacing = spacing
        self._produce_resonator(optimal_points)
        self.add_port("a", optimal_points[0], optimal_points[0] - optimal_points[1])

    def _produce_resonator_manual_spacing(self):
        """Produces polygon spiral resonator with spacing defined by `self.manual_spacing`.

        If the resonator cannot be created with the chosen spacing, it will instead raise a ValueError.
        """
        sp = [float(s) for s in self.manual_spacing] if isinstance(self.manual_spacing, list) else [self.manual_spacing]
        points = self._produce_path_points(sp)
        if points is None:
            self.raise_error_on_cell("Cannot create a resonator with the given parameters. Try decreasing the spacings "
                                     "or the turn radius.", (self.input_path.bbox() + self.poly_path.bbox()).center())
        self._produce_resonator(points)
        self.add_port("a", points[0], points[0] - points[1])

    def _produce_path_points(self, spacing):
        """Creates resonator path points with the given spacing.
        Function _produce_resonator takes these points as an argument.
        If spacing is unsuitable for creating points, the return value is None.

        Args:
            spacing: spacing between waveguide centers inside the polygon

        Returns:
            List of DPoints or None
        """

        def get_updated_length(pts, prev_length):
            """Updates the resonator length by adding the last point.

            Args:
                pts: list of DPoints
                prev_length: resonator length before adding the last point

            Returns:
                 resonator length including all points (or None if waveguide bends can't fit)
            """
            if len(pts) <= 1:
                return 0.0

            last_segment_len = (pts[-1] - pts[-2]).length()
            if len(pts) == 2:
                return last_segment_len

            # compute new length for the resonator
            _, _, alpha1, alpha2, _ = WaveguideCoplanar.get_corner_data(pts[-3], pts[-2], pts[-1], self.r)
            abs_curve = pi - abs(pi - abs(alpha2 - alpha1))
            corner_cut_dist = self.r * tan(abs_curve / 2)
            updated_length = prev_length - 2 * corner_cut_dist + self.r * abs_curve + last_segment_len

            # if the new segment is not long enough for the curve in the beginning, resonator cannot be created
            if last_segment_len < corner_cut_dist - 1e-5:
                return None

            # if the previous segment is not long enough for the curves at each end, resonator cannot be created
            if len(pts) > 3:
                corner_cut_dist += self._corner_cut_distance(pts[-4], pts[-3], pts[-2])[0]
            if (pts[-2] - pts[-3]).length() < corner_cut_dist - 1e-5:
                return None

            return updated_length

        # segments based on input_path points
        input_points = list(self.input_path.each_point())
        length = 0.0
        points = []
        for ip in input_points:
            # Update length after adding a point
            points.append(ip)
            length = get_updated_length(points, length)
            if length is None:
                return None

            # Test if the resonator is long enough
            if length >= self.length:
                return points

        # segments based on poly_path points
        poly_points = list(self.poly_path.each_point())
        n_poly_points = len(poly_points)
        if n_poly_points > 2:
            poly_edges = [pya.DEdge(poly_points[i], poly_points[(i+1) % n_poly_points]) for i in range(n_poly_points)]
            clockwise = is_clockwise(poly_points)
            # get the normal vectors (toward inside of polygon) of each edge
            normals = []
            for edge in poly_edges:
                _, direction = vector_length_and_direction(edge.p2 - edge.p1)
                normals.append(pya.DVector(direction.y, -direction.x) if clockwise else
                               pya.DVector(-direction.y, direction.x))
            # define amount of spacing for the first round
            shifts = [0.0] * len(poly_edges)
            if len(points) > 0:
                _, input_dir = vector_length_and_direction(poly_points[0] - points[-1])
                _, poly_dir = vector_length_and_direction(poly_points[0] - poly_points[-1])
                shifts[-1] = max(0.0, spacing[-1] * input_dir.sprod(poly_dir))
            i = 0
            current_edge = poly_edges[-1]
            while True:
                # get the edge shifted with spacing from the corresponding poly edge
                next_edge_without_shift = poly_edges[i % n_poly_points]
                shift = shifts[i % n_poly_points] * normals[i % n_poly_points]
                shifts[i % n_poly_points] += spacing[i % len(spacing)]
                next_edge = pya.DEdge(next_edge_without_shift.p1 + shift, next_edge_without_shift.p2 + shift)
                # Find intersection point of the lines defined by current_edge and next_edge.
                # We use `extended` since we want intersections between the "infinite" lines instead of finite edges.
                # Use  "intersection_point = current_edge.cut_point(next_edge)" after Klayout 0.26 support is dropped.
                intersection_point = current_edge.extended(1e7).crossing_point(next_edge.extended(1e7))
                # if the shift was so large that the new segment would end up in the opposite direction,
                # resonator cannot be created
                if i > 0 >= (intersection_point - points[-1]).sprod_sign(current_edge.d()):
                    return None

                # Append point and update length
                points.append(intersection_point)
                length = get_updated_length(points, length)
                if length is None:
                    return None

                # Test if the resonator is long enough
                if length >= self.length:
                    if i < n_poly_points:  # Outest segments don't need overlapping consideration
                        return points

                    # Check outer curve shortcut length to avoid inner segments overlapping with the outer curve.
                    i_out = len(points) - n_poly_points - 1
                    if i_out <= 0:  # Outer curve doesn't exist because input_path is empty
                        return points

                    corner_diff = points[-1] - points[i_out]  # vector from outer corner to inner corner
                    _, inner_dir = vector_length_and_direction(points[-1] - points[-2])
                    s_cut = corner_diff.sprod(inner_dir)
                    if s_cut >= 0:  # For concave corner, segment cannot overlap with outer curve
                        return points

                    # For convex corner, allow straight segment until the outer curve begins.
                    _, outer_dir = vector_length_and_direction(points[i_out] - points[i_out - 1])
                    r_cut, _ = self._corner_cut_distance(points[i_out - 1], points[i_out], points[i_out + 1])
                    if length - max(0.0, s_cut + r_cut * outer_dir.sprod(inner_dir)) >= self.length:
                        return points

                # prepare for the next iteration
                current_edge = next_edge
                i += 1

        return None

    def _produce_resonator(self, points):
        """Produces a polygon spiral resonator with the given path points

        Args:
            points: List of DPoints created by function _produce_path_points
        """
        tmp_cell = self.add_element(WaveguideCoplanar, path=points)
        length = tmp_cell.length()

        # handle correctly the last waveguide segment
        last_segment_curved = self._fix_waveguide_end(points, length)
        term2 = 0 if last_segment_curved else self.term2

        # produce bridges
        self._produce_airbridges(points)

        # insert waveguide with or without connector
        if self.connector_dist >= 0:
            self._produce_wg_with_connector(points, term2)
        else:
            self.insert_cell(WaveguideCoplanar, path=points, term2=term2)

    def _fix_waveguide_end(self, points, current_length):
        """Modifies the last points and places a WaveguideCoplanarCurved element at the end if needed.

        This is required since WaveguideCoplanar cannot end in the middle of a curved segment.

        Args:
            points: list of points used to create the resonator waveguide, may be modified by this method
            current_length: length of the resonator if points are not modified

        Returns:
            True if the last segment is curved and False if it's straight
        """
        extra_len = current_length - self.length
        last_seg_len, last_seg_dir = vector_length_and_direction(points[-1] - points[-2])
        if len(points) > 2:
            v1, v2, alpha1, alpha2, corner_pos = WaveguideCoplanar.get_corner_data(points[-3], points[-2], points[-1],
                                                                                   self.r)
            # distance between points[-2] and start of the curve
            corner_cut_dist = self.r * tan((pi - abs(pi - abs(alpha2 - alpha1))) / 2)
            # check if last waveguide segment is too short to be straight
            if last_seg_len - extra_len < corner_cut_dist:
                # remove last point and move the new last point to the start position of the old curve
                points.pop()
                _, new_last_dir = vector_length_and_direction(points[-1] - points[-2])
                points[-1] -= corner_cut_dist * new_last_dir
                # calculate how long the new curve piece needs to be
                if len(points) > 2:
                    tmp_cell = self.add_element(WaveguideCoplanar, path=points)
                    curve_length = self.length - tmp_cell.length()
                    if curve_length <= 0.0:
                        points[-1] += curve_length * new_last_dir
                        return False
                else:
                    curve_length = self.length - (points[-1] - points[-2]).length()
                curve_alpha = curve_length / self.r
                # add new curve piece at the waveguide end
                fids = [0, 1] if self.connector_dist < 0 else [1, 0]
                curve_cell = self.add_element(WaveguideCoplanarCurved, alpha=curve_alpha,
                                              face_ids=[self.face_ids[f] for f in fids])
                curve_trans = pya.DCplxTrans(1, degrees(alpha1) - v1.vprod_sign(v2)*90, v1.vprod_sign(v2) < 0,
                                             corner_pos)
                self.insert_cell(curve_cell, curve_trans)
                WaveguideCoplanarCurved.produce_curve_termination(self, curve_alpha, self.term2, curve_trans, fids[0])
                return True

        # set last point to correct position based on length
        points[-1] = points[-1] - extra_len * last_seg_dir
        return False

    def _produce_airbridges(self, points):
        """Produces airbridges defined either by self.bridge_spacing or self.n_bridges_pattern.

        All airbridges have at least half bridge width distance to end of the straight.

        Args:
            points: list of points used to create the resonator waveguide
        """
        # Create airbridges by self.bridge_spacing
        bridge_width = Airbridge.get_schema()["bridge_width"].default
        if self.bridge_spacing > 0.0:
            dist_to_next_bridge = self.bridge_spacing
            for i in range(0, len(points) - 1):
                segment_len, segment_dir = vector_length_and_direction(points[i + 1] - points[i])
                cut_dist, curve_len = (self._corner_cut_distance(points[i], points[i + 1], points[i + 2])
                                       if i + 2 < len(points) else (0.0, 0.0))
                end_of_straight = segment_len - bridge_width - cut_dist

                angle = degrees(atan2(segment_dir.y, segment_dir.x))
                while dist_to_next_bridge < end_of_straight:
                    pos = points[i] + dist_to_next_bridge * segment_dir
                    self.insert_cell(Airbridge, pya.DCplxTrans(1, angle, False, pos))
                    dist_to_next_bridge += self.bridge_spacing
                dist_to_next_bridge = max(dist_to_next_bridge - segment_len + 2 * cut_dist - curve_len,
                                          cut_dist + bridge_width)

        # Create airbridges by self.n_bridges_pattern
        nb = [int(n) for n in self.n_bridges_pattern] if isinstance(self.n_bridges_pattern, list) else []
        n_beg = self.input_path.num_points()
        if any(nb) and n_beg < len(points) - 2:
            cut_dist0, _ = self._corner_cut_distance(points[n_beg - 1], points[n_beg], points[n_beg + 1])
            for i in range(n_beg, len(points) - 2):
                segment_len, segment_dir = vector_length_and_direction(points[i+1] - points[i])
                cut_dist1, _ = self._corner_cut_distance(points[i], points[i + 1], points[i + 2])

                n_bridges = nb[(i - n_beg) % len(nb)]
                shift = 0.5 - 0.5 * (((i - n_beg) // len(nb)) % 2)
                ab_dist = (segment_len - cut_dist0 - cut_dist1 - 2 * bridge_width) / (n_bridges - 0.5)
                angle = degrees(atan2(segment_dir.y, segment_dir.x))
                for b in range(n_bridges):
                    pos = points[i] + (cut_dist0 + bridge_width + (b + shift) * ab_dist) * segment_dir
                    self.insert_cell(Airbridge, pya.DCplxTrans(1, angle, False, pos))
                cut_dist0 = cut_dist1

    def _produce_wg_with_connector(self, points, term2):
        """Produces waveguide with face-to-face connector.

        Args:
            points: list of points used to create the resonator waveguide
            term2: end termination
        """
        # add connector cell and get connector length
        conn_cell = self.add_element(FlipChipConnectorRf)
        conn_ref = self.get_refpoints(conn_cell)
        port0 = self.face_ids[0] + "_port"
        port1 = self.face_ids[1] + "_port"
        conn_len, conn_dir = vector_length_and_direction(conn_ref[port1] - conn_ref[port0])

        def insert_wg_with_connector(segment, distance):
            s_len, s_dir = vector_length_and_direction(points[segment + 1] - points[segment])
            b_pos = points[segment] + distance * s_dir
            ang = get_angle(s_dir) - get_angle(conn_dir)
            trans = pya.DCplxTrans(1.0, ang, False, b_pos) * pya.DTrans(-conn_ref[port0])
            t_pos = self.insert_cell(conn_cell, trans=trans)[1][port1]
            if segment == 0 and distance < 1e-3:
                WaveguideCoplanar.produce_end_termination(self, t_pos, b_pos, self.term1)
            else:
                self.insert_cell(WaveguideCoplanar, path=points[:segment + 1] + [b_pos], term2=0)
            if segment + 2 == len(points) and s_len - conn_len - distance < 1e-3:
                WaveguideCoplanar.produce_end_termination(self, b_pos, t_pos, term2, face_index=1)
            else:
                self.insert_cell(WaveguideCoplanar, path=[t_pos] + points[segment + 1:],
                                 term1=0, term2=term2, face_ids=self.face_ids[1::-1])

        last = {}  # parameters for last possible connector position
        prev_len = 0.0
        prev_cut_dist = 0.0
        for i, p in enumerate(points):
            if i + 1 >= len(points):
                if last:
                    insert_wg_with_connector(**last)
                    return
                self.raise_error_on_cell("Face-to-face connector cannot fit.",
                                         (self.input_path.bbox() + self.poly_path.bbox()).center())
            corner_cut_dist, corner_length = ((0.0, 0.0) if i + 2 == len(points) else
                                              self._corner_cut_distance(p, points[i + 1], points[i + 2]))
            segment_len, _ = vector_length_and_direction(points[i + 1] - p)
            straight_len = segment_len - prev_cut_dist - corner_cut_dist
            if conn_len <= straight_len:
                last = {'segment': i, 'distance': segment_len - corner_cut_dist - conn_len}
                dist = self.connector_dist - conn_len / 2 - prev_len + prev_cut_dist
                if dist <= last['distance']:
                    insert_wg_with_connector(i, max(prev_cut_dist, dist))
                    return
            prev_len += straight_len + corner_length
            prev_cut_dist = corner_cut_dist

    def _corner_cut_distance(self, point1, point2, point3):
        """Returns the distance from waveguide path corner to the start of the curve and the curve length.

        Args:
            point1: point before corner
            point2: corner point
            point3: point after corner

        Returns:
            corner cut distance, curve length
        """
        _, _, alpha1, alpha2, _ = WaveguideCoplanar.get_corner_data(point1, point2, point3, self.r)
        abs_curve = pi - abs(pi - abs(alpha2 - alpha1))
        return self.r*tan(abs_curve/2), self.r * abs_curve


def rectangular_parameters(above_space=500, below_space=400, right_space=1000, x_spacing=100, y_spacing=100,
                           bridges_left=False, bridges_bottom=False, bridges_right=False, bridges_top=False,
                           r=Element.get_schema()["r"].default, **kwargs):
    """A utility function to easily produce rectangular spiral resonator (old SpiralResonatorRectangle).

    Args:
        above_space: Space above the input (µm)
        below_space: Space below the input (µm)
        right_space: Space right of the input (µm)
        x_spacing: Spacing between vertical segments (µm)
        y_spacing: Spacing between horizontal segments (µm)
        bridges_left: Crossing airbridges left
        bridges_bottom: Crossing airbridges bottom
        bridges_right: Crossing airbridges right
        bridges_top: Crossing airbridges top
        r: Turn radius (µm)

    Returns:
        dictionary of parameters for SpiralResonatorPolygon
    """
    defaults = {"manual_spacing": [y_spacing, x_spacing], "r": r}
    if above_space == 0:
        params = {"input_path": pya.DPath([], 10),
                  "poly_path": pya.DPath([pya.DPoint(0, above_space), pya.DPoint(right_space, above_space),
                                          pya.DPoint(right_space, -below_space), pya.DPoint(0, -below_space)], 10),
                  "n_bridges_pattern": [bridges_top, bridges_right, bridges_bottom, bridges_left]}
    elif below_space == 0:
        params = {"input_path": pya.DPath([], 10),
                  "poly_path": pya.DPath([pya.DPoint(0, -below_space), pya.DPoint(right_space, -below_space),
                                          pya.DPoint(right_space, above_space), pya.DPoint(0, above_space)], 10),
                  "n_bridges_pattern": [bridges_bottom, bridges_right, bridges_top, bridges_left]}
    elif above_space > below_space:
        x1 = sqrt(above_space / (4 * r - above_space)) * r if above_space < 2 * r else r
        x2 = (sqrt((4 * r - above_space) * above_space) if above_space < 2 * r else 2 * r) - x1
        params = {"input_path": pya.DPath([pya.DPoint(0, 0), pya.DPoint(x1, 0)], 10),
                  "poly_path": pya.DPath([pya.DPoint(x2, above_space), pya.DPoint(right_space, above_space),
                                          pya.DPoint(right_space, -below_space), pya.DPoint(x2, -below_space)], 10),
                  "n_bridges_pattern": [bridges_top, bridges_right, bridges_bottom, bridges_left]}
    else:
        x1 = sqrt(below_space / (4 * r - below_space)) * r if below_space < 2 * r else r
        x2 = (sqrt((4 * r - below_space) * below_space) if below_space < 2 * r else 2 * r) - x1
        params = {"input_path": pya.DPath([pya.DPoint(0, 0), pya.DPoint(x1, 0)], 10),
                  "poly_path": pya.DPath([pya.DPoint(x2, -below_space), pya.DPoint(right_space, -below_space),
                                          pya.DPoint(right_space, above_space), pya.DPoint(x2, above_space)], 10),
                  "n_bridges_pattern": [bridges_bottom, bridges_right, bridges_top, bridges_left]}

    return {**defaults, **params, **kwargs}
