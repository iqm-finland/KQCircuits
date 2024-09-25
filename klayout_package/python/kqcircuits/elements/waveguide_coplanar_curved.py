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


from math import pi, sin, cos, ceil

from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import vector_length_and_direction, round_dpath_width
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.elements.waveguide_coplanar_straight import WaveguideCoplanarStraight


def arc(r, start, stop, n, mode=1):
    """Returns list of points of an arc

    Args:
        r: radius
        start: begin angle in radians
        stop: end angle in radians
        n: number of corners in full circle
        mode: discretization method, 0=shortcut, 1=match length, other=detour

    .. MARKERS_FOR_PNG 0,91 0,100
    """
    match mode:
        case 0:  # shortcut method, where points are on the arc
            end_ratio = 1.0
            r_scale = lambda _: 1.0
        case 1:  # matching length method, where combined length of segments equals the analytical length of the arc
            end_ratio = 0.7339449  # based on trigonometric calculations and a few degree Taylor series approximation
            r_scale = lambda x: 1 + x**2 / 24 + x**4 * 7 / 5760  # approximation for x/2 / sin(x/2) that accepts x=0
        case _:  # detour method, where segments are tangents on the arc
            end_ratio = 0.5
            r_scale = lambda x: 1.0 / cos(x / 2)

    c_steps = 2 * end_ratio - 1  # nominal constant steps at start and end
    n_steps = max(round(abs(stop - start) * n / (2 * pi) - c_steps), ceil(1 - c_steps))
    step = (stop - start) / (n_steps + c_steps)
    r_corner = r * r_scale(step)

    pts = [pya.DPoint(r * cos(start), r * sin(start))]
    for i in range(n_steps):
        alpha = start + step * (i + end_ratio)
        pts.append(pya.DPoint(r_corner * cos(alpha), r_corner * sin(alpha)))
    pts.append(pya.DPoint(r * cos(stop), r * sin(stop)))
    return pts


@add_parameters_from(WaveguideCoplanarStraight, "add_metal", "ground_grid_in_trace")
class WaveguideCoplanarCurved(Element):
    """The PCell declaration of a curved segment of a coplanar waveguide.

    Coordinate origin is left at the center of the arc.
    """

    alpha = Param(pdt.TypeDouble, "Curve angle (rad)", pi)
    length = Param(pdt.TypeDouble, "Actual length", 0, unit="μm", readonly=True)

    def coerce_parameters_impl(self):
        # Update length
        self.length = self.r * abs(self.alpha)

    @staticmethod
    def build_geometry(element, trans, alpha):
        (
            left_inner_arc,
            left_outer_arc,
            right_inner_arc,
            right_outer_arc,
            left_protection_arc,
            right_protection_arc,
            annotation_arc,
        ) = WaveguideCoplanarCurved.create_curve_arcs(element, alpha)

        # Left gap
        pts = left_inner_arc + left_outer_arc
        shape_1 = pya.DPolygon(pts)
        element.cell.shapes(element.get_layer("base_metal_gap_wo_grid")).insert(trans * shape_1)
        # Right gap
        pts = right_inner_arc + right_outer_arc
        shape_2 = pya.DPolygon(pts)
        element.cell.shapes(element.get_layer("base_metal_gap_wo_grid")).insert(trans * shape_2)

        pts = annotation_arc
        shape = round_dpath_width(pya.DPath(pts, element.a), element.layout.dbu)
        element.cell.shapes(element.get_layer("waveguide_path")).insert(trans * shape)
        if element.add_metal:
            shape = pya.DPolygon(left_inner_arc + list(reversed(right_inner_arc)))
            element.cell.shapes(element.get_layer("base_metal_addition")).insert(trans * shape)

        # Protection layer
        if element.ground_grid_in_trace:
            element.add_protection(trans * shape_1.sized(1))
            element.add_protection(trans * shape_2.sized(1))
        else:
            # Protection layer
            pts = left_protection_arc + right_protection_arc
            element.add_protection(trans * pya.DPolygon(pts))

    def build(self):
        WaveguideCoplanarCurved.build_geometry(self, pya.DTrans(), self.alpha)

    @staticmethod
    def create_curve_arcs(elem, angle):
        """Creates arcs of points for a curved waveguide.

        Args:
            elem: Element from which the waveguide parameters for the arc are taken
            angle (double): angle of the curved waveguide

        Returns:
            A tuple consisting of lists of points, each list representing one of the arcs. (left_gap_inner,
            left_gap_outer, right_gap_inner, right_gap_outer, left_protection, right_protection, annotation)
        """
        alphastart = 0
        alphastop = angle
        left_gap_inner = arc(elem.r - elem.a / 2, alphastart, alphastop, elem.n)
        left_gap_outer = arc(elem.r - elem.a / 2 - elem.b, alphastop, alphastart, elem.n)
        right_gap_inner = arc(elem.r + elem.a / 2, alphastart, alphastop, elem.n)
        right_gap_outer = arc(elem.r + elem.a / 2 + elem.b, alphastop, alphastart, elem.n)
        left_protection = arc(elem.r - elem.a / 2 - elem.b - elem.margin, alphastart, alphastop, elem.n)
        right_protection = arc(elem.r + elem.a / 2 + elem.b + elem.margin, alphastop, alphastart, elem.n)
        annotation = arc(elem.r, alphastart, alphastop, elem.n)
        return (
            left_gap_inner,
            left_gap_outer,
            right_gap_inner,
            right_gap_outer,
            left_protection,
            right_protection,
            annotation,
        )

    @staticmethod
    def produce_curve_termination(elem, angle, term_len, trans, face_index=0):
        """Produces termination for a curved waveguide.

        The termination consists of a rectangular polygon in the metal gap layer, and grid avoidance around it.
        The termination is placed at the position where a curved waveguide with alpha=angle and trans=trans would end.

        Args:
            elem: Element from which the waveguide parameters for the termination are taken
            angle (double): angle of the curved waveguide
            term_len (double): termination length, assumed positive
            trans (DTrans): transformation applied to the termination
            face_index (int): face index of the face in elem where the termination is created
        """
        (
            left_inner_arc,
            left_outer_arc,
            right_inner_arc,
            right_outer_arc,
            left_protection_arc,
            right_protection_arc,
            _,
        ) = WaveguideCoplanarCurved.create_curve_arcs(elem, angle)

        # direction of the termination box
        _, term_dir = vector_length_and_direction(left_outer_arc[0] - left_outer_arc[1])

        if term_len > 0:
            # metal gap for termination
            pts = [
                left_inner_arc[-1],
                left_outer_arc[0],
                left_outer_arc[0] + term_len * term_dir,
                right_outer_arc[0] + term_len * term_dir,
                right_outer_arc[0],
                right_inner_arc[-1],
            ]
            shape = pya.DPolygon(pts)
            elem.cell.shapes(elem.layout.layer(elem.face(face_index)["base_metal_gap_wo_grid"])).insert(trans * shape)

        # grid avoidance for termination
        protection_pts = [
            left_protection_arc[-1],
            left_protection_arc[-1] + (term_len + elem.margin) * term_dir,
            right_protection_arc[0] + (term_len + elem.margin) * term_dir,
            right_protection_arc[0],
        ]
        elem.add_protection(trans * pya.DPolygon(protection_pts), face_index)
