# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
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


import ast
import re
import logging
from itertools import product
from math import ceil
from typing import Callable, Sequence
from kqcircuits.defaults import default_cross_section_profile
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.cross_section.cross_section_profile import CrossSectionProfile
from kqcircuits.simulations.cross_section_simulation import CrossSectionSimulation
from kqcircuits.simulations.simulation import Simulation, to_1d_list


def _oxidise_layers(simulation: Simulation, ma_thickness: float, ms_thickness: float, sa_thickness: float) -> None:
    """Take the cross section geometry and add oxide layers between substrate, metal and vacuum.
    Will etch away substrate and metals to insert oxide geometry.
    """
    substrate_layers = [
        layer
        for layer in simulation.layout.layer_infos()
        if layer.name.startswith("substrate_") or layer.name == "substrate"
    ]
    substrate = _combine_region_from_layers(simulation.cell, substrate_layers)
    used_faces = []
    for face_group in simulation.get_parameters()["face_stack"]:
        if isinstance(face_group, list):
            used_faces.extend(face_group)
        else:
            used_faces.append(face_group)
    metal_layers = [
        layer
        for layer in simulation.layout.layer_infos()
        if layer.name in [f"{f}_{l}" for f, l in product(used_faces, ["ground", "signal"])]
    ]
    for f in used_faces:
        metal_layers += [layer for layer in simulation.layout.layer_infos() if layer.name.startswith(f"{f}_signal_")]
    metals = _combine_region_from_layers(simulation.cell, metal_layers)
    metal_edges = metals.edges()
    substrate_edges = substrate.edges()

    ma_edges = []
    for metal_edge in metal_edges:
        if not _edge_on_the_box_border(metal_edge.to_dtype(simulation.layout.dbu), simulation.box):
            ma_edges.extend(_remove_shared_points(metal_edge, substrate_edges, True))

    sa_edges, ms_edges = [], []
    for substrate_edge in substrate_edges:
        if not _edge_on_the_box_border(substrate_edge.to_dtype(simulation.layout.dbu), simulation.box):
            sa_edges.extend(_remove_shared_points(substrate_edge, metal_edges, True))
            ms_edges.extend(_remove_shared_points(substrate_edge, sa_edges, False))

    ma_layer = _thicken_edges(simulation, ma_edges, ma_thickness, False)
    ms_layer = _thicken_edges(simulation, ms_edges, ms_thickness, False)
    sa_layer = _thicken_edges(simulation, sa_edges, sa_thickness, False)
    ma_layer -= ms_layer  # MS layer takes precedence over both MA and SA layers
    sa_layer -= ms_layer
    sa_layer -= ma_layer  # MA layer takes precedence over SA layer

    # Etch and replace substrate layer regions
    if ms_thickness > 0.0 or sa_thickness > 0.0:
        for substrate_layer in substrate_layers:
            substrate_region = pya.Region(simulation.cell.shapes(simulation.layout.layer(substrate_layer)))
            simulation.cell.shapes(simulation.layout.layer(substrate_layer)).clear()
            simulation.cell.shapes(simulation.layout.layer(substrate_layer)).insert(
                substrate_region - ms_layer - sa_layer
            )

    # Etch and replace metal layer regions
    if ma_thickness > 0.0:
        for metal_layer in metal_layers:
            metal_region = pya.Region(simulation.cell.shapes(simulation.layout.layer(metal_layer)))
            simulation.cell.shapes(simulation.layout.layer(metal_layer)).clear()
            simulation.cell.shapes(simulation.layout.layer(metal_layer)).insert(metal_region - ma_layer)

    if ma_thickness > 0.0:
        simulation.cell.shapes(simulation.get_sim_layer("ma_layer")).insert(ma_layer)
    if ms_thickness > 0.0:
        simulation.cell.shapes(simulation.get_sim_layer("ms_layer")).insert(ms_layer)
    if sa_thickness > 0.0:
        simulation.cell.shapes(simulation.get_sim_layer("sa_layer")).insert(sa_layer)


def _check_metal_heights(simulation: Simulation) -> None:
    for i, h in enumerate(to_1d_list(simulation.metal_height), 1):
        if h == 0:
            logging.warning(f"Encountered zero metal height in CrossSectionSimulation (face {i}).")


