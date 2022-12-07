# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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
import os
from pathlib import Path
import gmsh
import numpy as np

try:
    import pya
except ImportError:
    import klayout.db as pya


def coord_dist(coord1: [], coord2: []):
    """
    Returns the distance between two points.

    Args:
        coord1(list(float)): coordinates (x, y, z) of point 1.
        coord2(list(float)): coordinates (x, y, z) of point 2.

    Returns:
        (float): distance between point 1 and 2
    """
    return np.linalg.norm(np.array(coord1) - np.array(coord2))


def add_polygon(point_coordinates: [], mesh_size=0):
    """
    Adds the geometry entities in the OpenCASCADE model for generating a polygon and keeps track of all the entities.
    Returns the geometry entity id.

    Args:
        point_coordinates(list(float)): list of point coordinates that frame the polygon
        mesh_size(float): mesh element size, default=0

    Returns:
        (int): entity id of the polygon
    """
    points = [gmsh.model.occ.addPoint(*coord, mesh_size) for coord in point_coordinates]
    lines = [gmsh.model.occ.addLine(points[i - 1], points[i]) for i in range(1, len(points))]
    lines.append(gmsh.model.occ.addLine(points[-1], points[0]))
    loops = [gmsh.model.occ.addCurveLoop(lines)]
    return gmsh.model.occ.addPlaneSurface(loops)


def add_polygon_with_splines(point_coordinates: [], mesh_size: [], tol=1.):
    """
    Adds the geometry entities in the OpenCASCADE model for generating a polygon and keeps track of all the entities.
    Returns the geometry entity ids. This method is similar to `add_polygon`. The only difference is that if the
    distance between two concecutive points < tol, then a spline is generated instead of line. But then ofcourse, there
    should be more than two points. Otherwise the result is the same. If spline is used for a trace of points, compared
    to lines, this makes it easier for the mesher to find a sensible mesh if the points are very close to each other.

    Args:
        point_coordinates(list((float, float, float))): list of coordinates that make up the polygon (when lines are
        drawn between each concecutive points)
        mesh_size(float): mesh size can be given to the points (note that these points are not used in the final mesh in
                          case the boolean operations are used.
        tol(float): tolerance for spline generation (if the distance between two concecutive points is smaller, use
                    spline instead of line)

    Returns:
        (list): list of entity ids
            * point_ids(list(int)): entity ids of each point used in the polygon
            * line_ids(list(int)): entity ids of each line used in the polygon
            * curve_loop_ids(list(int)): entity ids of each curveloop used in the polygon
            * plane_surface_id(int): entity id of the polygon

        Note that all of the ids become obsolete when boolean operations are used in OpenCASCADE kernel.
    """
    point_ids = []
    line_ids = []
    spline_points = []
    spline = False
    i = 0
    for i, coord in enumerate(point_coordinates):
        point_ids.append(gmsh.model.occ.addPoint(*coord, mesh_size))
        point_id = point_ids[-1]
        spline_points.append(point_id)
        if i > 0:
            coord1 = point_coordinates[i - 1]
            coord2 = point_coordinates[i]
            if spline:
                if coord_dist(coord1, coord2) > tol:
                    spline = False
                    spline_points.pop()
                    if len(spline_points) > 2:
                        line_ids.append(gmsh.model.occ.addSpline(spline_points))
                    else:
                        line_ids.append(gmsh.model.occ.addLine(spline_points[0], spline_points[1]))
                    line_ids.append(gmsh.model.occ.addLine(point_ids[i - 1], point_ids[i]))
                    spline_points = [point_id]
            elif coord_dist(coord1, coord2) <= tol:
                spline = True
            else:
                line_ids.append(gmsh.model.occ.addLine(point_ids[i - 1], point_ids[i]))
                spline_points = [point_id]
    if len(spline_points) > 1:  # in case spline and the last point distance < tol
        line_ids.append(gmsh.model.occ.addSpline(spline_points))

    line_ids.append(gmsh.model.occ.addLine(point_ids[i], point_ids[0]))
    curve_loop_ids = [gmsh.model.occ.addCurveLoop(line_ids)]
    plane_surface_id = gmsh.model.occ.addPlaneSurface(curve_loop_ids)
    return point_ids, line_ids, curve_loop_ids, plane_surface_id


def separated_hull_and_holes(polygon):
    """Returns Polygon with holes separated from hull. Takes Polygon or SimplePolygon as the argument."""
    bbox = polygon.bbox().enlarged(10, 10)
    region = pya.Region(bbox) - pya.Region(polygon)
    new_poly = pya.Polygon()
    for p in region.each():
        if p.bbox() == bbox:
            hull_region = pya.Region(bbox) - pya.Region(p)
            new_poly.assign_hull(list(hull_region[0].each_point_hull()), True)
        else:
            new_poly.insert_hole(list(p.each_point_hull()), True)
    return new_poly


