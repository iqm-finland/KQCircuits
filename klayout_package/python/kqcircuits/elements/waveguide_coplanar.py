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
from kqcircuits.util.parameters import Param, pdt, add_parameters_from

from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar_straight import WaveguideCoplanarStraight
from kqcircuits.elements.waveguide_coplanar_curved import WaveguideCoplanarCurved


@add_parameters_from(WaveguideCoplanarStraight, "add_metal", "ground_grid_in_trace")
class WaveguideCoplanar(Element):
    """The PCell declaration for an arbitrary coplanar waveguide.

    Coplanar waveguide defined by the width of the center conductor and gap. It can follow any segmented lines with
    predefined bending radios. It actually consists of straight and bent PCells. Termination lengths are lengths of
    extra ground gaps for opened transmission lines

    The ``path`` parameter defines the waypoints of the waveguide. When a DPath is supplied, the waypoints can be edited
    in the KLayout GUI with the Partial tool. Alternatively, a list of DPoint can be supplied, in which case the
    guiding shape is not visible in the GUI. This is useful for code-generated (sub)cells where graphical editing is not
    possible or desired.

    Warning:
        Arbitrary angle bents can have very small gaps between bends and straight segments due to
        precision of arithmetic. Small positive value of corner_safety_overlap can avoid these gaps.

    .. MARKERS_FOR_PNG 20,-10 50,0
    """

    path = Param(pdt.TypeShape, "TLine", pya.DPath([pya.DPoint(0, 0), pya.DPoint(100, 0)], 0))
    term1 = Param(pdt.TypeDouble, "Termination length start", 0, unit="μm")
    term2 = Param(pdt.TypeDouble, "Termination length end", 0, unit="μm")
    corner_safety_overlap = Param(pdt.TypeDouble, "Extend straight sections near corners", 0.001, unit="μm",
        docstring="Extend straight sections near corners by this amount (μm) to ensure all sections overlap")

    def can_create_from_shape_impl(self):
        return self.shape.is_path()

    def parameters_from_shape_impl(self):
        points = [pya.DPoint(point * self.layout.dbu) for point in self.shape.each_point()]
        self.path = pya.DPath(points, 1)

    def transformation_from_shape_impl(self):
        return pya.Trans()

    def produce_waveguide(self):
        if isinstance(self.path, list):
            points = [pya.DPoint(p) if isinstance(p, pya.DVector) else p for p in self.path]
        else:
            points = list(self.path.each_point())

        if len(points) < 2:
            self.raise_error_on_cell("Need at least 2 points for a waveguide.",
                                     points[0] if len(points) == 1 else pya.DPoint())

        # distance between points[0] and beginning of the straight
        last_cut_dist = 0.0 if self.term1 == 0 else -self.corner_safety_overlap

        # For each segment except the last
        for i in range(0, len(points) - 2):
            # Check if straight can fit between points[i] and points[i + 1]
            v1, _, alpha1, alpha2, corner_pos = self.get_corner_data(points[i], points[i + 1], points[i + 2], self.r)
            alpha = (alpha2 - alpha1 + math.pi) % (2 * math.pi) - math.pi  # turn angle (between -pi and pi) in radians
            # distance between points[i + 1] and beginning of the straight
            cut_dist = self.r * math.tan(abs(alpha) / 2) - self.corner_safety_overlap
            straight_length = v1.length() - last_cut_dist - cut_dist
            if straight_length < 0:
                self.raise_error_on_cell("Straight segment cannot fit. Try decreasing the turn radius.",
                                         points[i] + v1 / 2)

            # Straight segment before corner
            if straight_length > self.corner_safety_overlap:
                cell_straight = self.add_element(WaveguideCoplanarStraight, l=straight_length)
                start_point = points[i] + last_cut_dist / v1.length() * v1
                transf = pya.DCplxTrans(1, math.degrees(alpha1), False, start_point)
                self.insert_cell(cell_straight, transf)

            # Curved segment at the corner
            if 2 * cut_dist >= self.corner_safety_overlap:
                cell_curved = self.add_element(WaveguideCoplanarCurved, alpha=alpha)
                transf = pya.DCplxTrans(1, math.degrees(alpha1) + (90 if alpha < 0 else -90), False, corner_pos)
                self.insert_cell(cell_curved, transf)

            # Prepare for next iteration
            last_cut_dist = cut_dist

        # Check if straight can fit between the last two points
        v1 = points[-1] - points[-2]
        cut_dist = 0.0 if self.term2 == 0 else -self.corner_safety_overlap
        straight_length = v1.length() - last_cut_dist - cut_dist
        if straight_length < 0:
            self.raise_error_on_cell("Straight segment cannot fit. Try decreasing the turn radius.",
                                     points[-2] + v1 / 2)

        # Straight segment at the end
        if straight_length > self.corner_safety_overlap:
            subcell = self.add_element(WaveguideCoplanarStraight, l=straight_length)
            start_point = points[-2] + last_cut_dist / v1.length() * v1
            transf = pya.DCplxTrans(1, math.degrees(math.atan2(v1.y, v1.x)), False, start_point)
            self.insert_cell(subcell, transf)

        # Termination before the first segment
        WaveguideCoplanar.produce_end_termination(self, points[1], points[0], self.term1)
        self.add_port("a", points[0], points[0] - points[1])

        # Terminate the end
        WaveguideCoplanar.produce_end_termination(self, points[-2], points[-1], self.term2)
        self.add_port("b", points[-1], points[-1] - points[-2])

    def build(self):
        self.produce_waveguide()

    @staticmethod
    def get_corner_data(point1, point2, point3, r):
        """Returns data needed to create a curved waveguide at path corner.

        Args:
            point1: point before corner
            point2: corner point
            point3: point after corner
            r: curve radius

        Returns:
            A tuple (``v1``, ``v2``, ``alpha1``, ``alpha2``, ``corner_pos``), where

            * ``v1``: the vector (`point2` - `point1`)
            * ``v2``: the vector (`point3` - `point2`)
            * ``alpha1``: angle between `v1` and positive x-axis
            * ``alpha2``: angle between `v2` and positive x-axis
            * ``corner_pos``: position where the curved waveguide should be placed

        """
        v1 = point2 - point1
        v2 = point3 - point2
        alpha1 = math.atan2(v1.y, v1.x)
        alpha2 = math.atan2(v2.y, v2.x)
        alpha = (alpha2 - alpha1 + math.pi) % (2 * math.pi) - math.pi  # turn angle (between -pi and pi) in radians
        alphacorner = alpha1 + (alpha + math.pi) / 2  # corner middle angle plus 90 degrees
        distcorner = (r if alpha > 0 else -r) / math.cos(alpha / 2)
        corner_pos = point2 + pya.DVector(math.cos(alphacorner)*distcorner, math.sin(alphacorner)*distcorner)
        return v1, v2, alpha1, alpha2, corner_pos

    @staticmethod
    def produce_end_termination(elem, point_1, point_2, term_len, face_index=0):
        """Produces termination for a waveguide.

        The termination consists of a rectangular polygon in the metal gap layer, and grid avoidance around it.
        One edge of the polygon is centered at point_2, and the polygon extends to length "term_len" in the
        direction of (point_2 - point_1).

        Args:
            elem: Element from which the waveguide parameters for the termination are taken
            point_1: DPoint before point_2, used only to determine the direction
            point_2: DPoint after which termination is produced
            term_len (double): termination length, assumed positive
            face_index (int): face index of the face in elem where the termination is created
        """
        a = elem.a
        b = elem.b

        v = (point_2 - point_1)*(1/point_1.distance(point_2))
        u = pya.DTrans.R270.trans(v)
        shift_start = pya.DTrans(pya.DVector(point_2))

        if term_len > 0:
            poly = pya.DPolygon([pya.DPoint(u*(a/2 + b)),
                                 pya.DPoint(u*(a/2 + b) + v*term_len),
                                 pya.DPoint(u*(-a/2 - b) + v*term_len),
                                 pya.DPoint(u*(-a/2 - b))])
            elem.cell.shapes(elem.layout.layer(elem.face(face_index)["base_metal_gap_wo_grid"])).insert(
                poly.transform(shift_start))

        # protection
        term_len += elem.margin
        poly2 = pya.DPolygon([pya.DPoint(u*(a/2 + b + elem.margin)),
                              pya.DPoint(u*(a/2 + b + elem.margin) + v*term_len),
                              pya.DPoint(u*(-a/2 - b - elem.margin) + v*term_len),
                              pya.DPoint(u*(-a/2 - b - elem.margin))])
        elem.add_protection(poly2.transform(shift_start), face_index)

    @staticmethod
    def is_continuous(waveguide_cell, annotation_layer, tolerance):
        """Returns true if the given waveguide is determined to be continuous, false otherwise.

        The waveguide is considered continuous if the endpoints of its every segment (except first and last) are close
        enough to the endpoints of neighboring segments. The waveguide segments are not necessarily ordered correctly
        when iterating through the cells using begin_shapes_rec. This means we must compare the endpoints of each
        waveguide segment to the endpoints of all other waveguide segments.

        Args:
            waveguide_cell: Cell of the waveguide.
            annotation_layer: unsigned int representing the annotation layer
            tolerance: maximum allowed distance between connected waveguide segments

        """
        is_continuous = True

        # find the two endpoints for every waveguide segment

        endpoints = []  # endpoints of waveguide segment i are contained in endpoints[i][0] and endpoints[i][1]
        shapes_iter = waveguide_cell.begin_shapes_rec(annotation_layer)

        while not shapes_iter.at_end():
            shape = shapes_iter.shape()
            if shape.is_path():
                dtrans = shapes_iter.dtrans()  # transformation from shape coordinates to waveguide_cell coordinates
                pts = shape.each_dpoint()
                first_point = dtrans * next(pts, None)
                last_point = first_point.dup()
                for pt in pts:
                    last_point = pt
                last_point = dtrans * last_point
                endpoints.append([first_point, last_point])
            shapes_iter.next()

        # for every waveguide segment endpoint, try to find another endpoint which is close to it

        num_segments = len(endpoints)
        num_non_connected_points = 0

        for i in range(num_segments):

            def find_connected_point(point):
                """Tries to find a waveguide segment endpoint close enough to the given point."""

                found_connected_point = False

                for j in range(num_segments):
                    # pylint: disable=cell-var-from-loop
                    if i != j and (point.distance(endpoints[j][1]) < tolerance
                                   or point.distance(endpoints[j][0]) < tolerance):
                        # print("{} | {} | {}".format(point, endpoints[j][1], endpoints[j][0]))
                        found_connected_point = True
                        break

                if not found_connected_point:
                    nonlocal num_non_connected_points
                    num_non_connected_points += 1

            if endpoints[i][0].distance(endpoints[i][1]) != 0:  # we ignore any zero-length segments

                find_connected_point(endpoints[i][0])
                find_connected_point(endpoints[i][1])

            # we can have up to 2 non-connected points, because ends of the waveguide don't have to be connected
            if num_non_connected_points > 2:
                is_continuous = False
                break

        return is_continuous
