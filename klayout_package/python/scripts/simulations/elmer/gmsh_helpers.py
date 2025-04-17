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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).
from pathlib import Path
from typing import Any, Sequence, Iterable
import gmsh
import numpy as np

try:
    import pya
except ImportError:
    import klayout.db as pya

# prefix to use in case a layer name starts with number or other special character
MESH_LAYER_PREFIX = "elmer_prefix_"

# type alias for dimtag
DimTag = tuple[int, int]


def get_metal_layers(layers):
    return {k: v for k, v in layers.items() if "excitation" in v}


def get_elmer_layers(layers):
    """Prefixes dict keys if starting with number. Returns new modified dict"""
    return {apply_elmer_layer_prefix(k): v for k, v in layers.items()}


def apply_elmer_layer_prefix(name):
    return name if name[0].isalpha() else MESH_LAYER_PREFIX + name


def produce_mesh(json_data: dict[str, Any], msh_file: Path) -> None:
    """
    Produces mesh and optionally runs the Gmsh GUI

    Args:
        json_data: all the model data produced by `export_elmer_json`
        msh_file: mesh file name
    """
    if Path(msh_file).exists():
        print(f"Reusing existing mesh from {str(msh_file)}")
        return

    # Initialize gmsh
    gmsh.initialize()

    # Read geometry from gds file
    layout = pya.Layout()
    layout.read(json_data["gds_file"])
    cell = layout.top_cell()

    # Limiting boundary box (use variable 'box' if it is given. Otherwise, use bounding bo of the geometry.)
    if "box" in json_data:
        bbox = pya.DBox(
            json_data["box"]["p1"]["x"],
            json_data["box"]["p1"]["y"],
            json_data["box"]["p2"]["x"],
            json_data["box"]["p2"]["y"],
        ).to_itype(layout.dbu)
    else:
        bbox = cell.bbox()

    # Create mesh using geometries in gds file
    gmsh.model.add("3D-mesh")
    dim_tags = {}
    layers = json_data["layers"]
    for name, data in layers.items():
        # Get layer region
        if "layer" in data:
            layer_num = data["layer"]
            reg = pya.Region(cell.shapes(layout.layer(layer_num, 0))) & bbox
            if reg.is_empty():
                print(f"WARNING: encountered empty layer in Gmsh: {name}")
        else:
            reg = pya.Region(bbox)

        # Convert layer region to polygons
        layer_dim_tags = []
        layer_edge_ids = []
        for simple_poly in reg.each():
            poly = separated_hull_and_holes(simple_poly)
            hull_point_coordinates = [
                (point.x * layout.dbu, point.y * layout.dbu, 0) for point in poly.each_point_hull()
            ]
            hull_plane_surface_id, hull_edge_ids = add_polygon(hull_point_coordinates)
            layer_edge_ids += hull_edge_ids
            hull_dim_tag = (2, hull_plane_surface_id)
            hole_dim_tags = []
            for hole in range(poly.holes()):
                hole_point_coordinates = [
                    (point.x * layout.dbu, point.y * layout.dbu, 0) for point in poly.each_point_hole(hole)
                ]
                hole_plane_surface_id, hole_edge_ids = add_polygon(hole_point_coordinates)
                layer_edge_ids += hole_edge_ids
                hole_dim_tags.append((2, hole_plane_surface_id))
            if hole_dim_tags:
                layer_dim_tags += gmsh.model.occ.cut([hull_dim_tag], hole_dim_tags)[0]
            else:
                layer_dim_tags.append(hull_dim_tag)

        # Move to correct height
        z = data.get("z", 0.0)
        if z != 0.0:
            gmsh.model.occ.translate(layer_dim_tags, 0, 0, z)

        # Thicken sheet
        thickness = data.get("thickness", 0.0)
        if thickness != 0.0:
            extruded = gmsh.model.occ.extrude(layer_dim_tags, 0, 0, thickness)
            layer_dim_tags = [(d, t) for d, t in extruded if d == 3]

        # Store layer into dim_tags
        dim_tags[name] = layer_dim_tags

    # Add ports for wave equation simulations
    if json_data["tool"] == "wave_equation":
        for port in json_data["ports"]:
            if "polygon" in port:
                # add port polygon and store its dim_tag
                surface_id, _ = add_polygon(port["polygon"])
                dim_tags[f'port_{port["number"]}'] = [(2, surface_id)]

    # Subtract layers
    for name, data in layers.items():
        subtract = data.get("subtract", [])
        if subtract:
            tool_dim_tags = [t for n in subtract for t in dim_tags[n]]
            dim_tags[name] = gmsh.model.occ.cut(dim_tags[name], tool_dim_tags, removeTool=False)[0]
            gmsh.model.occ.synchronize()

    # Call fragment and get updated dim_tags as new_tags. Then synchronize.
    all_dim_tags = [tag for tags in dim_tags.values() for tag in tags]
    _, dim_tags_map_imp = gmsh.model.occ.fragment(all_dim_tags, [], removeTool=False)
    dim_tags_map = dict(zip(all_dim_tags, dim_tags_map_imp))
    new_tags = {
        name: [new_tag for old_tag in tags for new_tag in dim_tags_map[old_tag]] for name, tags in dim_tags.items()
    }
    gmsh.model.occ.synchronize()

    # Refine mesh
    mesh_size = json_data.get("mesh_size", {})
    mesh_global_max_size = mesh_size.pop("global_max", bbox.perimeter())
    mesh_field_ids = []
    for name, size in mesh_size.items():
        intersection: set[tuple[int, int]] = set()
        split_names = name.split("&")
        if all(n in new_tags for n in split_names):
            for sname in split_names:
                family = get_recursive_children(new_tags[sname]).union(new_tags[sname])
                intersection = intersection.intersection(family) if intersection else family

            mesh_field_ids += set_mesh_size_field(
                list(intersection - get_recursive_children(intersection)),
                mesh_global_max_size,
                *(size if isinstance(size, list) else [size]),
            )
        else:
            print(f'WARNING: No layers corresponding to mesh_size keys "{split_names}" found')

    # Set meshing options
    workflow = json_data.get("workflow", {})
    n_threads_dict = workflow["sbatch_parameters"] if "sbatch_parameters" in workflow else workflow
    gmsh_n_threads = int(n_threads_dict.get("gmsh_n_threads", 1))
    set_meshing_options(mesh_field_ids, mesh_global_max_size, gmsh_n_threads)

    # Remove layers without material
    for name, data in layers.items():
        if name in new_tags and data.get("material") is None:
            del new_tags[name]

    # Add excitation boundaries and remove those from original metal layers
    if json_data["tool"] != "epr_3d":
        metal_layers = get_metal_layers(layers)
        excitations = {d["excitation"] for d in metal_layers.values()}
        for excitation in excitations:
            excitation_names = [n for n, d in metal_layers.items() if d["excitation"] == excitation and n in new_tags]
            excitation_dts = [dt for n in excitation_names for dt in new_tags[n]]
            excitation_with_boundary = get_recursive_children(excitation_dts).union(excitation_dts)
            new_tags[f"excitation_{excitation}_boundary"] = [(d, t) for d, t in excitation_with_boundary if d == 2]
            for n in excitation_names:
                new_tags[n] = [(d, t) for d, t in new_tags[n] if d == 3]

    # Modify new_tags for wave equation simulations
    if json_data["tool"] == "wave_equation":
        # Split edge ports into parts by intersecting layers
        edge_ports_dts = set()
        for port in json_data["ports"]:
            port_name = f'port_{port["number"]}'
            if port_name in new_tags and port["type"] == "EdgePort":
                port_dts = set(new_tags[port_name])
                edge_ports_dts.update(port_dts)
                for name, dts in list(new_tags.items()):
                    part_dts = [(d, t) for d, t in port_dts.intersection(get_recursive_children(dts)) if d == 2]
                    if part_dts:
                        new_tags[f"{port_name}_{name}"] = part_dts
                del new_tags[port_name]

        # Set domain boundary as ground
        solid_dts = [(d, t) for dts in new_tags.values() for d, t in dts if d == 3]
        face_dts = [(d, t) for dt in solid_dts for d, t in get_recursive_children([dt]) if d == 2]
        new_tags["domain_boundary"] = [d for d in face_dts if face_dts.count(d) == 1 and d not in edge_ports_dts]

    # Create physical groups from each object in new_tags
    for name, dts in new_tags.items():
        if dts:
            gmsh.model.addPhysicalGroup(
                max(d for d, _ in dts), [t for _, t in dts], name=apply_elmer_layer_prefix(name)
            )

    # Generate and save mesh
    gmsh.model.mesh.generate(1)
    gmsh.model.mesh.generate(2)
    gmsh.model.mesh.generate(3)

    optimize_mesh(json_data.get("mesh_optimizer"))
    gmsh.write(str(msh_file))

    # Open mesh viewer
    if workflow.get("run_gmsh_gui", False):
        gmsh.fltk.run()

    gmsh.finalize()


