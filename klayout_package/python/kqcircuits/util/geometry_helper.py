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


"""Helper module for general geometric functions"""

from math import cos, sin, radians, atan2, degrees, pi, ceil
from typing import List
import numpy as np
from scipy import spatial
from kqcircuits.defaults import default_layers, default_path_length_layers
from kqcircuits.pya_resolver import pya


def vector_length_and_direction(vector):
    """Returns the direction and length of the pya.DVector "vector"."""
    length = vector.length()
    direction = vector / length
    return length, direction


def point_shift_along_vector(start, other, distance=None):
    """Returns a point at a `distance` away from point `start` in the direction of point `other`."""
    v = other - start
    if distance is not None:
        return start + v / v.length() * distance
    else:
        return start + v


def get_direction(angle):
    """
    Returns the direction vector corresponding to `angle`.

    Args:
        angle: angle in degrees

    Returns: Unit vector in direction angle
    """
    return pya.DVector(cos(radians(angle)), sin(radians(angle)))


def get_angle(vector):
    """
    Returns the angle in degrees for a given DVector (or DPoint)

    Args:
        vector: input vector

    Returns: angle in degrees
    """
    return degrees(atan2(vector.y, vector.x))


def get_cell_path_length(cell, layer=None):
    """Returns the length of the paths in the cell.

    Adding together the cell's paths' lengths in the "1t1_waveguide_path", "2b1_waveguide_path" and
    "waveguide_length" layers.

    Args:
        cell: A cell object.
        layer: None or an unsigned int to specify a non-standard layer
    """

    if layer is not None:
        return _get_length_per_layer(cell, layer)

    length = 0
    for path_layer in default_path_length_layers:
        length += _get_length_per_layer(cell, path_layer)

    return length


def _get_length_per_layer(cell, layer):
    """Get length of the paths in the cell in the specified layer."""

    length = 0
    layer = cell.layout().layer(default_layers[layer]) if isinstance(layer, str) else layer

    for inst in cell.each_inst():  # over child cell instances, not instances of itself
        shapes_iter = inst.cell.begin_shapes_rec(layer)
        while not shapes_iter.at_end():
            shape = shapes_iter.shape()
            if shape.is_path():
                length += shape.path_dlength()
            shapes_iter.next()

    # in case of waveguide, there are no shapes in the waveguide cell itself
    # but the following allows function reuse in other applications
    for shape in cell.shapes(layer).each():
        if shape.is_path():
            length += shape.path_dlength()

    return length


def get_object_path_length(obj, layer=None):
    """Returns sum of lengths of all the paths in the object and its children

    Arguments:
        obj: ObjectInstPath object
        layer: layer integer id in the database, waveguide layer by default
    """

    if obj.is_cell_inst():
        # workaround for getting the cell due to KLayout bug, see
        # https://www.klayout.de/forum/discussion/1191/cell-shapes-cannot-call-non-const-method-on-a-const-reference
        # TODO: replace by `cell = obj.inst().cell` once KLayout bug is fixed
        cell = obj.layout().cell(obj.inst().cell_index)
        return get_cell_path_length(cell, layer)
    else:  # is a shape
        # TODO ignore paths on wrong layers
        shape = obj.shape
        if shape.is_path():
            return shape.path_dlength()
    return 0


def simple_region(region):
    return pya.Region([poly.to_simple_polygon() for poly in region.each()])