def create_cross_sections_from_simulations(
    simulations: list[Simulation],
    cuts: tuple[pya.DPoint, pya.DPoint] | list[tuple[pya.DPoint, pya.DPoint]],
    profile: CrossSectionProfile | Callable[[Simulation], CrossSectionProfile] = default_cross_section_profile,
    post_processing_function: None | Callable[[CrossSectionSimulation], None] = None,
    oxidise_layers_function: Callable[[CrossSectionSimulation, float, float, float], None] = _oxidise_layers,
    ma_permittivity: float = 0,
    ms_permittivity: float = 0,
    sa_permittivity: float = 0,
    ma_thickness: float = 0,
    ms_thickness: float = 0,
    sa_thickness: float = 0,
    vertical_cull: tuple[float, float] | None = None,
    mer_box: pya.DBox | list[pya.DBox] | None = None,
    london_penetration_depth: float | list = 0,
    magnification_order: int = 0,
    layout: pya.Layout | None = None,
) -> list[Simulation]:
    """Create cross-sections of all simulation geometries in the list.
    Will set 'box' and 'cell' parameters according to the produced cross-section geometry data.

    Args:
        simulations: List of Simulation objects, usually produced by a sweep
        cuts: 1. A tuple (p1, p2), where p1 and p2 are endpoints of a cross-section cut or
              2. a list of such tuples such that each Simulation object gets an individual cut
        profile: CrossSectionProfile object that defines vertical level values for each layer.
            If not set, will use ``default_cross_section_profile``
        post_processing_function: Additional function to post-process the cross-section geometry.
            Defaults to None, in which case no post-processing is performed.
            The function takes a CrossSectionSimulation object as argument
        oxidise_layers_function: Set this argument if you have a custom way of introducing
            oxidization layers to the cross-section metal deposits and substrate.
            See expected function signature from typehints
        ma_permittivity: Permittivity of metal–vacuum (air) interface
        ms_permittivity: Permittivity of metal–substrate interface
        sa_permittivity: Permittivity of substrate–vacuum (air) interface
        ma_thickness: Thickness of metal–vacuum (air) interface
        ms_thickness: Thickness of metal–substrate interface
        sa_thickness: Thickness of substrate–vacuum (air) interface
        vertical_cull: Tuple of two y-coordinates, will cull all geometry not in-between the y-coordinates.
            None by default, which means all geometry is retained.
        mer_box: If set as pya.DBox, will create a specified box as metal edge region,
            meaning that the geometry inside the region are separated into different layers with '_mer' suffix
        london_penetration_depth: London penetration depth of the superconducting material
        magnification_order: Increase magnification of simulation geometry to accomodate more precise spacial units.
            0 =   no magnification with 1e-3 dbu
            1 =  10x magnification with 1e-4 dbu
            2 = 100x magnification with 1e-5 dbu etc
            Consider setting non-zero value when using oxide layers with < 1e-3 layer thickness
        layout: predefined layout for the cross-section simulation. If not set, will create new layout.

    Returns:
        List of CrossSectionSimulation objects for each Simulation object in simulations
    """
    if isinstance(cuts, tuple):
        cuts = [cuts] * len(simulations)
    cuts = [tuple(c if isinstance(c, pya.DPoint) else c.to_p() for c in cut) for cut in cuts]
    if len(simulations) != len(cuts):
        raise ValueError("Number of cuts did not match the number of simulations")
    if any(len(simulation.get_parameters()["face_stack"]) not in (1, 2) for simulation in simulations):
        raise ValueError("Only single face and flip chip cross section simulations currently supported")
    if not layout:
        layout = pya.Layout()

    # Increase database unit accuracy in layout if bigger magnification_order set
    if magnification_order > 0:
        layout.dbu = 10 ** (-3 - magnification_order)

    # Collect cross section simulation sweeps
    return [
        _construct_cross_section_simulation(
            layout,
            cut,
            simulation,
            post_processing_function,
            oxidise_layers_function,
            ma_permittivity,
            ms_permittivity,
            sa_permittivity,
            ma_thickness,
            ms_thickness,
            sa_thickness,
            vertical_cull,
            mer_box,
            london_penetration_depth,
            profile,
        )
        for simulation, cut in zip(simulations, cuts)
    ]