def optimize_mesh(mesh_optimizer: dict | None) -> None:
    """Optimize the mesh if the mesh_optimizer is a dictionary. Ignore mesh optimization if mesh_optimizer is None."""
    if mesh_optimizer is None:
        return
    try:
        # Try optimizing with Netgen as the default method
        gmsh.model.mesh.optimize(**{"method": "Netgen", **mesh_optimizer})
    except Exception as error:  # pylint: disable=broad-except
        print(f"WARNING: Mesh optimization failed: {error}")


def coord_dist(coord1: Sequence[float], coord2: Sequence[float]) -> float:
    """
    Returns the distance between two points.

    Args:
        coord1: coordinates (x, y, z) of point 1.
        coord2: coordinates (x, y, z) of point 2.

    Returns:
        distance between point 1 and 2
    """
    return float(np.linalg.norm(np.array(coord1) - np.array(coord2)))


def add_polygon(point_coordinates: Sequence[Sequence[float]], mesh_size: float = 0) -> tuple[int, list[int]]:
    """
    Adds the geometry entities in the OpenCASCADE model for generating a polygon and keeps track of all the entities.
    Returns the geometry entity id.

    Args:
        point_coordinates: list of point coordinates that frame the polygon
        mesh_size: mesh element size, default=0

    Returns:
        entity id of the polygon and list of entity ids of edge lines
    """
    points = [gmsh.model.occ.addPoint(*coord, mesh_size) for coord in point_coordinates]
    lines = [gmsh.model.occ.addLine(points[i - 1], points[i]) for i in range(1, len(points))]
    lines.append(gmsh.model.occ.addLine(points[-1], points[0]))
    loops = [gmsh.model.occ.addCurveLoop(lines)]
    return gmsh.model.occ.addPlaneSurface(loops), lines