def region_with_merged_points(region, tolerance):
    """ In each polygon of the region, removes points that are closer to other points than a given tolerance.

    Arguments:
        region: Input region
        tolerance: Minimum distance, in database units, between two adjacent points in the resulting region

    Returns:
        region: with merged points
    """
    def find_next(curr, step, data):
        """ Returns the next index starting from 'i' to direction 'step' for which 'data' has positive value """
        num = len(data)
        j = curr + step
        while data[j % num] <= 0.0:
            j += step
        return j

    def merged_points(points):
        """ Removes points that are closer another points than a given tolerance. Returns list of points."""
        # find squared length of each segment of polygon
        num = len(points)
        squares = [0.0] * num
        for i in range(0, num):
            squares[i] = points[i].sq_distance(points[(i + 1) % num])

        # merge short segments
        curr_id = 0
        squared_tolerance = tolerance ** 2
        while curr_id < num:
            if squares[curr_id % num] >= squared_tolerance:
                # segment long enough: increase 'curr' for the next iteration
                curr_id = find_next(curr_id, 1, squares)
                continue

            # segment too short: merge segment with the shorter neighbor segment (prev or next)
            prev_id = find_next(curr_id, -1, squares)
            next_id = find_next(curr_id, 1, squares)
            if squares[prev_id % num] < squares[next_id % num]:  # merge with the previous segment
                squares[curr_id % num] = 0.0
                curr_id = prev_id
            else:  # merge with the next segment
                squares[next_id % num] = 0.0
                next_id = find_next(next_id, 1, squares)
            squares[curr_id % num] = points[curr_id % num].sq_distance(points[next_id % num])

        return [point for square, point in zip(squares, points) if square > 0.0]

    # Quick exit if tolerance is not positive
    if tolerance <= 0.0:
        return region

    # Merge points of hulls and holes of each polygon
    new_region = pya.Region()
    for poly in region.each():
        new_poly = pya.Polygon(merged_points(list(poly.each_point_hull())))
        for hole_id in range(poly.holes()):
            new_poly.insert_hole(merged_points(list(poly.each_point_hole(hole_id))))
        new_region.insert(new_poly)
    return new_region


def region_with_merged_polygons(region, tolerance, expansion=0.0):
    """ Merges polygons in given region. Ignores gaps that are smaller than given tolerance.

    Arguments:
        region: input region
        tolerance: largest gap size to be ignored
        expansion: the amount by which the polygons are expanded (edges move outwards)

    Returns:
        region with merged polygons
    """
    new_region = region.sized(0.5 * tolerance)  # expand polygons to ignore gaps in merge
    new_region.merge()
    new_region.size(expansion - 0.5 * tolerance)  # shrink polygons back to original shape (+ optional expansion)
    new_region = new_region.smoothed(2)  # smooth out the slight jaggedness on the edges
    return new_region


def match_points_on_edges(cell, layout, layers):
    """ Goes through each polygon edge and splits the edge whenever it passes through a point of another polygon.

    This function can eliminate gaps and overlaps caused by transformation to simple_polygon.

    Arguments:
        cell: A cell object.
        layout: A layout object
        layers: List of layers to be considered and modified
    """
    # Gather points from layers to `all_points` dictionary. This ignores duplicate points.
    all_points = dict()
    for layer in layers:
        shapes = cell.shapes(layout.layer(layer))
        for shape in shapes:
            all_points.update({point: list() for point in shape.simple_polygon.each_point()})
    if not all_points:
        return  # nothing is done if no points exist

    # For each point, assign a list of surrounding points using Voronoi diagram
    point_list = list(all_points)
    vor = spatial.Voronoi([(p.x, p.y) for p in point_list])
    for link in vor.ridge_points:
        all_points[point_list[link[0]]].append(point_list[link[1]])
        all_points[point_list[link[1]]].append(point_list[link[0]])

    # Travel through polygon edges and split edge whenever it passes through a point
    for layer in layers:
        shapes = cell.shapes(layout.layer(layer))
        for shape in shapes:
            points = list(shape.simple_polygon.each_point())
            new_points = []
            for i, p1 in enumerate(points):
                p0 = points[i - 1]
                edge = pya.Edge(p0, p1)
                # Travel from p0 to p1 in Voronoi diagram
                while p0 != p1:
                    # List points that are on the edge towards p1
                    sq_dist = p0.sq_distance(p1)
                    p_on_edge = [p for p in all_points[p0] if edge.contains(p) and p.sq_distance(p1) < sq_dist]
                    if p_on_edge:
                        # Update p0 to be the point on edge towards p1 that is furthest from p1
                        p0 = max(p_on_edge, key=lambda x, y=p1: x.sq_distance(y))
                        new_points.append(p0)  # Add the point to the polygon. Finally, p0 is equal to p1 here.
                    else:
                        # Update p0 to be the neighbour closest to p1
                        p0 = min(all_points[p0], key=lambda x, y=p1: x.sq_distance(y))

            # Replace polygon if any points are added
            if len(new_points) != len(points):
                shapes.replace(shape, pya.SimplePolygon(new_points, True))


