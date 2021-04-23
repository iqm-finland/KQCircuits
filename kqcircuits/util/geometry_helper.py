"""Helper module for general geometric functions"""

from math import cos, sin, radians

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
    """Returns the direction vector corresponding to `angle`."""
    return pya.DVector(cos(radians(angle)), sin(radians(angle)))


def get_cell_path_length(cell, annotation_layer):
    """
    Returns the length of the paths in the cell.

    Args:
        cell: A cell object.
        annotation_layer: An unsigned int representing the annotation_layer.

    """
    length = 0
    for inst in cell.each_inst():  # over child cell instances, not instances of itself
        shapes_iter = inst.cell.begin_shapes_rec(annotation_layer)
        while not shapes_iter.at_end():
            shape = shapes_iter.shape()
            if shape.is_path():
                length += shape.path_dlength()
            shapes_iter.next()
    # in case of waveguide, there are no shapes in the waveguide cell itself
    # but the following allows function reuse in other applications
    for shape in cell.shapes(annotation_layer).each():
        if shape.is_path():
            length += shape.path_dlength()

    return length


def get_object_path_length(obj, layer):
    """Returns sum of lengths of all the paths in the object and its children

    Attributes:
        obj: ObjectInstPath object
        layer: layer integer id in the database
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
    return new_region


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
    return True if det < 0 else False