def separated_hull_and_holes(polygon: pya.Polygon | pya.SimplePolygon) -> pya.Polygon | pya.SimplePolygon:
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


def set_mesh_size(
    dim_tags: Sequence[DimTag],
    min_mesh_size: float,
    max_mesh_size: float,
    dist_min: float,
    dist_max: float,
    sampling: int | None = None,
) -> list[int]:
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

        dim_tags(list(int, int)): a list of entity dim_tags:
            dimTag (as called in Gmsh) is a tuple of

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity

        min_mesh_size: minimum mesh size
        max_mesh_size: maximum mesh size
        dist_min: distance to which the minimum mesh size is used
        dist_max: distance after which the maximum mesh size is used
        sampling: number of sampling points when computing the distance from the curve. The default value is None.
                  In that case, the value is determined by 1.5 times the maximum reachable distance in the bounding box
                  of the entity (curve) divided by the minimum mesh size. The sampling value is forced to be at least 3
                  to avoid bug in line-based mesh refinement. At the moment there is no obvious way to implement
                  curve_length/min_mesh_size type of algorithm.

    Returns:
        list of the threshold field ids that were defined in this function
    """
    mesh_field_ids = []
    for dim_tag in dim_tags:
        if dim_tag[0] > 2:
            dim_tags += gmsh.model.getBoundary([dim_tag], combined=False, oriented=False, recursive=False)
            continue
        tag_distance_field = gmsh.model.mesh.field.add("Distance")
        key_dict = {0: "PointsList", 1: "CurvesList", 2: "SurfacesList"}
        gmsh.model.mesh.field.setNumbers(tag_distance_field, key_dict[dim_tag[0]], [dim_tag[1]])

        # Sample the object with points
        if dim_tag[0] > 0:
            if sampling is None:
                bbox = gmsh.model.occ.getBoundingBox(*dim_tag)
                bbox_diam = coord_dist(bbox[0:3], bbox[3:6])  # diameter of bounding box
                final_sampling = np.ceil(1.5 * bbox_diam / min_mesh_size)
            else:
                final_sampling = sampling
            gmsh.model.mesh.field.setNumber(tag_distance_field, "Sampling", max(3, final_sampling))

        mesh_field_id = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(mesh_field_id, "InField", tag_distance_field)
        gmsh.model.mesh.field.setNumber(mesh_field_id, "SizeMin", min_mesh_size)
        gmsh.model.mesh.field.setNumber(mesh_field_id, "SizeMax", max_mesh_size)
        gmsh.model.mesh.field.setNumber(mesh_field_id, "DistMin", dist_min)
        gmsh.model.mesh.field.setNumber(mesh_field_id, "DistMax", dist_max)
        mesh_field_ids.append(mesh_field_id)

    return mesh_field_ids


def set_mesh_size_field(
    dim_tags: Sequence[DimTag],
    global_max: float,
    size: float,
    distance: float | None = None,
    slope: float = 1.0,
) -> list[int]:
    """
    Set the maximal mesh element length in the neighbourhood of the entities given in `dim_tags`. The element size near
    the entities is determined by 'size', 'expansion_dist', and 'expansion_rate'. Further away from the entities the
    element size gradually increases to `global_max`. The maximal mesh elements size as function of distance 'x' from
    the entity is given by min(global_max, size + max(0, x - distance) * slope).

    Args:

        dim_tags: a list of entity dim_tags:
            dimTag (as called in Gmsh) is a tuple of

                * dimension(int): the dimension of the entity (0=point, 1=line, 2=surface, 3=volume)
                * tag(int): the id of the entity

        global_max: global maximal mesh element length
        size: the maximal mesh element length inside at the entity and its expansion
        distance: expansion distance in which the maximal mesh element length is constant (default=size)
        slope: the slope of the increase in the maximal mesh element length outside the entity

    Returns:
        list of the threshold field ids that were defined in this function
    """
    dist = size if distance is None else distance
    return set_mesh_size(dim_tags, size, global_max, dist, dist + (global_max - size) / slope)


def get_recursive_children(dim_tags: Iterable[DimTag]) -> set[DimTag]:
    """Returns children and all recursive grand children of given parent entities

    Args:
        dim_tags: list of dim tags of parent entities

    Returns:
        set of dim tags of all children and recursive grand children
    """
    children: set[DimTag] = set()
    while dim_tags:
        dim_tags = gmsh.model.getBoundary(list(dim_tags), combined=False, oriented=False, recursive=False)
        children = children.union(dim_tags)
    return children


def set_meshing_options(mesh_field_ids: list[int], max_size: float, n_threads: int) -> None:
    """Setup meshing options including mesh size fields and number of parallel threads.

    Args:
        mesh_field_ids: list of the threshold field ids that are given by set_mesh_size function
        max_size: global maximal mesh element length
        n_threads: Number of threads to be used in mesh generation
    """
    background_field_id = gmsh.model.mesh.field.add("Min")
    gmsh.model.mesh.field.setNumbers(background_field_id, "FieldsList", mesh_field_ids)
    gmsh.model.mesh.field.setAsBackgroundMesh(background_field_id)
    gmsh.option.setNumber("Mesh.MeshSizeMax", max_size)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.Algorithm", 5)
    gmsh.option.setNumber("Mesh.Algorithm3D", 1)  # 1: Delaunay, 10: HXT
    gmsh.option.setNumber("Mesh.ToleranceInitialDelaunay", 1e-16)
    gmsh.option.setNumber("General.NumThreads", n_threads)
    gmsh.option.setNumber("Mesh.MaxNumThreads1D", n_threads)
    gmsh.option.setNumber("Mesh.MaxNumThreads2D", n_threads)
    gmsh.option.setNumber("Mesh.MaxNumThreads3D", n_threads)
