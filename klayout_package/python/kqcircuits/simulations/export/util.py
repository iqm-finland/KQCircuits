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


import math
from sys import float_info
from typing import List
from kqcircuits.pya_resolver import pya


def _dist(edge: pya.Edge, point: pya.Point):
    """
    If point projected to line by edge is in edge then use `distance_abs`
    but otherwise take the minimum distance to end points
    """
    v_edge = pya.Vector(edge.p2 - edge.p1)
    if v_edge.sprod(v_edge) > 0:
        v_point_start = pya.Vector(point - edge.p1)
        v_point_end = pya.Vector(point - edge.p2)

        v_point_start_projection = v_edge.sprod(v_point_start) / math.sqrt(v_edge.sprod(v_edge))
        v_point_end_projection = v_edge.sprod(v_point_end) / math.sqrt(v_edge.sprod(v_edge))

        if edge.length() >= abs(v_point_start_projection + v_point_end_projection):
            out = edge.distance_abs(point)
        else:
            out = min(point.distance(edge.p1), point.distance(edge.p2))
    else:
        out = min(point.distance(edge.p1), point.distance(edge.p2))
    return out


def find_edge_from_point_in_polygons(polygons: List[pya.Polygon], point: pya.DPoint, dbu, tolerance=0.01):
    """
    Finds the edge closest to a point, and returns the edge as well as it's polygon and edge index
    """

    # Find closest edge to point
    edges = [
        (i, j, edge.to_dtype(dbu))
        for (i, polygon) in enumerate(polygons)
        for (j, edge) in enumerate(polygon.each_edge())
    ]
    (distance, i, j, nearest_edge) = sorted([(_dist(edge, point), i, j, edge) for (i, j, edge) in edges])[0]
    if distance < tolerance:
        return i, j, nearest_edge
    else:
        raise ValueError(f"No edge found at {point=}, {nearest_edge=}, {distance=}")


def get_enclosing_polygon(points: List[List[float]]):
    """
    Order points in such a way that they form a polygon without intersecting
    lines. The ordering is clockwise starting from the left-most point.

    Arguments:
        points: List of points [x,y]

    Returns:
        ordered list of points [x,y]

    Notes:
        Points on the line joining the extreme vertices are kept on one
        boundary chain, so collinear endpoints cannot cause backtracking.
    """

    points.sort()
    pleft, pright = points[0], points[-1]
    dx, dy = pright[0] - pleft[0], pright[1] - pleft[1]
    coordinate_scale = max(max(abs(point[0]), abs(point[1])) for point in points)
    pabove, pbelow, boundary = [], [], []
    for point in points[1:-1]:
        vx, vy = point[0] - pleft[0], point[1] - pleft[1]
        cross1, cross2 = dx * vy, dy * vx
        cross = cross1 - cross2
        # Include coordinate representation error, especially far from the
        # origin, as well as roundoff in the cross-product calculation.
        tolerance = (
            8
            * float_info.epsilon
            * (abs(cross1) + abs(cross2) + coordinate_scale * (abs(dx) + abs(dy) + abs(vx) + abs(vy)))
        )
        if abs(cross) <= tolerance:
            boundary.append(point)
        elif cross > 0:
            pabove.append(point)
        else:
            pbelow.append(point)

    if boundary:
        if pabove:
            pbelow = sorted(pbelow + boundary)
        else:
            # Without an upper chain, its straight edge would overlap any
            # collinear vertices placed on the lower chain.
            pabove = boundary
    return [pleft] + pabove + [pright] + pbelow[::-1]