def add_shape_polygons(cell: pya.Cell, layer_map: dict, face: str, layer: str, z_level: float, mesh_size: float):
    """
    Create all polygons in a layer using `add_polygon_with_splines` according to the hull of each KLayout shape.
    Returns the so called list of dim_tags of all the created polygons which can be used to refer to the shapes later.

    Args:
        cell(pya.Cell): 2-dimensional geometry as pya.Cell object
        layer_map(dict): map from full layer name to layer number
        face(str): face abbreviation (for example in flip chip, '1t1' is the bottom and '2b1' is the top).
        layer(str): layer name (for example 'simulation_ground')
        z_level(float): the z-coordinate of the layer.
        mesh_size(float): mesh size can be given to the points (note that these points are not used in the final mesh in
                          case the boolean operations are used.
    Returns:
        hull_dim_tags(list(int, int)): dimTag (as called in Gmsh) is a tuple of
            * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
            * tag(int): the id of the entity
    """
    layout = cell.layout()
    shapes = cell.shapes(layout.layer(*layer_map[f"{face}_{layer}"]))
    dim_tags = []
    for shape in shapes.each():
        poly = separated_hull_and_holes(shape.polygon)
        hull_point_coordinates = [(point.x * layout.dbu, point.y * layout.dbu, z_level)
                                  for point in poly.each_point_hull()]
        _, _, _, hull_plane_surface_id = add_polygon_with_splines(hull_point_coordinates, mesh_size)
        hull_dim_tag = (2, hull_plane_surface_id)
        hole_dim_tags = []
        for hole in range(poly.holes()):
            hole_point_coordinates = [(point.x * layout.dbu, point.y * layout.dbu, z_level)
                                      for point in poly.each_point_hole(hole)]
            _, _, _, hole_plane_surface_id = add_polygon_with_splines(hole_point_coordinates, mesh_size)
            hole_dim_tags.append((2, hole_plane_surface_id))
        if hole_dim_tags:
            dim_tags += gmsh.model.occ.cut([hull_dim_tag], hole_dim_tags)[0]
        else:
            dim_tags.append(hull_dim_tag)
    return dim_tags


def create_face(cell: pya.Cell, layer_map: dict, face: str, z_level: float, mesh_sizes=None, port_dim_tags=None):
    """
    Create the face of a chip according to the "simulation_ground", "simulation_gap" and "simulation_signal" layers
    using the `add_shape_polygons` method.

    Args:
        cell(pya.Cell): 2-dimensional geometry as pya.Cell object
        layer_map(dict): map from full layer name to layer number
        face(str): face abbreviation (for example in flip chip, '1t1' is the bottom and '2b1' is the top).
        z_level(float): set the z-coordinate of the chip face.
        mesh_sizes(dict): a mesh size can be given to the points:

            * ground(float): mesh size of the ground layer
            * ground_grid(float): mesh size of the ground grid layer
            * gap(float): mesh size of the gap layer
            * signal(float): mesh size of the signal layer

        port_dim_tags(list): list of DimTags of the port polygons

    Returns:
        tags(dict): a dictionary containing all the dim_tags of the created face:
            * ground(list(int, int)): a list of dim_tags belonging to the ground, dimTag is a tuple of

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity

            * ground_grid(list(int, int)): a list of dim_tags belonging to the ground_grid, dimTag is a tuple of

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity

            * gap(list(int, int)): a list of dim_tags belonging to the gap dimTag  is a tuple of

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity

            * signal(list(int, int)): a list of dim_tags belonging to the signal dimTag is a tuple of

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity

    Note that all of the mesh sizes become obsolete when boolean operations are used in OpenCASCADE kernel.
    """
    if mesh_sizes is None:
        mesh_sizes = {
            'ground': 200.,
            'ground_grid': 200.,
            'gap': 10.,
            'signal': 10.,
        }
    if port_dim_tags is None:
        port_dim_tags = []

    ground_dim_tags = add_shape_polygons(cell, layer_map, face, "simulation_ground", z_level, mesh_sizes['ground'])
    ground_grid_dim_tags = add_shape_polygons(cell, layer_map, face, "ground_grid", z_level, mesh_sizes['ground_grid'])
    gap_dim_tags = add_shape_polygons(cell, layer_map, face, "simulation_gap", z_level, mesh_sizes['gap'])
    signal_dim_tags = add_shape_polygons(cell, layer_map, face, "simulation_signal", z_level, mesh_sizes['signal'])

    if len(ground_dim_tags) > 0 and len(ground_grid_dim_tags) > 0:
        ground_dim_tags, _ = gmsh.model.occ.cut(ground_dim_tags, ground_grid_dim_tags, removeTool=False)
    if len(gap_dim_tags) > 0 and len(port_dim_tags) > 0:
        gap_dim_tags, _ = gmsh.model.occ.cut(gap_dim_tags, port_dim_tags, removeTool=False)

    return {
        'ground': ground_dim_tags,
        'gap': gap_dim_tags,
        'signal': signal_dim_tags,
        'ground_grid': ground_grid_dim_tags,
    }


