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


from math import pi, tan, degrees, atan2

from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_curved import WaveguideCoplanarCurved
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import vector_length_and_direction, is_clockwise
from kqcircuits.util.parameters import Param, pdt, add_parameters_from


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

    Airbridges can optionally be placed with a given spacing along the resonator waveguide.

    """

    length = Param(pdt.TypeDouble, "Resonator length", 5000, unit="μm")
    input_path = Param(pdt.TypeShape, "Input waveguide path", pya.DPath([pya.DPoint(-200, 0), pya.DPoint(0, 0)], 10))
    poly_path = Param(pdt.TypeShape, "Polygon path",
                      pya.DPath([pya.DPoint(0, 800), pya.DPoint(1000, 0), pya.DPoint(0, -800)], 10))
    auto_spacing = Param(pdt.TypeBoolean, "Use automatic spacing", True)
    manual_spacing = Param(pdt.TypeDouble, "Manual spacing between waveguide centers", 300, unit="μm")
    bridges = Param(pdt.TypeBoolean, "Airbridges", False)
    bridge_spacing = Param(pdt.TypeDouble, "Airbridge spacing", 300, unit="μm")

    def produce_impl(self):

        if self.auto_spacing:
            self._produce_resonator_automatic_spacing()
        else:
            self._produce_resonator_manual_spacing()

        super().produce_impl()

    def _produce_resonator_automatic_spacing(self):
        """Produces polygon spiral resonator with automatically determined waveguide spacing.

        This creates resonators with different spacing, until it finds the largest spacing that can be used to create
        a valid resonator. Only the final resonator with optimal spacing is inserted to `self.cell` in the end.
        """
        # find optimal spacing using bisection method
        min_spacing, max_spacing = 0, self.length
        optimal_points = self._produce_path_points(min_spacing)
        if optimal_points is None:
            self.raise_error_on_cell("Cannot create a resonator with the given parameters. Try decreasing the turn "
                                     "radius.", (self.input_path.bbox() + self.poly_path.bbox()).center())

        spacing_tolerance = 0.001
        while max_spacing - min_spacing > spacing_tolerance:
            spacing = (min_spacing + max_spacing) / 2
            points = self._produce_path_points(spacing)
            if points is not None:
                optimal_points = points
                min_spacing = spacing
            else:
                max_spacing = spacing
        self._produce_resonator(optimal_points)

    def _produce_resonator_manual_spacing(self):
        """Produces polygon spiral resonator with spacing defined by `self.manual_spacing`.

        If the resonator cannot be created with the chosen spacing, it will instead raise a ValueError.
        """
        points = self._produce_path_points(self.manual_spacing)
        if points is None:
            self.raise_error_on_cell("Cannot create a resonator with the given parameters. Try decreasing the spacings "
                                     "or the turn radius.", (self.input_path.bbox() + self.poly_path.bbox()).center())
        self._produce_resonator(points)

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
            if last_segment_len < corner_cut_dist - 1e-13:
                return None

            # if the previous segment is not long enough for the curves at each end, resonator cannot be created
            if len(pts) > 3:
                corner_cut_dist += self._corner_cut_distance(pts[-4], pts[-3], pts[-2])
            if (pts[-2] - pts[-3]).length() < corner_cut_dist - 1e-13:
                return None

            return updated_length

        # segments based on input_path points
        input_path_points_iter = self.input_path.each_point()
        length = 0.0
        points = [next(input_path_points_iter)]
        while True:
            try:
                points.append(next(input_path_points_iter))
            except StopIteration:
                break

            # Update length after adding the last point
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
            poly_edges = [pya.DEdge(poly_points[i - 1], poly_points[i]) for i in range(n_poly_points)]
            clockwise = is_clockwise(poly_points)
            # get the normal vectors (toward inside of polygon) of each edge
            normals = []
            for edge in poly_edges:
                _, direction = vector_length_and_direction(edge.p2 - edge.p1)
                normals.append(pya.DVector(direction.y, -direction.x) if clockwise else
                               pya.DVector(-direction.y, direction.x))
            i = 0
            current_edge = poly_edges[0]
            while True:
                # get the edge with i//len spacing from the corresponding poly edge
                next_edge_without_shift = poly_edges[(i + 1) % n_poly_points]
                shift = spacing*((i + 1)//n_poly_points)*normals[(i + 1) % n_poly_points]
                next_edge = pya.DEdge(next_edge_without_shift.p1 + shift, next_edge_without_shift.p2 + shift)
                # Find intersection point of the lines defined by current_edge and next_edge.
                # We use `extended` since we want intersections between the "infinite" lines instead of finite edges.
                intersection_point = current_edge.extended(1e7).crossing_point(next_edge.extended(1e7))
                # if the shift was so large that the new segment would end up in the opposite direction,
                # resonator cannot be created
                if (intersection_point - points[-1]).sprod_sign(current_edge.d()) <= 0:
                    return None

                # Append point and update length
                points.append(intersection_point)
                length = get_updated_length(points, length)
                if length is None:
                    return None

                # Compute outer curve shortcut length for the last point.
                # This may limit the length of the last straight segment to avoid overlapping with the outer segment.
                if i >= n_poly_points and self.r > spacing:
                    next_corner_cut_dist = self._corner_cut_distance(poly_points[(i - 1) % n_poly_points],
                                                                     poly_points[i % n_poly_points],
                                                                     poly_points[(i + 1) % n_poly_points])
                    shortcut_length = (self.r - spacing) / self.r * next_corner_cut_dist
                else:
                    shortcut_length = 0.0

                # Test if the resonator is long enough
                if length - shortcut_length >= self.length:
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
        tmp_cell = self.add_element(WaveguideCoplanar, SpiralResonatorPolygon, path=pya.DPath(points, 0))
        length = tmp_cell.length()

        # handle correctly the last waveguide segment
        last_segment_curved = self._fix_waveguide_end(points, length)
        term2 = 0 if last_segment_curved else self.term2

        # produce bridges
        if self.bridges:
            dist_to_next_bridge = self.bridge_spacing
            for i in range(1, len(points)):
                dist_to_next_bridge = self._produce_airbridges_for_segment(points, i, dist_to_next_bridge)

        wg_cell = self.add_element(WaveguideCoplanar, SpiralResonatorPolygon, path=pya.DPath(points, 0), term2=term2)
        self.insert_cell(wg_cell)

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
                points[-1] -= corner_cut_dist * vector_length_and_direction(points[-1] - points[-2])[1]
                # calculate how long the new curve piece needs to be
                tmp_cell = self.add_element(WaveguideCoplanar, SpiralResonatorPolygon, path=pya.DPath(points, 0))
                curve_length = self.length - tmp_cell.length()
                curve_alpha = curve_length / self.r
                # add new curve piece at the waveguide end
                curve_cell = self.add_element(WaveguideCoplanarCurved, SpiralResonatorPolygon, alpha=curve_alpha)
                curve_trans = pya.DCplxTrans(1, degrees(alpha1) - v1.vprod_sign(v2)*90, v1.vprod_sign(v2) < 0,
                                             corner_pos)
                self.insert_cell(curve_cell, curve_trans)
                WaveguideCoplanarCurved.produce_curve_termination(self, curve_alpha, self.term2, curve_trans)
                return True

        # set last point to correct position based on length
        points[-1] = points[-1] - extra_len * last_seg_dir
        return False

    def _produce_airbridges_for_segment(self, points, end_point_idx, dist_to_next_bridge):
        """Produces airbridges in the segment between points[end_point_idx-1] and points[end_point_idx].

        Args:
            points: list of points used to create the resonator waveguide
            end_point_idx: index of the segment end point
            dist_to_next_bridge: distance until the next airbridge should created

        Returns:
            distance until the next airbridge should created
        """
        segment_len, segment_dir = vector_length_and_direction(points[end_point_idx] - points[end_point_idx - 1])
        bridge_width = Airbridge.get_schema()["pad_width"].default
        remaining_len = segment_len - bridge_width
        prev_pos = points[end_point_idx - 1]
        # ensure that the bridge will not be too close to the corner before
        if end_point_idx - 2 >= 0:
            corner_1_cut_dist = self._corner_cut_distance(points[end_point_idx - 2], points[end_point_idx - 1],
                                                          points[end_point_idx])
            dist_to_next_bridge = max(dist_to_next_bridge, corner_1_cut_dist)
        while remaining_len > dist_to_next_bridge:
            add_bridge = True
            # ensure that the bridge will not be too close to the corner after
            if end_point_idx + 1 < len(points):
                corner_2_cut_dist = self._corner_cut_distance(points[end_point_idx - 1], points[end_point_idx],
                                                              points[end_point_idx + 1])
                if remaining_len - dist_to_next_bridge < corner_2_cut_dist:
                    remaining_len = 0
                    dist_to_next_bridge = 0
                    add_bridge = False
            # create bridge
            if add_bridge:
                pos = prev_pos + dist_to_next_bridge*segment_dir
                angle = degrees(atan2(segment_dir.y, segment_dir.x))
                self.insert_cell(Airbridge, pya.DCplxTrans(1, angle, False, pos), face_ids=self.face_ids)
                remaining_len -= dist_to_next_bridge
                dist_to_next_bridge = self.bridge_spacing
                prev_pos = pos
        dist_to_next_bridge -= remaining_len
        return dist_to_next_bridge

    def _corner_cut_distance(self, point1, point2, point3):
        """Returns the distance from waveguide path corner to the start of a curved waveguide placed at the corner.

        Args:
            point1: point before corner
            point2: corner point
            point3: point after corner

        """
        _, _, alpha1, alpha2, _ = WaveguideCoplanar.get_corner_data(point1, point2, point3, self.r)
        abs_curve = pi - abs(pi - abs(alpha2 - alpha1))
        return self.r*tan(abs_curve/2)
