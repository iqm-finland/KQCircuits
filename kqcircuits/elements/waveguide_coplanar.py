# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import math

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar_straight import WaveguideCoplanarStraight
from kqcircuits.elements.waveguide_coplanar_curved import WaveguideCoplanarCurved

from kqcircuits.util.geometry_helper import get_cell_path_length

class WaveguideCoplanar(Element):
    """The PCell declaration for an arbitrary coplanar waveguide.

    Coplanar waveguide defined by the width of the center conductor and gap. It can follow any segmented lines with
    predefined bending radios. It actually consists of straight and bent PCells. Warning: Arbitrary angle bents
    actually have very small gaps between bends and straight segments due to precision of arithmetic. To be fixed in a
    future release.
    """

    PARAMETERS_SCHEMA = {
        "path": {
            "type": pya.PCellParameterDeclaration.TypeShape,
            "description": "TLine",
            "default": pya.DPath([pya.DPoint(0, 0), pya.DPoint(100, 0)], 0)
        },
        "term1": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Termination length start [μm]",
            "default": 0
        },
        "term2": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Termination length end [μm]",
            "default": 0
        },
        "corner_safety_overlap": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Extend straight sections near corners [μm]",
            "docstring": "Extend straight sections near corners by this amount [μm] to ensure all sections overlap",
            "default": 0.001
        },
    }

    def can_create_from_shape_impl(self):
        return self.shape.is_path()

    def parameters_from_shape_impl(self):
        points = [pya.DPoint(point * self.layout.dbu) for point in self.shape.each_point()]
        self.path = pya.DPath(points, 1)

    def transformation_from_shape_impl(self):
        return pya.Trans()

    def produce_waveguide(self):
        points = [point for point in self.path.each_point()]

        # Termination before the first segment
        WaveguideCoplanar.produce_end_termination(self, points[1], points[0], self.term1)
        self.add_port("a", points[0], points[0]-points[1])

        # For each segment except the last
        if self.term1 > 0 and len(points) > 1:
            # Extend segment_last negatively
            v2 = points[1] - points[0]
            segment_last = (points[0] - self.corner_safety_overlap*v2/v2.length()).to_p()
        else:
            segment_last = points[0]

        for i in range(0, len(points) - 2):
            # Corner coordinates
            v1 = points[i + 1] - points[i]
            v2 = points[i + 2] - points[i + 1]
            crossing = points[i + 1]
            alpha1 = math.atan2(v1.y, v1.x)
            alpha2 = math.atan2(v2.y, v2.x)
            alphacorner = (((math.pi - (alpha2 - alpha1)) / 2) + alpha2)
            distcorner = v1.vprod_sign(v2) * self.r / math.sin((math.pi - (alpha2 - alpha1)) / 2)
            corner = crossing + pya.DVector(math.cos(alphacorner) * distcorner, math.sin(alphacorner) * distcorner)

            # Straight segment before the corner
            segment_start = segment_last
            segment_end = points[i + 1]
            cut = v1.vprod_sign(v2) * self.r / math.tan((math.pi - (alpha2 - alpha1)) / 2)
            l = segment_start.distance(segment_end) - cut + self.corner_safety_overlap
            angle = 180 / math.pi * math.atan2(segment_end.y - segment_start.y, segment_end.x - segment_start.x)
            subcell = self.add_element(WaveguideCoplanarStraight, Element.PARAMETERS_SCHEMA, l=l)

            transf = pya.DCplxTrans(1, angle, False, pya.DVector(segment_start))
            self.insert_cell(subcell, transf)
            segment_last = (points[i + 1] + v2 * (1 / v2.abs()) * cut - self.corner_safety_overlap*v2/v2.length()).to_p()

            # Curve at the corner
            alpha = alpha2 - alpha1
            min_angle = 1e-5  # close to the smallest angle that can create a valid curved waveguide
            if abs(alpha) >= min_angle:
                subcell = self.add_element(WaveguideCoplanarCurved, Element.PARAMETERS_SCHEMA, alpha=alpha, n=self.n)
                transf = pya.DCplxTrans(1, alpha1 / math.pi * 180.0 - v1.vprod_sign(v2) * 90, False, corner)

            self.insert_cell(subcell, transf)

        # Last segment
        segment_start = segment_last
        segment_end = points[-1]
        l = segment_start.distance(segment_end)
        if self.term2 > 0:
            l += self.corner_safety_overlap
        angle = 180 / math.pi * math.atan2(segment_end.y - segment_start.y, segment_end.x - segment_start.x)

        # Terminate the end
        WaveguideCoplanar.produce_end_termination(self, points[-2], points[-1], self.term2)
        self.add_port("b", points[-1], points[-1]-points[-2])

        subcell = self.add_element(WaveguideCoplanarStraight, Element.PARAMETERS_SCHEMA, l=l)
        transf = pya.DCplxTrans(1, angle, False, pya.DVector(segment_start))
        self.insert_cell(subcell, transf)

    def produce_impl(self):
        self.produce_waveguide()

    get_length = get_cell_path_length

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
            poly = pya.DPolygon([u*(a/2 + b), u*(a/2 + b) + v*term_len, u*(-a/2 - b) + v*term_len,
                                 u*(-a/2 - b)])
            elem.cell.shapes(elem.layout.layer(elem.face(face_index)["base metal gap wo grid"])).insert(
                poly.transform(shift_start))

        # protection
        term_len += elem.margin
        poly2 = pya.DPolygon([u*(a/2 + b + elem.margin), u*(a/2 + b + elem.margin) + v*term_len,
                              u*(-a/2 - b - elem.margin) + v*term_len, u*(-a/2 - b - elem.margin)])
        elem.cell.shapes(elem.layout.layer(elem.face(face_index)["ground grid avoidance"])).insert(
            poly2.transform(shift_start))

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