def bounding_box_from_dim_tags(dim_tags: list):
    """
    Returns the bounding box of all the geometry entities refered to in dim_tags list.

    Args:
        dim_tags(list(int, int)):
            dimTag (as called in Gmsh) is a tuple of:
                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity
    Returns:
        bounding_box(list()):
            * xminmin(float): minimum x-coordinate of all the bounding boxes
            * yminmin(float): minimum y-coordinate of all the bounding boxes
            * zminmin(float): minimum z-coordinate of all the bounding boxes
            * xmaxmax(float): maximum x-coordinate of all the bounding boxes
            * ymaxmax(float): maximum y-coordinate of all the bounding boxes
            * zmaxmax(float): maximum z-coordinate of all the bounding boxes
    """
    for i, dim_tag in enumerate(dim_tags):
        xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.occ.getBoundingBox(*dim_tag)
        if i == 0:
            xminmin = xmin
            yminmin = ymin
            zminmin = zmin
            xmaxmax = xmax
            ymaxmax = ymax
            zmaxmax = zmax
        else:
            xminmin = min(xmin, xminmin)
            yminmin = min(ymin, yminmin)
            zminmin = min(zmin, zminmin)
            xmaxmax = max(xmax, xmaxmax)
            ymaxmax = max(ymax, ymaxmax)
            zmaxmax = max(zmax, zmaxmax)

    return xminmin, yminmin, zminmin, xmaxmax, ymaxmax, zmaxmax


def bounding_box_to_xyzdxdydz(bounding_box: [], dz: float = None):
    """
    Returns a bounding box in a format that is compatible to generating a box.

    Args:
        bounding_box(list):
            * xmin(float): minimum x-coordinate of the bounding box
            * ymin(float): minimum y-coordinate of the bounding box
            * zmin(float): minimum z-coordinate of the bounding box
            * xmax(float): maximum x-coordinate of the bounding box
            * ymax(float): maximum y-coordinate of the bounding box
            * zmax(float): maximum z-coordinate of the bounding box
        dz(float): override the dz of the bounding box
    Returns:
        bounding_box(list):
            * xmin(float): minimum x-coordinate of the bounding box
            * ymin(float): minimum y-coordinate of the bounding box
            * zmin(float): minimum z-coordinate of the bounding box
            * dx(float): dx of the maximum x-coordinate of the bounding box with respect to xmin
            * dy(float): dy of the maximum y-coordinate of the bounding box with respect to ymin
            * dz(float): dz of the maximum z-coordinate of the bounding box with respect to zmin
    """
    x = bounding_box[0]
    y = bounding_box[1]
    z = bounding_box[2]
    dx = bounding_box[3] - bounding_box[0]
    dy = bounding_box[4] - bounding_box[1]
    if dz is None:
        dz = bounding_box[5] - bounding_box[2]
    return x, y, z, dx, dy, dz


def box_volume(dim_tags, height=None):
    """
    Creates a box volume including faces determined by `dim_tags` list, and optionally include also `height`.

    Args:
        dim_tags: a list of dim_tags of the faces to be included into the box,
            dimTag (as called in Gmsh) is a tuple of:

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity

        height: optional z-value to be included into the box

    Returns:
        (int, int): dim_tag of the box volume with dim=3 and tag automatically generated.
    """
    box = bounding_box_to_xyzdxdydz(bounding_box_from_dim_tags(dim_tags), height)
    return 3, gmsh.model.occ.addBox(*box, tag=-1)


def face_tag_dict_to_list(face_dim_tag_dict: dict):
    """
    Reorganize dim_tag dict into a list of dim_tags. Basically the point is to have all the geometric entities
    in the same list, regardless of their membership to certain layers.

    Args:
        face_dim_tag_dict(dict): a dictionary containing all the dim_tags of the created face:

            * ground(list(int, int)): a list of dim_tags belonging to the ground:
                    dimTag (as called in Gmsh) is a tuple of

                        * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                        * tag(int): the id of the entity

            * ground_grid(list(int, int)): a list of dim_tags belonging to the ground_grid:
                    dimTag (as called in Gmsh) is a tuple of

                        * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                        * tag(int): the id of the entity

            * gap(list(int, int)): a list of dim_tags belonging to the gap:
                    dimTag (as called in Gmsh) is a tuple of

                        * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                        * tag(int): the id of the entity

            * signal(list(int, int)): a list of dim_tags belonging to the signal:
                    dimTag (as called in Gmsh) is a tuple of

                        * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                        * tag(int): the id of the entity
    Returns:
        (list(int, int)): a list of dim_tags belonging to the the face:
            dimTag (as called in Gmsh) is a tuple of

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity
    """
    keys = ['ground', 'ground_grid', 'gap', 'signal']
    dim_tags = []
    for key in keys:
        dim_tags += face_dim_tag_dict[key]
    return dim_tags


