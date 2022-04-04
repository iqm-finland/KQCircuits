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
from pathlib import Path
import os
import gmsh
from kqcircuits.simulations.simulation import Simulation
import numpy as np

def coord_dist(coord1: [], coord2: []):
    """
    Returns the distance of two points based on two coordinates.

    Args:
        coord1(list(float)): coordinates (x, y, z) of point 1.
        coord2(list(float)): coordinates (x, y, z) of point 2.

    Returns:
        (float): distance between point 1 and 2
    """
    return np.sqrt(
                  (coord1[0]-coord2[0])**2.
                + (coord1[1]-coord2[1])**2.
                + (coord1[2]-coord2[2])**2.
    )

def add_polygon(point_coordinates: [], mesh_size: float):
    """
    Adds the geometry entities in the OpenCASCADE model for generating a polygon and keeps track of all the entities.
    Returns the geometry entity ids.

    Args:
        point_coordinates(list(float)):
            list of coordinates that make up the polygon (when lines are drawn betwee each concecutive points)
        mesh_size(float):
            mesh size can be given to the points (note that these points are not used in the final mesh
            in case the boolean operations are used.

    Returns:
        (list()): list of entity ids
            * point_ids(list(int)): entity ids of each point used in the polygon
            * line_ids(list(int)): entity ids of each line used in the polygon
            * curve_loop_ids(list(int)): entity ids of each curveloop used in the polygon
            * plane_surface_id(int): entity id of the polygon

        Note that all of the ids become obsolete when boolean operations are used in OpenCASCADE kernel.
    """
    point_ids = []
    line_ids = []
    curve_loop_ids = []
    i = 0
    for i, coord in enumerate(point_coordinates):
        point_ids.append(gmsh.model.occ.addPoint(*coord, mesh_size))
        if i > 0:
            line_ids.append(gmsh.model.occ.addLine(point_ids[i-1], point_ids[i]))
    line_ids.append(gmsh.model.occ.addLine(point_ids[i], point_ids[0]))
    curve_loop_ids.append(gmsh.model.occ.addCurveLoop(line_ids))
    plane_surface_id = gmsh.model.occ.addPlaneSurface(curve_loop_ids)
    return point_ids, line_ids, curve_loop_ids, plane_surface_id

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
    curve_loop_ids = []
    spline_points = []
    spline = False
    i = 0
    for i, coord in enumerate(point_coordinates):
        point_ids.append(gmsh.model.occ.addPoint(*coord, mesh_size))
        point_id = point_ids[-1]
        spline_points.append(point_id)
        if i > 0:
            coord1 = point_coordinates[i-1]
            coord2 = point_coordinates[i]
            if spline:
                if coord_dist(coord1, coord2) > tol:
                    spline = False
                    spline_points.pop()
                    if len(spline_points) > 2:
                        line_ids.append(gmsh.model.occ.addSpline(spline_points))
                    else:
                        line_ids.append(gmsh.model.occ.addLine(spline_points[0], spline_points[1]))
                    line_ids.append(gmsh.model.occ.addLine(point_ids[i-1], point_ids[i]))
                    spline_points = [point_id]
            else:
                if coord_dist(coord1, coord2) <= tol:
                    spline = True
                else:
                    line_ids.append(gmsh.model.occ.addLine(point_ids[i-1], point_ids[i]))
                    spline_points = [point_id]
    if len(spline_points) > 1:  # in case spline and the last point distance < tol
        line_ids.append(gmsh.model.occ.addSpline(spline_points))

    line_ids.append(gmsh.model.occ.addLine(point_ids[i], point_ids[0]))
    curve_loop_ids.append(gmsh.model.occ.addCurveLoop(line_ids))
    plane_surface_id = gmsh.model.occ.addPlaneSurface(curve_loop_ids)
    return point_ids, line_ids, curve_loop_ids, plane_surface_id