def is_clockwise(polygon_points):
    """Returns True if the polygon points are in clockwise order, False if they are counter-clockwise.

    Args:
        polygon_points: list of polygon points, must be either in clockwise or counterclockwise order
    """
    # see https://en.wikipedia.org/wiki/Curve_orientation#Orientation_of_a_simple_polygon
    bottom_left_point_idx = 0
    for idx, point in enumerate(polygon_points[1:]):
        if point.x < polygon_points[bottom_left_point_idx].x and point.y < polygon_points[bottom_left_point_idx].y:
            bottom_left_point_idx = idx
    a = polygon_points[bottom_left_point_idx - 1]
    b = polygon_points[bottom_left_point_idx]
    c = polygon_points[(bottom_left_point_idx + 1) % len(polygon_points)]
    det = (b.x - a.x)*(c.y - a.y) - (c.x - a.x)*(b.y - a.y)
    return det < 0


def circle_polygon(r, n=64, origin=pya.DPoint(0, 0)):
    """
    Returns a polygon for a full circle around the origin.

    Args:
        r: Radius
        origin: Center of the circle, default (0,0)
        n: Number of points.

    Returns: list of ``DPoint``s, length ``n``.
    """
    return pya.DPolygon([origin + pya.DPoint(cos(a / n * 2 * pi) * r, sin(a / n * 2 * pi) * r) for a in range(0, n)])


def arc_points(r, start=0, stop=2 * pi, n=64, origin=pya.DPoint(0, 0)):
    """
    Returns point describing an arc around the origin with specified start and stop angles. The start and stop angle
    are included.

    If start < stop, the points are counter-clockwise; if start > stop, the points are clockwise.

    Args:
        r: Arc radius
        start: Start angle in radians, default 0
        stop: Stop angle in radians, default 2*pi
        origin: Center of the arc, default (0,0)
        n: Number of steps corresponding to a full circle.

    """
    n_steps = max(ceil(n * abs(stop - start) / (2 * pi)), 2)
    step = (stop - start) / (n_steps - 1)
    return [origin + pya.DPoint(cos(start + a * step) * r, sin(start + a * step) * r) for a in range(0, n_steps)]


def _cubic_polynomial(control_points: List[pya.DPoint],
                      spline_matrix: np.array,
                      sample_points: int = 100,
                      endpoint: bool = False) -> List[pya.DPoint]:
    """Returns a list of DPoints sampled uniformly from a third order polynomial spline

    Args:
        control_points: list of exactly four control points
        spline_matrix: matrix of coefficients of the polynomial function
        sample_points: number of points to sample for the curve
        endpoint: if True, will distribute sample points to sample at t = 1.0
    """
    if len(control_points) != 4:
        raise ValueError("There should be exactly four control points for cubic polynomial")
    if spline_matrix.shape != (4, 4):
        raise ValueError("spline_matrix must be of shape (4, 4)")
    geometry_matrix = np.array([[p.x, p.y] for p in control_points]).T
    result_points = []
    for t in np.linspace(0.0, 1.0, sample_points, endpoint=endpoint):
        result_vector = geometry_matrix.dot(spline_matrix).dot(np.array([1, t, t*t, t*t*t]).T)
        result_points.append(pya.DPoint(result_vector[0], result_vector[1]))
    return result_points