def find_layer_by_name(layer_name: str, layout: pya.Layout) -> pya.LayerInfo:
    """Returns layerinfo if there already is a layer by layer_name in layout. None if no such layer exists"""
    for l in layout.layer_infos():
        if l.datatype == 0 and layer_name == l.name:
            return l
    return None


def free_layer_slots(layout: pya.Layout):
    """A generator of available layer slots"""
    layer_index = 0
    reserved_layer_ids = [l.layer for l in layout.layer_infos() if l.datatype == 0]
    while True:
        layer_index += 1
        if layer_index in reserved_layer_ids:
            continue
        yield layer_index


def visualise_cross_section_cut_on_original_layout(
    simulations: list[Simulation],
    cuts: tuple[pya.DPoint, pya.DPoint] | list[tuple[pya.DPoint, pya.DPoint]],
    cut_label: str = "cut",
    width_ratio: float = 0.0,
) -> None:
    """Visualise requested cross section cuts on the original simulation layout.

    Will add a rectangle between two points of the cut, and two text points into layer "cross_section_cut"::

        * f"{cut_label}_1" representing the left side of the cross section simulation
        * f"{cut_label}_2" representing the right side of the cross section simulation

    In case the export takes cross sections for one simulation multiple times, this function
    can be called on same simulation sweep multiple times so that multiple cuts can be visualised
    in the same layout. In such case it is recommended to differentiate the cuts using `cut_label`.

    Args:
        simulations: list of simulations from which cross sections are taken. After this call these simulations
            will be modified to include the visualised cuts.
        cuts: 1. A tuple (p1, p2), where p1 and p2 are endpoints of a cross-section cut or
              2. a list of such tuples such that each Simulation object gets an individual cut
        cut_label: prefix of the two text points shown for the cut
        width_ratio: rectangles visualising cuts will have a width of length of the cut multiplied by width_ratio.
            By default will set 0 width line, which is visualised in KLayout.
    """
    if isinstance(cuts, tuple):
        cuts = [cuts] * len(simulations)
    cuts = [tuple(c if isinstance(c, pya.DPoint) else c.to_p() for c in cut) for cut in cuts]
    if len(simulations) != len(cuts):
        raise ValueError("Number of cuts did not match the number of simulations")
    for simulation, cut in zip(simulations, cuts):
        cut_length = (cut[1] - cut[0]).length()
        marker_path = pya.DPath(cut, cut_length * width_ratio).to_itype(simulation.layout.dbu)
        # Prevent .OAS saving errors by rounding integer value of path width to even value
        marker_path.width -= marker_path.width % 2
        marker = pya.Region(marker_path)
        simulation.visualise_region(marker, cut_label, "cross_section_cut", cut)


def _combine_region_from_layers(cell: pya.Cell, layers: Sequence[pya.LayerInfo]) -> pya.Region:
    """Produce a region combined from regions in layers list"""
    region = pya.Region()
    layout = cell.layout()
    for layer in layers:
        region += pya.Region(cell.shapes(layout.layer(layer)))
    return region


def _edge_on_the_box_border(edge: pya.DEdge, box: pya.DBox) -> bool:
    """True if edge is exactly at the rim of the box"""
    return (
        (edge.x1 == box.p1.x and edge.x2 == box.p1.x)
        or (edge.x1 == box.p2.x and edge.x2 == box.p2.x)
        or (edge.y1 == box.p1.y and edge.y2 == box.p1.y)
        or (edge.y1 == box.p2.y and edge.y2 == box.p2.y)
    )


def _cut_edge(target_edge: pya.Edge, source_edge: pya.Edge, extra_edges: Sequence[pya.Edge]) -> pya.Edge:
    """Cut an end of the target_edge with source_edge.

    If source_edge leaves behind two ends of the target_edge,
    the second edge bit is stored in extra_edges.

    Each edge should be in integer form (pya.Edge)
    """
    # Copy target_edge to not modify the original edge instance
    result_edge = pya.Edge(target_edge.p1.x, target_edge.p1.y, target_edge.p2.x, target_edge.p2.y)
    if result_edge.contains_excl(source_edge.p1):
        if result_edge.contains_excl(source_edge.p2) and source_edge.p2 != result_edge.p2:
            extra_edges.append(pya.Edge(source_edge.p2, result_edge.p2))
        result_edge.p2 = source_edge.p1
    elif result_edge.contains_excl(source_edge.p2):
        result_edge.p1 = source_edge.p2
    return result_edge