def get_bounding_boxes(dim_tags: list):
    """
    Return bounding boxes of entities defined by list of dim_tags.

    Args:
        dim_tags(list(int, int)): a list of dim_tags:
            dimTag (as called in Gmsh) is a tuple of

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity
    Returns:
        bboxes(list): list of bounding boxes
            (list): list of floats describing one bounding box

                * xmin(float): minimum x-coordinate of the bounding box
                * ymin(float): minimum y-coordinate of the bounding box
                * zmin(float): minimum z-coordinate of the bounding box
                * xmax(float): maximum x-coordinate of the bounding box
                * ymax(float): maximum y-coordinate of the bounding box
                * zmax(float): maximum z-coordinate of the bounding box
    """
    return [gmsh.model.occ.getBoundingBox(*dim_tag) for dim_tag in dim_tags]


def get_entities_in_bounding_boxes(bboxes: list, dim: int, eps=1e-6):
    """
    Return list of dim_tags of entities in bounding boxes

    Args:
        bboxes(list): list of bounding boxes

            (list): list of floats describing one bounding box

                * xmin(float): minimum x-coordinate of the bounding box
                * ymin(float): minimum y-coordinate of the bounding box
                * zmin(float): minimum z-coordinate of the bounding box
                * xmax(float): maximum x-coordinate of the bounding box
                * ymax(float): maximum y-coordinate of the bounding box
                * zmax(float): maximum z-coordinate of the bounding box

        dim(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
        eps(float): this is added on top of each dimension of the bounding box (min and max) so that
                    everything that is in the box, is really taken into account even if there are some
                    numerical errors.
    Returns:
        out_dim_tags(list(int, int)): a list of dim_tags of the entities that were found:
            dimTag (as called in Gmsh) is a tuple of

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity
    """
    out_dim_tags = []
    for bbox in bboxes:
        xmin, ymin, zmin, xmax, ymax, zmax = bbox
        out_dim_tags += gmsh.model.occ.getEntitiesInBoundingBox(xmin - eps, ymin - eps, zmin - eps,
                                                                xmax + eps, ymax + eps, zmax + eps, dim)
    return out_dim_tags


def set_mesh_size_use_bounding_box(dim_tags: list, mesh_size: float):
    """
    Set the mesh size of those entities that are in the bounding box of entities defined by list of dim_tags.

    Args:
        dim_tags(list(int, int)): a list of dim_tags of the entities to define the bounding boxes:
            dimTag (as called in Gmsh) is a tuple of

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity

            mesh_size: the mesh size to be defined to the entities in the bounding boxes
    """
    bboxes = get_bounding_boxes(dim_tags)
    gmsh.model.mesh.setSize(get_entities_in_bounding_boxes(bboxes, 0), mesh_size)


def produce_geometry_info_for_dim_tags(dim_tags: list):
    """
    Produce some geometry information for the dim_tags for identification purposes.
    Currently, center of mass and bounding box is computed.

    Args:
        dim_tags(list(int, int)): a list of dim_tags of the entities to define the bounding boxes:
            dimTag (as called in Gmsh) is a tuple of

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity

            mesh_size: the mesh size to be defined to the entities in the bounding boxes
    Returns:
        geom_info(dict): geometry info for identification purposes:
            * dim_tag_1(dict): dictionary for dim_tag_1
                * c_o_m(float): Center of mass for dim_tag_1
                * bbox(float): Bounding box for dim_tag_1
                * .
                * .
                * .

            * dim_tag_n(dict): dictionary for dim_tag_n
                * c_o_m(float): Center of mass for dim_tag_n
                * bbox(float): Bounding box for dim_tag_n
                * .
                * .
                * .
    """
    geom_info = {}
    for dim_tag in dim_tags:
        geom_info[dim_tag] = {'c_o_m': gmsh.model.occ.getCenterOfMass(*dim_tag)}
        geom_info[dim_tag]['bbox'] = gmsh.model.occ.getBoundingBox(*dim_tag)

    return geom_info


def map_dim_tags_to_outdim_tags(geom_info: dict, dim: int):
    """
    Returns a mapping from old dim_tags to dim_tags in the current model (typically after fragmentation when the old
    entities are removed). "dimTag" (as called in Gmsh) is a tuple of:

        * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
        * tag(int): the id of the entity

    Args:
        geom_info(dict): geometry info for identification purposes:

            * dim_tag_1(dict): dictionary for dim_tag_1
                * c_o_m(float): Center of mass for dim_tag_1
                * bbox(float): Bounding box for dim_tag_1
                * .
                * .
                * .

            * dim_tag_n(dict): dictionary for dim_tag_n
                * c_o_m(float): Center of mass for dim_tag_n
                * bbox(float): Bounding box for dim_tag_n

        dim(int): dimension of the searched shapes

    Returns:
        dim_tagMap(dict):
            * dim_tag_1(int, int): a dim_tag(int, int) in the current model
                * .
                * .
                * .

            * dim_tag_n(int, int): a dim_tag(int, int) in the current model

    """
    outdim_tags = gmsh.model.occ.getEntities(dim)
    dim_tagMap = {}
    for dim_tag in geom_info:
        bbox = geom_info[dim_tag]['bbox']
        for outdim_tag in outdim_tags:
            outbbox = gmsh.model.occ.getBoundingBox(*outdim_tag)
            if np.allclose(bbox, outbbox, rtol=0.01):
                dim_tagMap[dim_tag] = outdim_tag

    return dim_tagMap


