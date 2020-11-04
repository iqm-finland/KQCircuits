"""Helper module for general geometric functions"""
from kqcircuits.pya_resolver import pya
import numpy as np


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
    else: # is a shape
        # TODO ignore paths on wrong layers
        shape = obj.shape
        if shape.is_path():
            return shape.path_dlength()
    return 0

def simple_region(region):
    return pya.Region([poly.to_simple_polygon() for poly in region.each()])

def simple_region_with_merged_points(region, tolerance):
    """ Converts all polygons in a region to simple polygons, and removes points that are closer together than
    a given tolerance.

    Arguments:
        region: Input region
        tolerance: Minimum distance, in database units, between two adjacent points in the resulting region

    Returns:
        region with only simple polygons
    """
    def find_next(i, step, data):
        """ Returns the next index starting from 'i' to direction 'step' for which 'data' has positive value """
        s = len(data)
        j = i + step
        while data[j % s] <= 0.0: j += step
        return j

    # Quick exit if tolerance is not positive
    if tolerance <= 0.0:
        return simple_region(region)

    squared_tolerance = tolerance**2
    new_region = pya.Region()
    for poly in region.each():
        simple_poly = poly.to_simple_polygon()
        size = simple_poly.num_points()

        # find length of each segment of polygon
        lensq = [0.0] * size
        for i in range(0, size):
            lensq[i] = simple_poly.point(i).sq_distance(simple_poly.point((i+1) % size))

        # merge short segments
        i = 0
        while i < size:
            if lensq[i % size] >= squared_tolerance:
                # segment long enough: increase 'i' for the next iteration
                i = find_next(i, 1, lensq)
                continue

            # segment too short: merge segment with the shorter neighbor segment (prev or next)
            prev = find_next(i, -1, lensq)
            next = find_next(i, 1, lensq)
            if lensq[prev % size] < lensq[next % size]: # merge with the previous segment
                lensq[i % size] = 0.0
                i = prev
            else: # merge with the next segment
                lensq[next % size] = 0.0
                next = find_next(next, 1, lensq)
            lensq[i % size] = simple_poly.point(i % size).sq_distance(simple_poly.point(next % size))

        # insert polygon
        new_points = [val for i, val in zip(lensq, simple_poly.each_point()) if i > 0.0]
        new_region.insert(pya.SimplePolygon(new_points))

    return new_region

def region_with_merged_polygons(region, tolerance):
    """ Merges polygons in given region.
    If tolerance > 0, then matches closely located points and edges of different polygons before merging.

    Arguments:
        region: input region
        tolerance: minimum distance, in database units, between two polygons

    Returns:
        region with merged polygons
    """
    def nearest_point(ofpoints, topoint):
        """ Finds the point from list 'ofpoints' with shortest distance to point 'topoint'
        Returns:
             tuple of minimal squared distance 'min_sq' and nearest point 'min_point'
        """
        min_sq = 1e30
        min_point = None
        for point in ofpoints:
            sq = point.sq_distance(topoint)
            if sq < min_sq:
                min_point = point
                min_sq = sq
        return (min_sq, min_point)

    def nearest_edge(ofpoints, topoint):
        """ Finds the edge from point list 'ofpoints' with shortest distance to point 'topoint'
        Returns:
             tuple of minimal squared distance 'min_sq' and edge id 'min_i'
        """
        size = len(ofpoints)
        min_sq = 1e30
        min_i = 0
        for i in range(0, size):
            edge0 = ofpoints[i-1]
            edge1 = ofpoints[i]
            edge_v = np.array([edge1.x - edge0.x, edge1.y - edge0.y])
            point_v = np.array([topoint.x - edge0.x, topoint.y - edge0.y])
            dot = np.inner(point_v, edge_v)
            if dot <= 0.0: continue
            lensq = np.inner(edge_v, edge_v)
            if dot >= lensq: continue
            v = point_v - (dot / lensq) * edge_v
            sq = np.inner(v,v)
            if sq < min_sq:
                min_i = i
                min_sq = sq
        return (min_sq, min_i)

    # Quick exit if tolerance is not positive
    if tolerance <= 0.0:
        return region.merged()

    # Store hulls and holes of polygons into matrix of points.
    # Also compute bounding boxes of each polygon to improve merging efficiency.
    new_points = [] # matrix of points
    hull_box = [] # extended polygon bounding box
    for poly in region.each():
        new_rings = [[i for i in poly.each_point_hull()]]
        for hole in range(poly.holes()):
            new_rings.append([i for i in poly.each_point_hole(hole)])
        new_points.append(new_rings)
        box = poly.bbox()
        box.p1 -= pya.Point(tolerance, tolerance)
        box.p2 += pya.Point(tolerance, tolerance)
        hull_box.append(box)

    # Relocate points that are close to points of other polygons.
    # Also create new points on edges that are close to points of other polygons.
    squared_tolerance = tolerance**2
    for p1 in range(len(new_points)):
        for p2 in range(p1+1, len(new_points)):
            if not hull_box[p1].overlaps(hull_box[p2]):
                continue # extended bounding boxes do not overlap -> further comparison between polygons not needed
            poly1 = new_points[p1]
            poly2 = new_points[p2]
            for r1 in range(len(poly1)):
                for r2 in range(len(poly2)):
                    if r1 * r2 > 0: break # no need to compare polygon hole with other polygon hole
                    ring1 = poly1[r1]
                    ring2 = poly2[r2]
                    for point2 in ring2:
                        (sq, point1) = nearest_point(ring1, point2)
                        if sq < squared_tolerance: # move point of ring2
                            point2.x = point1.x
                            point2.y = point1.y
                            continue
                        (sq, ins) = nearest_edge(ring1, point2)
                        if sq < squared_tolerance: # insert point on edge of ring1
                            ring1.insert(ins, pya.Point(point2.x, point2.y))
                    for point1 in ring1:
                        (sq, ins) = nearest_edge(ring2, point1)
                        if sq < squared_tolerance: # insert point on edge of ring2
                            ring2.insert(ins, pya.Point(point1.x, point1.y))

    # Create new merged region from matrix of points
    new_region = pya.Region()
    for rings in new_points:
        new_poly = pya.Polygon(rings[0])
        for hole in range(1, len(rings)):
            new_poly.insert_hole(rings[hole])
        new_region.insert(new_poly)
    return new_region.merged()