def _remove_shared_points(
    target_edge: pya.Edge, acting_edges: Sequence[pya.Edge], is_adjacent: bool
) -> Sequence[pya.Edge]:
    """Remove all points shared by target_edge and edges in acting_edges

    Returns a set of continuous edges that are not contained by acting_edges.
    Set is_adjacent to True if the shape of acting_edges is adjacent to the shape
    from which target_edge was taken. Set to False if the shapes are on top of eah other.

    Each edge should be in integer form (pya.Edge)
    """
    edge_bits = [target_edge]
    for acting_edge in acting_edges:
        # Set acting_edge to point to same direction as target_edge
        if is_adjacent:
            acting_edge = acting_edge.swapped_points()
        # Consider edges if they share points, which means they are parallel and have same displacement
        if acting_edge.is_parallel(target_edge):
            # Remove edge bits if they are completely covered by acting_edge
            edge_bits = [e for e in edge_bits if not (acting_edge.contains(e.p1) and acting_edge.contains(e.p2))]
            extra_edge_bits = []  # Collect extra edge bits here
            edge_bits = [_cut_edge(e, acting_edge, extra_edge_bits) for e in edge_bits]
            edge_bits.extend(extra_edge_bits)  # Add extra bits
            edge_bits = [e for e in edge_bits if e.p1 != e.p2]  # Remove zero length edge bits
    return edge_bits


def _normal_of_edge(simulation: Simulation, p1: pya.Point, p2: pya.Point, scale: float) -> pya.Point:
    """Returns a normal of edge p1->p2.

    If (p1, p2) are in same polygon in given order,
    the returned normal will stick out of polygon.
    The magnitude of the normal will be set to `scale`.

    p1, p2 are pya.Point (integer) objects, however
    scale is scaled according to pya.DPoint domain.
    """
    edge_dir = p2 - p1
    normal = pya.Point(-edge_dir.y, edge_dir.x)
    dnormal = normal.to_dtype(simulation.layout.dbu)
    return (dnormal * (scale / dnormal.abs())).to_itype(simulation.layout.dbu)


def _thicken_edges(simulation: Simulation, edges: Sequence[pya.Edge], thickness: float, grow: bool) -> pya.Region:
    """Take edges and add thickness to produce a region.

    Set grow to True to grow the region outward, False to grow inward
    Each edge should be in integer form (pya.Edge)
    """
    if thickness <= 0.0:  # Don't do anything if no thickness
        return pya.Region()
    # Construct a graph from the edges to find paths
    # Start by finding start points for paths
    start_points = [e.p1 for e in edges if e.p1 not in [e2.p2 for e2 in edges]]
    path_graph = {}
    for edge in edges:
        path_graph[edge.p1] = edge

    result_region = pya.Region()
    processed_edges = []
    # Take each start_point and follow the path until the end
    for current_point in start_points:
        inner_path = [current_point]
        normals = []
        while True:
            current_edge = path_graph[current_point]
            processed_edges.append(current_edge)
            # First collect path points for the region polygon
            inner_path.append(current_edge.p2)
            # Also collect their normals
            normals.append(
                (1.0 if grow else -1.0) * _normal_of_edge(simulation, current_edge.p1, current_edge.p2, thickness)
            )
            # At the end point, terminate
            if current_edge.p2 not in path_graph:
                break
            # Otherwise proceed to next point in path
            current_point = current_edge.p2
        # Connect to the second layer of the path to add thickness
        outer_path = [inner_path[-1] + normals[-1]]
        # Backtrack the path for the second layer of the polygon
        for idx in range(len(normals) - 1, 0, -1):
            normal_sum = normals[idx] + normals[idx - 1]  # Sum normals of surrounding edges of the point
            outer_path.append(inner_path[idx] + normal_sum)
        outer_path.append(inner_path[0] + normals[0])
        result_region += pya.Region(pya.Polygon(inner_path + outer_path))

    # Handle edges in loops separately
    loop_edges = [e for e in edges if e not in processed_edges]
    processed_edges = []
    for start_edge in loop_edges:
        if start_edge in processed_edges:
            continue
        current_edge = start_edge
        loop = [current_edge.p1]
        while current_edge.p2 != start_edge.p1:
            loop.append(current_edge.p2)
            current_edge = path_graph[current_edge.p2]
            processed_edges.append(current_edge)
        loop_poly = pya.Polygon(loop)
        if grow:
            # We are growing on the rim of the loop. Take the rim, then copy the
            # shrinked rim, then subtract shrinked rim from original rim.
            # To shrink, we have to rely on normals
            loop_sized = []
            for i, p in enumerate(loop):
                j = 0 if i + 1 == len(loop) else i + 1
                normal_next = _normal_of_edge(simulation, p, loop[j], thickness)
                normal_prev = _normal_of_edge(simulation, loop[i - 1], p, thickness)
                loop_sized.append(p + normal_prev + normal_next)
            loop_sized = pya.Polygon(loop_sized)
        else:
            # We are "growing" out of the rim of the loop. Take the rim,
            # then copy the magnified rim, subtracting original rim from
            # the magnified rim. We can just use `sized` method.
            loop_sized = loop_poly.to_dtype(simulation.layout.dbu)
            loop_sized = loop_sized.sized(thickness)
            loop_sized = loop_sized.to_itype(simulation.layout.dbu)
        if grow:
            result_region += pya.Region(loop_poly) - pya.Region(loop_sized)
        else:
            result_region += pya.Region(loop_sized) - pya.Region(loop_poly)
    return result_region