def dtmap(dim_tagMap: dict, dim_tags: list):
    """
    Returns a map old dim_tags->dim_tags in the current model.

    Args:
        dim_tagMap(dict):
            * dim_tag_1(int, int): a dim_tag(int, int) in the current model
                * .
                * .
                * .

            * dim_tag_n(int, int): a dim_tag(int, int) in the current model

        dim_tags(list(int, int)): a list of dim_tags of the entities:
            dimTag (as called in Gmsh) is a tuple of

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity

    Returns:
        outdim_tags(list(int, int)): a list of dim_tags in the current model based on the old dim_tags and the
            dim_tagMap -mapping: dimTag (as called in Gmsh) is a tuple of:
                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity
    """
    mapped_dim_tags = [dim_tagMap[dim_tag] for dim_tag in dim_tags]
    return gmsh.model.getBoundary(mapped_dim_tags, False, False, True)


def set_mesh_size(dim_tags: list, min_mesh_size: float, max_mesh_size: float, dist_min: float, dist_max: float,
                  sampling: float = None):
    """
    Set the mesh size such that it is `min_mesh_size` when near the curves of boundaries defined by the entities of
    dim_tags and gradually increasing to `max_mesh_size`.

    .. code-block:: text

      max_mesh_size -                     /------------------
                                         /
                                        /
                                       /
      min_mesh_size -o----------------/
                     |                |    |
                  Point         dist_min  dist_max

    Args:

        dim_tags(list(int, int)): a list of BOUNDARY dim_tags:
            dimTag (as called in Gmsh) is a tuple of

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity

        min_mesh_size(float): minimum mesh size
        max_mesh_size(float): maximum mesh size
        dist_min(float): distance to which the minimum mesh size is used
        dist_max(float): distance after which the maximum mesh size is used
        sampling(fload): number of sampling points when computing the distance from the curve. The default
                         value is None. In that case the value is determined by 1.5 times the maximum reachable
                         distance in the bounding box of the entity (curve) divided by the minimum mesh size. At
                         the moment there is no obvious way to implement curve_length/min_mesh_size type of
                         algorithm.

    Returns:
        tag_threshold_fields(list(int)): tag list of the threshold fields that were defined in this function
    """
    outdim_tags = gmsh.model.getBoundary(dim_tags, combined=False, oriented=False, recursive=True)  # search points
    gmsh.model.mesh.setSize(outdim_tags, min_mesh_size)

    outdim_tags = gmsh.model.getBoundary(dim_tags, combined=False, oriented=False, recursive=False)  # search lines

    tag_threshold_fields = []
    if sampling is None:
        for dim_tag in outdim_tags:
            curve = dim_tag[1]
            tag_distance_field = gmsh.model.mesh.field.add("Distance")
            gmsh.model.mesh.field.setNumbers(tag_distance_field, "CurvesList", [curve])
            bbox = gmsh.model.occ.getBoundingBox(*dim_tag)
            bbox_maxdist = coord_dist(bbox[:3], bbox[3:6])
            sampling = np.ceil(1.5 * bbox_maxdist / min_mesh_size)
            gmsh.model.mesh.field.setNumber(tag_distance_field, "Sampling", sampling)
            tag_threshold_field = gmsh.model.mesh.field.add("Threshold")
            gmsh.model.mesh.field.setNumber(tag_threshold_field, "InField", tag_distance_field)
            gmsh.model.mesh.field.setNumber(tag_threshold_field, "SizeMin", min_mesh_size)
            gmsh.model.mesh.field.setNumber(tag_threshold_field, "SizeMax", max_mesh_size)
            gmsh.model.mesh.field.setNumber(tag_threshold_field, "DistMin", dist_min)
            gmsh.model.mesh.field.setNumber(tag_threshold_field, "DistMax", dist_max)
            tag_threshold_fields.append(tag_threshold_field)
    else:
        curve_list = [dim_tag[1] for dim_tag in outdim_tags]
        tag_distance_field = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(tag_distance_field, "CurvesList", curve_list)
        gmsh.model.mesh.field.setNumber(tag_distance_field, "Sampling", sampling)
        tag_threshold_field = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(tag_threshold_field, "InField", tag_distance_field)
        gmsh.model.mesh.field.setNumber(tag_threshold_field, "SizeMin", min_mesh_size)
        gmsh.model.mesh.field.setNumber(tag_threshold_field, "SizeMax", max_mesh_size)
        gmsh.model.mesh.field.setNumber(tag_threshold_field, "DistMin", dist_min)
        gmsh.model.mesh.field.setNumber(tag_threshold_field, "DistMax", dist_max)
        tag_threshold_fields.append(tag_threshold_field)
    return tag_threshold_fields