def add_shape_polygons(simulation: Simulation, face_id: int, layer_name: str, z_level: float, mesh_size: float):
    """
    Create all polygons in a layer using `add_polygon_with_splines` according to the hull of each KLayout shape.
    Returns the so called list of dim_tags of all the created polygons which can be used to refer to the shapes later.

    Args:
        simulation(Simulation): KQC simulation object that contains all the polygons.
        face_id(int): KQC uses face ids to differenciate between different chips faces (for example in flip chip, 0 is
                      the bottom and 1 is the top).
        layer_name(str): the name of the layer to be created.
        z_level(float): the z-coordinate of the layer.
        mesh_size(float): mesh size can be given to the points (note that these points are not used in the final mesh in
                          case the boolean operations are used.
    Returns:
        hull_dim_tags(list(int, int)): dimTag (as called in Gmsh) is a tuple of
            * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
            * tag(int): the id of the entity
    """
    layout = simulation.layout
    shapes = simulation.cell.shapes(layout.layer(simulation.face(face_id)[layer_name]))
    hull_dim_tags = []
    for shape in shapes.each():
        hull_point_coordinates = [(point.x*layout.dbu, point.y*layout.dbu, z_level)
                                  for point in shape.each_point_hull()]
        _, _, _, hull_plane_surface_id = add_polygon_with_splines(hull_point_coordinates, mesh_size)
        hull_dim_tags.append((2, hull_plane_surface_id))
    return hull_dim_tags