def _iterate_layers_and_modify_region(
    cell: pya.Cell, process_region: Callable[[pya.Region, pya.LayerInfo], pya.Region]
) -> None:
    """Iterates over all (non-empty) layers in cell
    and replaces the region in that layer with process_region(region, layer)
    """
    for layer in cell.layout().layer_infos():
        region = pya.Region(cell.shapes(cell.layout().layer(layer)))
        if region.is_empty():
            continue
        cell.shapes(cell.layout().layer(layer)).clear()
        cell.shapes(cell.layout().layer(layer)).insert(process_region(region, layer))


def _construct_cross_section_simulation(
    layout: pya.Layout,
    cut: tuple[pya.DPoint, pya.DPoint],
    simulation: Simulation,
    post_processing_function: None | Callable[[CrossSectionSimulation], None],
    oxidise_layers_function: Callable[[CrossSectionSimulation, float, float, float], None],
    ma_permittivity: float,
    ms_permittivity: float,
    sa_permittivity: float,
    ma_thickness: float,
    ms_thickness: float,
    sa_thickness: float,
    vertical_cull: None | tuple[float, float],
    mer_box: None | pya.DBox | list[pya.DBox],
    london_penetration_depth: float | list,
    profile: CrossSectionProfile,
) -> CrossSectionSimulation:
    """Produce CrossSectionSimulation object"""
    _check_metal_heights(simulation)
    if callable(profile):
        cross_section_profile = profile(simulation)
    else:
        cross_section_profile = profile
    intersections_by_layer = take_cross_section(simulation.cell, cut, cross_section_profile)
    xsection_cell = produce_intersection_shapes(simulation, layout, intersections_by_layer, cross_section_profile)
    xsection_parameters = simulation.get_parameters()
    xsection_parameters["london_penetration_depth"] = london_penetration_depth
    cell_bbox = xsection_cell.dbbox()
    # Disabled for single face and flip-chip cases
    # cell_bbox.p1 -= pya.DPoint(0, xsection_parameters['lower_box_height'])
    if len(xsection_parameters["face_stack"]) == 1:
        cell_bbox.p2 += pya.DPoint(0, xsection_parameters["upper_box_height"])
    if vertical_cull is not None:
        cell_bbox.p1 = pya.DPoint(cell_bbox.p1.x, min(vertical_cull))
        cell_bbox.p2 = pya.DPoint(cell_bbox.p2.x, max(vertical_cull))
    xsection_parameters["box"] = cell_bbox
    xsection_parameters["cell"] = xsection_cell
    xsection_simulation = CrossSectionSimulation(layout, **xsection_parameters, ignore_process_layers=True)
    # Keep all parameters given in simulations for JSON
    for k, v in xsection_parameters.items():
        setattr(xsection_simulation, k, v)
    xsection_simulation.xsection_source_class = type(simulation)
    xsection_simulation.register_cell_layers_as_sim_layers()

    material_dict = xsection_parameters["material_dict"]
    material_dict = ast.literal_eval(material_dict) if isinstance(material_dict, str) else material_dict
    substrate_material = xsection_parameters["substrate_material"]
    substrate_1_permittivity = material_dict[substrate_material[0]]["permittivity"]

    xsection_simulation.set_permittivity("substrate_1", substrate_1_permittivity)
    if len(xsection_parameters["face_stack"]) == 2:
        substrate_2_permittivity = substrate_1_permittivity
        if len(substrate_material) > 1:
            substrate_2_permittivity = material_dict[substrate_material[1]]["permittivity"]
        xsection_simulation.set_permittivity("substrate_2", substrate_2_permittivity)

    if post_processing_function:
        post_processing_function(xsection_simulation)

    if oxidise_layers_function:
        oxidise_layers_function(xsection_simulation, ma_thickness, ms_thickness, sa_thickness)

    if vertical_cull is not None:

        def _cull_region_vertically(region, layer):  # pylint: disable=unused-argument
            return region & cell_bbox.to_itype(xsection_cell.layout().dbu)

        _iterate_layers_and_modify_region(xsection_cell, _cull_region_vertically)

    if mer_box is not None:
        regions_to_update = {}
        if isinstance(mer_box, list):
            box_region = pya.Region()
            for mb in mer_box:
                box_region += pya.Region(mb.to_itype(xsection_cell.layout().dbu))
        else:
            box_region = pya.Region(mer_box.to_itype(xsection_cell.layout().dbu))

        def _separate_region_in_mer_box(region, layer):
            region_in_box = region & box_region
            regions_to_update[f"{layer.name}_mer"] = region_in_box
            return region - box_region

        _iterate_layers_and_modify_region(xsection_cell, _separate_region_in_mer_box)
        vacuum_in_box = box_region
        for layer, region in regions_to_update.items():
            vacuum_in_box -= region
            xsection_cell.shapes(xsection_simulation.get_sim_layer(layer)).insert(region)
        xsection_cell.shapes(xsection_simulation.get_sim_layer("vacuum_mer")).insert(vacuum_in_box)

    if ma_thickness > 0.0:
        xsection_simulation.set_permittivity("ma_layer", ma_permittivity)
    if ms_thickness > 0.0:
        xsection_simulation.set_permittivity("ms_layer", ms_permittivity)
    if sa_thickness > 0.0:
        xsection_simulation.set_permittivity("sa_layer", sa_permittivity)
    xsection_simulation.process_layers()
    return xsection_simulation