def get_bbox_sides_as_bboxes(bbox):
    """
    Returns the sides of a bounding box in a bounding box format.

    Args:
        bbox(list): list of floats describing one bounding box

            * xmin(float): minimum x-coordinate of the bounding box
            * ymin(float): minimum y-coordinate of the bounding box
            * zmin(float): minimum z-coordinate of the bounding box
            * xmax(float): maximum x-coordinate of the bounding box
            * ymax(float): maximum y-coordinate of the bounding box
            * zmax(float): maximum z-coordinate of the bounding box

    Returns:
        (dict): each value in a format as the input argument `bbox`

            * xmin: bounding box of the side where x is xmin
            * xmax: bounding box of the side where x is xmax
            * ymin: bounding box of the side where y is ymin
            * ymax: bounding box of the side where y is ymax
            * zmin: bounding box of the side where z is zmin
            * zmax: bounding box of the side where z is zmax

    """
    xmin, ymin, zmin, xmax, ymax, zmax = bbox
    return {
        'xmin': (xmin, ymin, zmin, xmin, ymax, zmax),
        'xmax': (xmax, ymin, zmin, xmax, ymax, zmax),
        'ymin': (xmin, ymin, zmin, xmax, ymin, zmax),
        'ymax': (xmin, ymax, zmin, xmax, ymax, zmax),
        'zmin': (xmin, ymin, zmin, xmax, ymax, zmin),
        'zmax': (xmin, ymin, zmax, xmax, ymax, zmax),
    }

def get_parent_body(dim_tag, body_dim_tags):
    """
    Find the parent body of a (outer) boundary.
    """

    return next(
        (
            e
            for e in body_dim_tags
            if dim_tag in gmsh.model.getBoundary([e], oriented=False)
        ),
        None,
    )

def set_physical_name(dim_tag, name):
    gmsh.model.addPhysicalGroup(dim_tag[0], [dim_tag[1]], name=name)