def create_face(face_id: int, z_level: float, simulation: Simulation, mesh_sizes=None, port_dim_tags=None):
    """
    Create the face of a chip according to the "simulation_ground", "simulation_gap" and "simulation_signal" layers
    using the `add_shape_polygons` method.

    Args:
        face_id(int): KQC uses face ids to differenciate between different chips faces (for example in flip chip, 0 is
            the bottom and 1 is the top).
        z_level(float): set the z-coordinate of the chip face.
        simulation(Simulation): KQC simulation object that contains all the polygons.
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

    ground_hull_dim_tags = add_shape_polygons(simulation, face_id, "simulation_ground",
            z_level, mesh_sizes['ground'])
    ground_grid_hull_dim_tags = add_shape_polygons(simulation, face_id, "ground_grid",
            z_level, mesh_sizes['ground_grid'])
    gap_hull_dim_tags = add_shape_polygons(simulation, face_id, "simulation_gap",
            z_level, mesh_sizes['gap'])
    signal_hull_dim_tags = add_shape_polygons(simulation, face_id, "simulation_signal",
            z_level, mesh_sizes['signal'])

    if len(ground_hull_dim_tags) > 0 and (len(gap_hull_dim_tags) > 0 or len(ground_grid_hull_dim_tags) > 0):
        cutter = gap_hull_dim_tags + ground_grid_hull_dim_tags
        ground_dim_tags, _ = gmsh.model.occ.cut(ground_hull_dim_tags, cutter, removeTool=False)
        cutter = signal_hull_dim_tags + port_dim_tags
        gap_dim_tags, _ = gmsh.model.occ.cut(gap_hull_dim_tags, cutter, removeTool=False)
    else:
        ground_dim_tags = ground_hull_dim_tags
        gap_dim_tags = gap_hull_dim_tags

    tags = {
        'ground': ground_dim_tags,
        'gap': gap_dim_tags,
        'signal': signal_hull_dim_tags,
        'ground_grid': ground_grid_hull_dim_tags,
    }

    return tags

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

    bounding_box = xminmin, yminmin, zminmin, xmaxmax, ymaxmax, zmaxmax

    return bounding_box

def bounding_box_to_xyzdxdydz(bounding_box: [], dz: float=None):
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
    dx = bounding_box[3]-bounding_box[0]
    dy = bounding_box[4]-bounding_box[1]
    if dz is None:
        dz = bounding_box[5]-bounding_box[2]
    return x, y, z, dx, dy, dz

def substrate(face_dim_tag_dict: dict, dz: float):
    """
    Create a substrate that has fits the size of a created face and has the thickness of `dz`.

    Args:
        face_dim_tag_dict(dict):
            a dictionary containing all the dim_tags of the created face:
                * ground(list(int, int)): a list of dim_tags belonging to the ground, dimTag (as in Gmsh) is a tuple of
                    * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                    * tag(int): the id of the entity

                * gap(list(int, int)): a list of dim_tags belonging to the gap dimTag (as in Gmsh) is a tuple of
                    * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                    * tag(int): the id of the entity

                * signal(list(int, int)): a list of dim_tags belonging to the signal dimTag (as in Gmsh) is a tuple of
                    * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                    * tag(int): the id of the entity

        dz(float): chip thickness
    Returns:
        (int, int): dim_tag of the substrate volume with dim=3 and tag automatically generated.
    """
    face_bounding_box = bounding_box_from_dim_tags(face_dim_tag_dict['ground'])
    xyzdxdydz = bounding_box_to_xyzdxdydz(face_bounding_box, dz)
    return (3, gmsh.model.occ.addBox(*xyzdxdydz, tag=-1))

def vacuum_between_faces(face0_ground_dim_tags: list, face1_ground_dim_tags: list):
    """
    Create a vacuum between the faces 0 and 1.

    Args:
        face0_ground_dim_tags(list(int, int)): a list of dim_tags belonging to the ground,
            dimTag (as called in Gmsh) is a tuple of:

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity

        face1_ground_dim_tags(list(int, int)): a list of dim_tags belonging to the ground,
            dimTag (as called in Gmsh) is a tuple of:

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity

    Returns:
        (int, int): dim_tag of the vacuum volume with dim=3 and tag automatically generated.
    """
    bounding_box = bounding_box_from_dim_tags(face0_ground_dim_tags + face1_ground_dim_tags)
    xyzdxdydz = bounding_box_to_xyzdxdydz(bounding_box)
    return (3, gmsh.model.occ.addBox(*xyzdxdydz, tag=-1))

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
    bboxes = []
    for dim_tag in dim_tags:
        bboxes.append(gmsh.model.occ.getBoundingBox(*dim_tag))
    return bboxes

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
        geom_info[dim_tag] = {}
        geom_info[dim_tag]['c_o_m'] = gmsh.model.occ.getCenterOfMass(*dim_tag)
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
    for dim_tag in geom_info.keys():
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
            bbox_maxdist = coord_dist(bbox[0:3], bbox[3:6])
            sampling = np.ceil(1.5*bbox_maxdist/min_mesh_size)
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

def add_port(port, mesh_size: float):
    """
    Adds a port polygon to the model, sets the signal and ground ids and returns the port dim_tag.

    Args:
        port(simulation.port): a port defined in the `Simulation` class.
        mesh_size(float): mesh size can be given to the points (note that these points are not used in the final mesh in
                          case the boolean operations are used.

    Returns:
        dim_tag: DimTag of the port polygon
    """
    _, line_ids, _, surface_id = add_polygon(port['polygon'], mesh_size)
    port['dim_tag'] = (2, surface_id)
    gmsh.model.occ.synchronize()

    if port['type'] == 'InternalPort':
        for line_id in line_ids:
            if gmsh.model.isInside(1, line_id, port['signal_edge'][0]) and \
               gmsh.model.isInside(1, line_id, port['signal_edge'][1]):
                signal_id = line_id
            elif gmsh.model.isInside(1, line_id, port['ground_edge'][0]) and \
                    gmsh.model.isInside(1, line_id, port['ground_edge'][1]):
                ground_id = line_id

        port['signal_edge_dim_tag'] = (1, signal_id)
        port['ground_edge_dim_tag'] = (1, ground_id)

    return port['dim_tag']

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
    sides = {
        'xmin': (xmin, ymin, zmin, xmin, ymax, zmax),
        'xmax': (xmax, ymin, zmin, xmax, ymax, zmax),
        'ymin': (xmin, ymin, zmin, xmax, ymin, zmax),
        'ymax': (xmin, ymax, zmin, xmax, ymax, zmax),
        'zmin': (xmin, ymin, zmin, xmax, ymax, zmin),
        'zmax': (xmin, ymin, zmax, xmax, ymax, zmax),
    }
    return sides

def export_gmsh_msh(simulation: Simulation, path: Path,
                    default_mesh_size: float = 100,
                    signal_min_mesh_size: float = 100,
                    signal_max_mesh_size: float = 100,
                    signal_min_dist: float = 100,
                    signal_max_dist: float = 100,
                    signal_sampling: float = None,
                    ground_min_mesh_size: float = 100,
                    ground_max_mesh_size: float = 100,
                    ground_min_dist: float = 100,
                    ground_max_dist: float = 100,
                    ground_sampling: float = None,
                    ground_grid_min_mesh_size: float = 100,
                    ground_grid_max_mesh_size: float = 100,
                    ground_grid_min_dist: float = 100,
                    ground_grid_max_dist: float = 100,
                    ground_grid_sampling: float = None,
                    gap_min_mesh_size: float = 100,
                    gap_max_mesh_size: float = 100,
                    gap_min_dist: float = 100,
                    gap_max_dist: float = 100,
                    gap_sampling: float = None,
                    port_min_mesh_size: float = 100,
                    port_max_mesh_size: float = 100,
                    port_min_dist: float = 100,
                    port_max_dist: float = 100,
                    port_sampling: float = None,
                    algorithm: int = 5,
                    show: bool = False,
                    gmsh_n_threads: int = 1
                    ):
    """
    Builds the model using OpenCASCADE kernel and exports the result in "simulation.msh"
    file in the specified simulation `path`

    Args:

        simulation(Simulation): The simulation to be exported
        path(Path): path of the simulation export folder
        default_mesh_size(float): Default size to be used where not defined
        signal_min_mesh_size(float): Minimum mesh size near signal region curves
        signal_max_mesh_size(float): Maximum mesh size near signal region curves
        signal_min_dist(float): Mesh size will be the minimum size until this distance
                                from the signal region curves
        signal_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the signal region curves
        signal_sampling(float): Number of points used for sampling each signal region curve
        ground_min_mesh_size(float): Minimum mesh size near ground region curves
        ground_max_mesh_size(float): Maximum mesh size near ground region curves
        ground_min_dist(float): Mesh size will be the minimum size until this distance
                                from the ground region curves
        ground_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the ground region curves
        ground_sampling(float): Number of points used for sampling each ground region curve
        ground_grid_min_mesh_size(float): Minimum mesh size near ground_grid region curves
        ground_grid_max_mesh_size(float): Maximum mesh size near ground_grid region curves
        ground_grid_min_dist(float): Mesh size will be the minimum size until this distance
                                from the ground_grid region curves
        ground_grid_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the ground_grid region curves
        ground_grid_sampling(float): Number of points used for sampling each ground_grid region curve
        gap_min_mesh_size(float): Minimum mesh size near gap region curves
        gap_max_mesh_size(float): Maximum mesh size near gap region curves
        gap_min_dist(float): Mesh size will be the minimum size until this distance
                                from the gap region curves
        gap_max_dist(float): Mesh size will grow from to the maximum size until
                                this distance from the gap region curves
        gap_sampling(float): Number of points used for sampling each gap region curve
        port_min_mesh_size(float): Minimum mesh size near port region curves
        port_max_mesh_size(float): Maximum mesh size near port region curves
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
             * port_data_gmsh(list):

                 each element contain port data that one gets from `Simulation.get_port_data` + gmsh specific data:

                    * Items from `Simulation.get_port_data`
                    * dim_tag: DimTags of the port polygons
                    * occ_bounding_box: port bounding box
                    * dim_tags: list of DimTags if the port consist of more than one (`EdgePort`)
                    * signal_dim_tag: DimTag of the face that is connected to the signal edge of the port
                    * signal_physical_name: physical name of the signal face

    """
    filepath = path.joinpath(simulation.name + '.msh')

    if gmsh_n_threads == -1:
        gmsh_n_threads = int(os.cpu_count()/2 + 0.5)  # for the moment avoid psutil.cpu_count(logical=False)

    gmsh.initialize()
    gmsh.option.setNumber("General.NumThreads", gmsh_n_threads)
    gmsh.model.add(simulation.name)

    edge_dim_tags = []
    port_data_gmsh = simulation.get_port_data()
    if simulation.wafer_stack_type == 'multiface':
        chip_distance = simulation.chip_distance
        face_ids = simulation.face_ids
        face_z_levels = [chip_distance if id == 't' else 0 for id in face_ids]
        chip_dzs = [-simulation.substrate_height if id == 'b' else simulation.substrate_height_top for id in face_ids]
        face_port_dim_tags = [[], []]
        edge_port_dim_tags = []
        for port in port_data_gmsh:
            if port['type'] == 'InternalPort':
                face_port_dim_tags[port['face']].append(add_port(port, port_min_mesh_size))
                edge_dim_tags.append(port['signal_edge_dim_tag'])
                edge_dim_tags.append(port['ground_edge_dim_tag'])
            else:
                edge_port_dim_tags.append(add_port(port, port_min_mesh_size))
                port['occ_bounding_box'] = gmsh.model.occ.getBoundingBox(*port['dim_tag'])
                port['signal_location_float'] = \
                        port['signal_location'].x, port['signal_location'].y, face_z_levels[port['face']]

        face_dim_tag_dicts = []
        for face in [0, 1]:
            face_dim_tag_dicts.append(create_face(face, face_z_levels[face], simulation,
                                                port_dim_tags=face_port_dim_tags[face]))

        chip0 = substrate(face_dim_tag_dicts[0], chip_dzs[0])
        chip1 = substrate(face_dim_tag_dicts[1], chip_dzs[1])
        vacuum = vacuum_between_faces(face_dim_tag_dicts[0]['ground'], face_dim_tag_dicts[1]['ground'])
        face0_dim_tags = face_tag_dict_to_list(face_dim_tag_dicts[0])
        face1_dim_tags = face_tag_dict_to_list(face_dim_tag_dicts[1])
        all_dim_tags = [chip0, chip1, vacuum] + (face0_dim_tags + face1_dim_tags
                                                 + face_port_dim_tags[0] + face_port_dim_tags[1] + edge_port_dim_tags)
        gmsh.model.occ.synchronize()
        out_all_dim_tags, _ = gmsh.model.occ.fragment(all_dim_tags, [])
        gmsh.model.occ.synchronize()

        gmsh.model.mesh.setSize(gmsh.model.getEntities(0), default_mesh_size)
        mesh_field_ids = []
        for face in [0, 1]:
            mesh_field_ids += set_mesh_size(face_dim_tag_dicts[face]['signal'],
                    signal_min_mesh_size, signal_max_mesh_size, signal_min_dist, signal_max_dist, signal_sampling)
            mesh_field_ids += set_mesh_size(face_dim_tag_dicts[face]['ground'],
                    ground_min_mesh_size, ground_max_mesh_size, ground_min_dist, ground_max_dist, ground_sampling)
            mesh_field_ids += set_mesh_size(face_dim_tag_dicts[face]['gap'],
                    gap_min_mesh_size, gap_max_mesh_size, gap_min_dist, gap_max_dist, gap_sampling)
            mesh_field_ids += set_mesh_size(face_dim_tag_dicts[face]['ground_grid'], ground_grid_min_mesh_size,
                    ground_grid_max_mesh_size, ground_grid_min_dist, ground_grid_max_dist, ground_grid_sampling)
            mesh_field_ids += set_mesh_size(face_port_dim_tags[face],
                    port_min_mesh_size, port_max_mesh_size, port_min_dist, port_max_dist, port_sampling)

        for face_dim_tag_dict in face_dim_tag_dicts:
            face_signal_dim_tags = list(face_dim_tag_dict['signal'])
            for port in port_data_gmsh:
                if port['type'] == 'InternalPort':
                    gmsh.model.setPhysicalName(*port['dim_tag'], 'port_' + str(port['number']))

                    for dim_tag in face_signal_dim_tags:
                        if gmsh.model.isInside(*dim_tag, port['signal_edge'][0]) and\
                           gmsh.model.isInside(*dim_tag, port['signal_edge'][1]):
                            port['signal_dim_tag'] = dim_tag
                            port['signal_physical_name'] = 'signal_' + str(port['number'])
                            gmsh.model.setPhysicalName(*dim_tag, port['signal_physical_name'])
                else:
                    port['dim_tags'] = get_entities_in_bounding_boxes([port['occ_bounding_box']], 2)
                    for i, dim_tag in enumerate(port['dim_tags']):
                        gmsh.model.setPhysicalName(*dim_tag, 'port_{}_{}'.format(port['number'], i))

                    for dim_tag in face_signal_dim_tags:
                        if gmsh.model.isInside(*dim_tag, port['signal_location_float']):
                            port['signal_dim_tag'] = dim_tag
                            port['signal_physical_name'] = 'signal_' + str(port['number'])
                            gmsh.model.setPhysicalName(*dim_tag, port['signal_physical_name'])

        gmsh.model.setPhysicalName(*chip0, 'chip_0')
        gmsh.model.setPhysicalName(*chip1, 'chip_1')
        gmsh.model.setPhysicalName(*vacuum, 'vacuum')

    # Find all the extreme boundaries and add physical names to them
    bbox_all = bounding_box_from_dim_tags(out_all_dim_tags)
    bbox_all_sides = get_bbox_sides_as_bboxes(bbox_all)
    for side_name in ['xmin', 'ymin', 'zmin', 'xmax', 'ymax', 'zmax']:
        bbox_all_dim_tags = get_entities_in_bounding_boxes([bbox_all_sides[side_name]], 2)
        for i, dim_tag in enumerate(bbox_all_dim_tags):
            gmsh.model.setPhysicalName(*dim_tag, '{}_{}'.format(side_name, i))

    simulation.ground_names = []
    for i, dim_tag in enumerate(face_dim_tag_dicts[0]['ground'] + face_dim_tag_dicts[1]['ground']):
        ground_name = 'ground_{}'.format(i)
        gmsh.model.setPhysicalName(*dim_tag, ground_name)
        simulation.ground_names.append(ground_name)

    background_field_id = gmsh.model.mesh.field.add("Min")
    gmsh.model.mesh.field.setNumbers(background_field_id, "FieldsList", mesh_field_ids)
    gmsh.model.mesh.field.setAsBackgroundMesh(background_field_id)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.Algorithm", algorithm)
    gmsh.option.setNumber("Mesh.Algorithm3D", 10) # HTX
    gmsh.option.setNumber("Mesh.ToleranceInitialDelaunay", 1e-14)
    gmsh.option.setNumber("Mesh.MaxNumThreads1D", gmsh_n_threads)
    gmsh.option.setNumber("Mesh.MaxNumThreads2D", gmsh_n_threads)
    gmsh.option.setNumber("Mesh.MaxNumThreads3D", gmsh_n_threads)

    gmsh.model.mesh.generate(3)
    gmsh.write(str(filepath))
    if show:
        gmsh.fltk.run()
    gmsh.finalize()

    return filepath, port_data_gmsh