def bspline_points(control_points: List[pya.DPoint],
                   sample_points: int = 100,
                   startpoint: bool = False,
                   endpoint: bool = False) -> List[pya.DPoint]:
    """Samples points uniformly from the B-Spline constructed from a sequence of control points.
    The spline is derived from a sequence of cubic splines for each subsequence of four-control points
    in a sliding window.

    Unlike Bezier curves, for each spline in B-Spline it is not guaranteed
    that the first and last control point will be in the spline.

    B-Spline cubic polynomial implemented based on the following reference:
    Kaihuai Qin, "General matrix representations for B-splines", Proceedings Pacific Graphics '98
    Sixth Pacific Conference on Computer Graphics and Applications, Singapore, 1998, pp. 37-43,
    doi: 10.1109/PCCGA.1998.731996

    Args:
        control_points: a sequence of control points, must have at least 4 pya.DPoints elements
        sample_points: number of uniform samples of each cubic B-spline,
            total number of samples is: sample_points * (control_points - 3)
        startpoint: If True, will prepend duplicates of the first control point so that the
            first control point will be in the B-Spline
        endpoint: If True, will append duplicates of the last control point so that the
            last control point will be in the B-Spline

    Returns:
        List of pya.DPoints that can be used as part of a polygon
    """
    # B-Spline doesn't guarantee that the spline will go through the end points,
    # duplicate points on either end if needed
    if startpoint:
        control_points = [control_points[0], control_points[0]] + control_points
    if endpoint:
        control_points = control_points + [control_points[-1], control_points[-1]]
    if len(control_points) < 4:
        raise ValueError("B-Spline needs at least four control points")
    bspline_matrix = (1.0/6.0) * np.array([[ 1,-3, 3,-1],
                                           [ 4, 0,-6, 3],
                                           [ 1, 3, 3,-3],
                                           [ 0, 0, 0, 1]])
    result_points = []
    # Sliding window
    for window_start in range(len(control_points) - 3):
        result_points += _cubic_polynomial( control_points[window_start:window_start+4],
                                            bspline_matrix,
                                            sample_points,
                                            endpoint=(window_start == len(control_points) - 4))
    return result_points


def bezier_points(control_points: List[pya.DPoint], sample_points: int = 100) -> List[pya.DPoint]:
    """Samples points uniformly from the Bezier curve constructed from a sequence of control points.
    The curve is derived from a sequence of cubic splines for each subsequence of four-control points
    such that subsequence shares one control point with the previous subsequence.

    Special care needs to be taken to guarantee continuity in the tangent of the curve.
    The third and fourth control point of each subsequence as well as the second
    control point of the next subsequence have to be in the same line.

    Bezier cubic polynomial implemented based on the following reference:
    Kaihuai Qin, "General matrix representations for B-splines", Proceedings Pacific Graphics '98
    Sixth Pacific Conference on Computer Graphics and Applications, Singapore, 1998, pp. 37-43,
    doi: 10.1109/PCCGA.1998.731996

    Args:
        control_points: a sequence of control points, must be of length equal to 3*n+1 for some integer n
        sample_points: number of uniform samples of each cubic spline,
            total number of samples is: sample_points * ((control_points - 3) / 3)

    Returns:
        List of pya.DPoints that can be used as part of a polygon
    """
    if (len(control_points) - 1) % 3 == 0:
        raise ValueError("For Bezier curve, the number of control points should equal to 3*n+1 for some integer n")
    bezier_matrix = np.array([[ 1,-3, 3,-1],
                              [ 0, 3,-6, 3],
                              [ 0, 0, 3,-3],
                              [ 0, 0, 0, 1]])
    result_points = []
    # Windows with one shared control point
    for window_start in range(0, len(control_points) - 3, 3):
        result_points += _cubic_polynomial( control_points[window_start:window_start+4],
                                            bezier_matrix,
                                            sample_points,
                                            endpoint=(window_start == len(control_points) - 4))
    return result_points