def export_gmsh_msh(sim_data: dict, path: Path, default_mesh_size: float = 100, signal_min_mesh_size: float = 100,
                    signal_min_dist: float = 100, signal_max_dist: float = 100,
                    signal_sampling: float = None, ground_min_mesh_size: float = 100,
                    ground_min_dist: float = 100, ground_max_dist: float = 100, ground_sampling: float = None,
                    ground_grid_min_mesh_size: float = 100,
                    ground_grid_min_dist: float = 100, ground_grid_max_dist: float = 100,
                    ground_grid_sampling: float = None, gap_min_mesh_size: float = 100,
                    gap_min_dist: float = 100, gap_max_dist: float = 100,
                    gap_sampling: float = None, port_min_mesh_size: float = 100,
                    port_min_dist: float = 100, port_max_dist: float = 100, port_sampling: float = None,
                    algorithm: int = 5, show: bool = False, gmsh_n_threads: int = 1):
    """
    Builds the model using OpenCASCADE kernel and exports the result in "simulation.msh"
    file in the specified simulation `path`

    Args:

        sim_data(dict): simulation data in dictionary format
        path(Path): path of the simulation export folder
        default_mesh_size(float): Default size to be used where not defined
        signal_min_mesh_size(float): Minimum mesh size near signal region curves
        signal_min_dist(float): Mesh size will be the minimum size until this distance
                                from the signal region curves
        signal_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the signal region curves
        signal_sampling(float): Number of points used for sampling each signal region curve
        ground_min_mesh_size(float): Minimum mesh size near ground region curves
        ground_min_dist(float): Mesh size will be the minimum size until this distance
                                from the ground region curves
        ground_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the ground region curves
        ground_sampling(float): Number of points used for sampling each ground region curve
        ground_grid_min_mesh_size(float): Minimum mesh size near ground_grid region curves
        ground_grid_min_dist(float): Mesh size will be the minimum size until this distance
                                from the ground_grid region curves
        ground_grid_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the ground_grid region curves
        ground_grid_sampling(float): Number of points used for sampling each ground_grid region curve
        gap_min_mesh_size(float): Minimum mesh size near gap region curves
        gap_min_dist(float): Mesh size will be the minimum size until this distance
                                from the gap region curves
        gap_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the gap region curves
        gap_sampling(float): Number of points used for sampling each gap region curve
        port_min_mesh_size(float): Minimum mesh size near port region curves
        port_min_dist(float): Mesh size will be the minimum size until this distance
                                from the port region curves
        port_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the port region curves
        port_sampling(float): Number of points used for sampling each port region curve
        algorithm(float): Gmsh meshing algorithm (default is 5)
        show(float): Show the mesh in Gmsh graphical interface after completing the mesh
                     (for large meshes this can take a long time)
        gmsh_n_threads(int): number of threads used in Gmsh meshing (default=1, -1 means all physical cores)

    Returns:

        tuple:

            * filepath(Path): Path to exported msh file
            * model_data(dict): Model data for creating Elmer sif file (see export_elmer_sif)
    """
    params = sim_data['parameters']
    filepath = Path(path).joinpath(params['name'] + '.msh')

    if gmsh_n_threads == -1:
        gmsh_n_threads = int(os.cpu_count() / 2 + 0.5)  # for the moment avoid psutil.cpu_count(logical=False)

    gmsh.initialize()
    gmsh.option.setNumber("General.NumThreads", gmsh_n_threads)
    gmsh.model.add(params['name'])

    layout = pya.Layout()
    layout.read(str(Path(path).joinpath(sim_data['gds_file'])))
    cell = layout.top_cell()

    port_data_gmsh = sim_data['ports']
    faces = [0] if params['wafer_stack_type'] == 'planar' else [0, 1]
    face_z_levels = [0 if params['face_ids'][face] == '1t1' else params['chip_distance'] for face in faces]
    chip_dzs = [-params['substrate_height'] if params['face_ids'][face] == '1t1' else params['substrate_height_top']
                for face in faces]

    # Produce shapes
    face_port_dim_tags = [[] for _ in faces]
    edge_port_dim_tags = []
    for port in port_data_gmsh:
        if 'polygon' in port:
            # add port polygon and store its dim_tag
            surface_id = add_polygon(port['polygon'], port_min_mesh_size)
            port['dim_tag'] = (2, surface_id)
            if port['type'] == 'InternalPort':
                face_port_dim_tags[port['face']].append(port['dim_tag'])
            else:
                edge_port_dim_tags.append(port['dim_tag'])
                port['occ_bounding_box'] = gmsh.model.occ.getBoundingBox(*port['dim_tag'])

    face_dim_tag_dicts = []
    chips = []
    face_dim_tags = []
    for face in faces:
        face_dim_tag_dicts.append(create_face(cell, sim_data['layers'], params['face_ids'][face],
                                              face_z_levels[face], port_dim_tags=face_port_dim_tags[face]))
        chips.append(box_volume(face_dim_tag_dicts[face]['ground'], chip_dzs[face]))
        face_dim_tags.append(face_tag_dict_to_list(face_dim_tag_dicts[face]))

    ground_dim_tags = [v for f in face_dim_tag_dicts for v in f['ground']]
    vacuum = box_volume(ground_dim_tags, params['box_height'] if params['wafer_stack_type'] == 'planar' else None)

    # Finalize geometry using fragment -> dim_tags need to be updated
    all_dim_tags = chips + [vacuum] + [a for b in face_dim_tags for a in b] + [a for b in face_port_dim_tags for a in
                                                                               b] + edge_port_dim_tags
    all_dim_tags_new, dim_tags_map_imp = gmsh.model.occ.fragment(all_dim_tags, [], removeTool=False)
    dim_tags_map = dict(zip(all_dim_tags, dim_tags_map_imp))
    face_port_dim_tags = [[t for tag in tags for t in dim_tags_map[tag]] for tags in face_port_dim_tags]
    new_ground_dim_tags = [new_tag for old_tag in ground_dim_tags for new_tag in dim_tags_map[old_tag] ]

    face_dim_tag_dicts = [{k: [t for tag in d[k] for t in dim_tags_map[tag]] for k in d} for d in face_dim_tag_dicts]
    chips = [t for tag in chips for t in dim_tags_map[tag]]
    vacuum = dim_tags_map[vacuum][0]
    gmsh.model.occ.synchronize()

    gmsh.model.mesh.setSize(gmsh.model.getEntities(0), default_mesh_size)
    mesh_field_ids = []
    for face in faces:
        mesh_field_ids += set_mesh_size(face_dim_tag_dicts[face]['signal'],
                                        signal_min_mesh_size, default_mesh_size, signal_min_dist,
                                        signal_max_dist, signal_sampling)
        mesh_field_ids += set_mesh_size(face_dim_tag_dicts[face]['ground'],
                                        ground_min_mesh_size, default_mesh_size, ground_min_dist,
                                        ground_max_dist, ground_sampling)
        mesh_field_ids += set_mesh_size(face_dim_tag_dicts[face]['gap'],
                                        gap_min_mesh_size, default_mesh_size, gap_min_dist, gap_max_dist,
                                        gap_sampling)
        mesh_field_ids += set_mesh_size(face_dim_tag_dicts[face]['ground_grid'], ground_grid_min_mesh_size,
                                        default_mesh_size, ground_grid_min_dist, ground_grid_max_dist,
                                        ground_grid_sampling)
        mesh_field_ids += set_mesh_size(face_port_dim_tags[face],
                                        port_min_mesh_size, default_mesh_size, port_min_dist, port_max_dist,
                                        port_sampling)

    for port in port_data_gmsh:
        face = port['face']
        if 'ground_location' in port:
            # Use 1e-2 safe margin to ensure that signal_location is in the signal polygon:
            signal_location = [x + 1e-2 * (x - y) for x, y in zip(port['signal_location'], port['ground_location'])]
        else:
            signal_location = list(port['signal_location'])
        signal_location += [params['chip_distance'] if face == 1 else 0.0]  # z-component

        for dim_tag in face_dim_tag_dicts[face]['signal']:
            if gmsh.model.isInside(*dim_tag, signal_location):
                port['signal_dim_tag'] = dim_tag
                port['signal_physical_name'] = 'signal_' + str(port['number'])
                set_physical_name(dim_tag, port['signal_physical_name'])

    for _ in face_dim_tag_dicts:
        body_dim_tags = gmsh.model.getEntities(3)
        body_port_phys_map = {}
        for dim_tag in body_dim_tags:
            body_port_phys_map[dim_tag] = []
        for port in port_data_gmsh:
            port['physical_names'] = []
            if 'polygon' in port:
                if port['type'] == 'InternalPort':
                    port_physical_name = 'port_' + str(port['number'])
                    set_physical_name(port['dim_tag'], port_physical_name)
                    parent_body_dim_tag = get_parent_body(port['dim_tag'], body_dim_tags)
                    if parent_body_dim_tag is not None:
                        port['physical_names'].append((parent_body_dim_tag, port_physical_name))
                        body_port_phys_map[parent_body_dim_tag].append(port_physical_name)

                else:
                    port['dim_tags'] = get_entities_in_bounding_boxes([port['occ_bounding_box']], 2)
                    for i, dim_tag in enumerate(port['dim_tags']):
                        port_physical_name = 'port_{}_{}'.format(port['number'], i)
                        set_physical_name(dim_tag, port_physical_name)
                        parent_body_dim_tag = get_parent_body(dim_tag, body_dim_tags)
                        if parent_body_dim_tag is not None:
                            port['physical_names'].append((parent_body_dim_tag, port_physical_name))
                            body_port_phys_map[parent_body_dim_tag].append(port_physical_name)

    for face in faces:
        set_physical_name(chips[face], 'chip_{}'.format(face))
    set_physical_name(vacuum, 'vacuum')

    # Find all the extreme boundaries and add physical names to them
    bbox_all = bounding_box_from_dim_tags(all_dim_tags_new)
    bbox_all_sides = get_bbox_sides_as_bboxes(bbox_all)
    for side_name in ['xmin', 'ymin', 'zmin', 'xmax', 'ymax', 'zmax']:
        bbox_all_dim_tags = get_entities_in_bounding_boxes([bbox_all_sides[side_name]], 2)
        for i, dim_tag in enumerate(bbox_all_dim_tags):
            set_physical_name(dim_tag, '{}_{}'.format(side_name, i))

    ground_names = []
    for i, dim_tag in enumerate(new_ground_dim_tags):
        ground_name = 'ground_{}'.format(i)
        set_physical_name(dim_tag, ground_name)
        ground_names.append(ground_name)

    background_field_id = gmsh.model.mesh.field.add("Min")
    gmsh.model.mesh.field.setNumbers(background_field_id, "FieldsList", mesh_field_ids)
    gmsh.model.mesh.field.setAsBackgroundMesh(background_field_id)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.Algorithm", algorithm)
    gmsh.option.setNumber("Mesh.Algorithm3D", 10)  # HTX
    gmsh.option.setNumber("Mesh.ToleranceInitialDelaunay", 1e-14)
    gmsh.option.setNumber("Mesh.MaxNumThreads1D", gmsh_n_threads)
    gmsh.option.setNumber("Mesh.MaxNumThreads2D", gmsh_n_threads)
    gmsh.option.setNumber("Mesh.MaxNumThreads3D", gmsh_n_threads)

    gmsh.model.mesh.generate(3)
    gmsh.write(str(filepath))
    if show:
        gmsh.fltk.run()
    gmsh.finalize()

    # TODO: make more intelligent material selector
    if params['wafer_stack_type'] == 'planar':
        body_materials = {
                (3, 1): "dielectric",
                (3, 2): "vacuum",
                }
    else:
        body_materials = {
                (3, 1): "dielectric",
                (3, 2): "dielectric",
                (3, 3): "vacuum",
                }

    # produce data to create Elmer sif file
    model_data = {
        'tool': sim_data['tool'],
        'faces': len(faces),
        'port_signal_names': [p['signal_physical_name'] for p in port_data_gmsh if 'signal_physical_name' in p],
        'body_port_phys_map': body_port_phys_map,
        'body_dim_tags': body_dim_tags,
        'body_materials': body_materials,
        'ground_names': ground_names,
        'substrate_permittivity': params['permittivity'],
    }
    return Path(filepath), model_data