def take_cross_section(
    cell: pya.Cell, cut: tuple[pya.DPoint, pya.DPoint], profile: CrossSectionProfile
) -> dict[pya.LayerInfo, list[tuple[float, float]]]:
    """Collect intersections between ``cut`` and polygons in ``cell`` for each layer taken into account in ``profile``.

    Returns: Dictionary mapping each pya.LayerInfo into segments where ``cut`` overlaps with layer polygon. Segments are
    given as sorted list of tuples (start, end) indicating distances from ``cut[0]`` to the segment points.
    """
    segments_by_layer = {}
    layout = cell.layout()
    cut_edge = pya.DEdge(cut[0], cut[1]).to_itype(layout.dbu)
    cut_vector = cut_edge.d()

    # Place constants related to non-orthogonal edges warning
    appr_edge_slope_tolerance = 0.2  # warning is given if edge slope compared to orthogonal exceeds approximately this
    database_unit_tolerance = 2  # the database unit tolerance

    # Compute variables related to non-orthogonal edges warning
    cut_region_width = ceil(0.5 * database_unit_tolerance / appr_edge_slope_tolerance) * 2
    max_cut_vector_sprod = cut_region_width * appr_edge_slope_tolerance * cut_vector.abs()

    # Simple path region for cut with small width. Use KLayout's boolean operators to detect the intersections.
    cut_region = pya.Region(pya.Path([cut_edge.p1, cut_edge.p2], cut_region_width))

    # Scale intersection dot products within confines of the cut
    crossing_edges = [e for s in cut_region.each() for e in s.each_edge() if cut_edge.crossed_by(e)]
    prods = [cut_vector.sprod(cut_edge.crossing_point(e)) for e in crossing_edges]
    cut_min = min(prods)
    cut_scale = (cut[1] - cut[0]).length() / (max(prods) - cut_min)

    for layer_info in profile.get_layers(layout):
        layer_region = pya.Region(cell.begin_shapes_rec(layout.layer(layer_info)))
        intersection = (cut_region & layer_region).merged()
        segments = []
        for polygon in intersection.each():
            crossing_edges = [e for e in polygon.each_edge() if cut_edge.crossed_by(e)]

            # Warn if cross-section is taken with non-orthogonal edges
            skew_edges = [e for e in crossing_edges if abs(cut_vector.sprod(e.d())) > max_cut_vector_sprod]
            for skew_edge in skew_edges:
                logging.warning(
                    f"Cross section is taken with non-orthogonal edge in cell '{cell.name}' at layer "
                    f"'{layer_info.name}' at location ({cut_edge.crossing_point(skew_edge).to_dtype(layout.dbu)})."
                )

            # Calculate intersection as value between 0 and cut length
            dists = [(cut_vector.sprod(cut_edge.crossing_point(e)) - cut_min) * cut_scale for e in crossing_edges]
            segments.append((min(dists), max(dists)))
        segments_by_layer[layer_info] = sorted(segments)
    return segments_by_layer


