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

from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import vector_length_and_direction
from kqcircuits.util.parameters import Param, pdt


def up_mod(a, per):
    # Finds remainder in the same direction as periodicity
    if a * per > 0:
        return a % per
    else:
        return a - per * math.floor(a / per)


def arc(r, start, stop, n):
    pts = []
    last = start

    alpha_rel = up_mod(stop - start, math.pi * 2)  # from 0 to 2 pi
    alpha_step = 2 * math.pi / n * (
        -1 if alpha_rel > math.pi else 1)
    # shorter dir
    # n_steps = math.floor((2*math.pi-alpha_rel)/abs(alpha_step) if alpha_rel > math.pi else alpha_rel/abs(alpha_step))
    n_steps = math.floor(
        (2 * math.pi - alpha_rel) / abs(alpha_step) if alpha_rel > math.pi else alpha_rel / abs(alpha_step))

    alpha = start

    for _ in range(0, n_steps + 1):
        pts.append(pya.DPoint(r * math.cos(alpha), r * math.sin(alpha)))
        alpha += alpha_step
        last = alpha

    if last != stop:
        alpha = stop
        pts.append(pya.DPoint(r * math.cos(alpha), r * math.sin(alpha)))

    return pts


class WaveguideCoplanarCurved(Element):
    """The PCell declaration of a curved segment of a coplanar waveguide.

    Coordinate origin is left at the center of the arc.
    """

    alpha = Param(pdt.TypeDouble, "Curve angle (rad)", math.pi)
    length = Param(pdt.TypeDouble, "Actual length", 0, unit="μm", readonly=True)

    def coerce_parameters_impl(self):
        # Update length
        self.length = self.r * abs(self.alpha)

    def produce_impl(self):

        left_inner_arc, left_outer_arc, right_inner_arc, right_outer_arc, left_protection_arc, right_protection_arc, \
            annotation_arc = WaveguideCoplanarCurved.create_curve_arcs(self, self.alpha)

        # Left gap
        pts = left_inner_arc + left_outer_arc
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)
        # Right gap
        pts = right_inner_arc + right_outer_arc
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)
        # Protection layer
        pts = left_protection_arc + right_protection_arc
        shape = pya.DPolygon(pts)
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(shape)
        # Annotation
        pts = annotation_arc
        shape = pya.DPath(pts, self.a + 2 * self.b)
        self.cell.shapes(self.get_layer("waveguide_length")).insert(shape)

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
        left_gap_inner = arc(elem.r - elem.a/2, alphastart, alphastop, elem.n)
        left_gap_outer = arc(elem.r - elem.a/2 - elem.b, alphastop, alphastart, elem.n)
        right_gap_inner = arc(elem.r + elem.a/2, alphastart, alphastop, elem.n)
        right_gap_outer = arc(elem.r + elem.a/2 + elem.b, alphastop, alphastart, elem.n)
        left_protection = arc(elem.r - elem.a/2 - elem.b - elem.margin, alphastart, alphastop, elem.n)
        right_protection = arc(elem.r + elem.a/2 + elem.b + elem.margin, alphastop, alphastart, elem.n)
        annotation = arc(elem.r, alphastart, alphastop, elem.n)
        return left_gap_inner, left_gap_outer, right_gap_inner, right_gap_outer, left_protection, right_protection,\
            annotation

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
        left_inner_arc, left_outer_arc, right_inner_arc, right_outer_arc, left_protection_arc, right_protection_arc,\
            _ = WaveguideCoplanarCurved.create_curve_arcs(elem, angle)

        # direction of the termination box
        _, term_dir = vector_length_and_direction(left_outer_arc[0] - left_outer_arc[1])

        if term_len > 0:
            # metal gap for termination
            pts = [
                left_inner_arc[-1],
                left_outer_arc[0],
                left_outer_arc[0] + term_len*term_dir,
                right_outer_arc[0] + term_len*term_dir,
                right_outer_arc[0],
                right_inner_arc[-1],
            ]
            shape = pya.DPolygon(pts)
            elem.cell.shapes(elem.layout.layer(elem.face(face_index)["base_metal_gap_wo_grid"])).insert(trans*shape)

        # grid avoidance for termination
        protection_pts = [
            left_protection_arc[-1],
            left_protection_arc[-1] + (term_len + elem.margin)*term_dir,
            right_protection_arc[0] + (term_len + elem.margin)*term_dir,
            right_protection_arc[0],
        ]
        protection_shape = pya.DPolygon(protection_pts)
        elem.cell.shapes(elem.get_layer("ground_grid_avoidance", face_index)).insert(trans*protection_shape)
