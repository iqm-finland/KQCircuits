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
            "description": "Termination length start (um)",
            "default": 0
        },
        "term2": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Termination length end (um)",
            "default": 0
        },
    }

    def __init__(self):
        super().__init__()

    def can_create_from_shape_impl(self):
        return self.shape.is_path()

    def parameters_from_shape_impl(self):
        points = [pya.DPoint(point * self.layout.dbu) for point in self.shape.each_point()]
        self.path = pya.DPath(points, 1)

    def transformation_from_shape_impl(self):
        return pya.Trans()

    def produce_end_termination(self, i_point_1, i_point_2, term_len):
        # Termination is after point2. Point1 determines the direction.
        # Negative term_len does not make any sense.
        points = [point for point in self.path.each_point()]
        a = self.a

        b = self.b

        v = (points[i_point_2] - points[i_point_1]) * (1 / points[i_point_1].distance(points[i_point_2]))
        u = pya.DTrans.R270.trans(v)
        shift_start = pya.DTrans(pya.DVector(points[i_point_2]))

        if term_len > 0:
            poly = pya.DPolygon([u * (a / 2 + b), u * (a / 2 + b) + v * (term_len), u * (-a / 2 - b) + v * (term_len),
                                 u * (-a / 2 - b)])
            self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(poly.transform(shift_start))

        # protection
        term_len += self.margin
        poly2 = pya.DPolygon([u * (a / 2 + b + self.margin), u * (a / 2 + b + self.margin) + v * (term_len),
                              u * (-a / 2 - b - self.margin) + v * (term_len), u * (-a / 2 - b - self.margin)])
        self.cell.shapes(self.layout.layer(self.face()["ground grid avoidance"])).insert(poly2.transform(shift_start))

    def produce_waveguide(self):
        points = [point for point in self.path.each_point()]

        # Termination before the first segment
        self.produce_end_termination(1, 0, self.term1)

        # For each segment except the last
        segment_last = points[0]
        self.l_temp = 0
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
            # self.cell.shapes(self.layout.layer(self.la)).insert(pya.DText("%f, %f, %f" % (alpha2-alpha1,distcorner,v1.vprod_sign(v2)),corner.x,corner.y))

            # Straight segment before the corner
            segment_start = segment_last
            segment_end = points[i + 1]
            cut = v1.vprod_sign(v2) * self.r / math.tan((math.pi - (alpha2 - alpha1)) / 2)
            l = segment_start.distance(segment_end) - cut
            angle = 180 / math.pi * math.atan2(segment_end.y - segment_start.y, segment_end.x - segment_start.x)
            subcell = WaveguideCoplanarStraight.create_cell(self.layout, {
                "a": self.a,
                "b": self.b,
                "l": l,  # TODO: Finish the list
                # "margin" : self.margin
            })

            self.l_temp += subcell.pcell_parameters_by_name()["l"]
            transf = pya.DCplxTrans(1, angle, False, pya.DVector(segment_start))
            self.insert_cell(subcell, transf)
            segment_last = points[i + 1] + v2 * (1 / v2.abs()) * cut

            # Curve at the corner
            subcell = WaveguideCoplanarCurved.create_cell(self.layout, {
                "a": self.a,
                "b": self.b,
                "alpha": alpha2 - alpha1,  # TODO: Finish the list,
                "n": self.n,
                "r": self.r
            })
            transf = pya.DCplxTrans(1, alpha1 / math.pi * 180.0 - v1.vprod_sign(v2) * 90, False, corner)

            self.insert_cell(subcell, transf)

        # Last segment
        segment_start = segment_last
        segment_end = points[-1]
        l = segment_start.distance(segment_end)
        angle = 180 / math.pi * math.atan2(segment_end.y - segment_start.y, segment_end.x - segment_start.x)

        # Terminate the end
        self.produce_end_termination(-2, -1, self.term2)

        subcell = WaveguideCoplanarStraight.create_cell(self.layout, {
            "a": self.a,
            "b": self.b,
            "l": l  # TODO: Finish the list
        })
        transf = pya.DCplxTrans(1, angle, False, pya.DVector(segment_start))
        self.insert_cell(subcell, transf)

    def produce_impl(self):
        self.produce_waveguide()

    @staticmethod
    def get_length(cell, annotation_layer):
        """
        Returns the length of a waveguide.

        Args:
            cell: A Cell of the waveguide.
            annotation_layer: An unsigned int representing the annotation_layer.

        """
        shapes_iter = cell.begin_shapes_rec(annotation_layer)
        length = 0
        while not shapes_iter.at_end():
            shape = shapes_iter.shape()
            if shape.is_path():
                length += shape.path_dlength()
            shapes_iter.next()
        return length

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