def produce_intersection_shapes(
    simulation: Simulation,
    layout: pya.Layout,
    segments_by_layer: dict[pya.LayerInfo, list[tuple[float, float]]],
    profile: CrossSectionProfile,
) -> pya.Cell:
    """Based on collected intersections of a cut, produces cross-section shapes.
    Shapes are placed to same layers, but to separate cell existing at separate layout.

    Args:
        simulation: Original Simulation object from which cross-section is taken from.
        layout: Layout where cross-section cell will be placed.
        segments_by_layer: layer segment data returned by ``take_cross_section``
        profile: CrossSectionProfile object that defines vertical level values for each layer.

    Returns:
        Cell placed to ``layout`` that contains cross-section shapes
    """
    # Produce regions in python dict first before placing them to KLayout layout
    raw_regions = {}
    for layer_info, segments in segments_by_layer.items():
        level = profile.get_level(layer_info.name, simulation)
        output_region = pya.Region()
        for start, end in segments:
            # TODO: remove add_this_to_xor_with_master
            output_region += pya.Region(
                pya.DBox(
                    start,
                    min(level) + profile.add_this_to_xor_with_master,
                    end,
                    max(level) + profile.add_this_to_xor_with_master,
                ).to_itype(layout.dbu)
            )
        raw_regions[layer_info] = output_region

    # Process layers by profile priority, where in case of shape overlap preserve higher priority layer
    regions_to_place = {}
    for layer_info in segments_by_layer.keys():
        dominant_layer_regex = profile.get_dominant_layer_regex(layer_info.name, simulation)
        subtractable_region = pya.Region()
        if dominant_layer_regex:
            for l, unsubtracted_region in raw_regions.items():
                if re.fullmatch(dominant_layer_regex, l.name):
                    subtractable_region += unsubtracted_region
        regions_to_place[layer_info] = raw_regions[layer_info] - subtractable_region

    # See which layers should be set as invisible according to profile
    for layer_info in segments_by_layer.keys():
        if layer_info in profile.get_invisible_layers(simulation):
            regions_to_place[layer_info].clear()

    # Process layers that should be changed to another layer according to profile
    for layer_info in segments_by_layer.keys():
        if profile.change_layer(layer_info, simulation) == layer_info:
            continue
        if not profile.change_layer(layer_info, simulation) in regions_to_place:
            regions_to_place[profile.change_layer(layer_info, simulation)] = pya.Region()
        regions_to_place[profile.change_layer(layer_info, simulation)] += regions_to_place[layer_info]
        regions_to_place[layer_info].clear()

    # Write cell and return it
    cell = layout.create_cell(simulation.cell.name)
    for layer_info in segments_by_layer.keys():
        cell.shapes(layout.layer(layer_info)).insert(regions_to_place[layer_info])
    return cell
