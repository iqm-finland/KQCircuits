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


import ast
import json
import os
import subprocess
from pathlib import Path
from typing import Callable, List, Tuple, Union
from kqcircuits.defaults import STARTUPINFO, XSECTION_PROCESS_PATH
from kqcircuits.pya_resolver import pya, klayout_executable_command
from kqcircuits.simulations.export.util import export_layers
from kqcircuits.simulations.cross_section_simulation import CrossSectionSimulation
from kqcircuits.simulations.simulation import Simulation


def xsection_call(input_oas: Path, output_oas: Path, cut1: pya.DPoint, cut2: pya.DPoint,
        process_path: Path = XSECTION_PROCESS_PATH, parameters_path: Path = None) -> None:
    """Calls on KLayout to run the XSection plugin

    Args:
        input_oas: Input OAS file (top-down geometry)
        output_oas: Output OAS file (Cross-section of input geometry)
        cut1: DPoint of first endpoint of the cross-section cut
        cut2: DPoint of second endpoint of the cross-section cut
        process_path: XSection process file that defines cross-section etching depths etc
        parameters_path: If process_path points to kqc_process.xs,
            parameters_path should point to the XSection parameters json file
            containing sweeped parameters and layer information.
    """
    if os.name == "nt":
        klayout_dir_name = "KLayout"
    elif os.name == "posix":
        klayout_dir_name = ".klayout"
    else:
        raise SystemError("Error: unsupported operating system")
    xsection_plugin_path = os.path.join(os.path.expanduser("~"), klayout_dir_name, "salt/xsection/macros/xsection.lym")
    cut_string = f"{cut1.x},{cut1.y};{cut2.x},{cut2.y}"

    if not klayout_executable_command():
        raise Exception("Can't find klayout executable command!")
    if not Path(xsection_plugin_path).is_file():
        raise Exception("The 'xsection' plugin is missing in KLayout! Go to 'Tools->Manage Packages' to install it.")

    # Hack: Weird prefix keeps getting added when path is converted to string which breaks the ruby plugin
    xs_run = str(process_path).replace("\\\\?\\", "")
    xs_params = str(parameters_path).replace("\\\\?\\", "")
    # When debugging, remove '-z' argument to see ruby error messages
    subprocess.run([klayout_executable_command(), input_oas.absolute(), '-z', '-nc', '-rx',
                    '-r', xsection_plugin_path,
                    '-rd', f'xs_run={xs_run}',
                    '-rd', f'xs_params={xs_params}',
                    '-rd', f'xs_cut={cut_string}',
                    '-rd', f'xs_out={output_oas.absolute()}'],
        check=True, startupinfo=STARTUPINFO)


# pylint: disable=dangerous-default-value
def create_xsections_from_simulations(simulations: List[Simulation],
                                      output_path: Path,
                                      cuts: Union[Tuple[pya.DPoint, pya.DPoint], List[Tuple[pya.DPoint, pya.DPoint]]],
                                      process_path: Path = XSECTION_PROCESS_PATH,
                                      ma_permittivity: float = 0,
                                      ms_permittivity: float = 0,
                                      sa_permittivity: float = 0,
                                      ma_thickness: float = 0,
                                      ms_thickness: float = 0,
                                      sa_thickness: float = 0,
                                      london_penetration_depth: float = 0,
                                      magnification_order: int = 0
                                    ) -> List[Simulation]:
    """Create cross-sections of all simulation geometries in the list.
    Will set 'box' and 'cell' parameters according to the produced cross-section geometry data.

    Args:
        simulations: List of Simulation objects, usually produced by a sweep
        output_path: Path for the exported simulation files
        cuts: 1. A tuple (p1, p2), where p1 and p2 are endpoints of a cross-section cut or
              2. a list of such tuples such that each Simulation object gets an individual cut
        process_path: XSection process file that defines cross-section etching depths etc
        ma_permittivity: Permittivity of metal–vacuum (air) interface
        ms_permittivity: Permittivity of metal–substrate interface
        sa_permittivity: Permittivity of substrate–vacuum (air) interface
        ma_thickness: Thickness of metal–vacuum (air) interface
        ms_thickness: Thickness of metal–substrate interface
        sa_thickness: Thickness of substrate–vacuum (air) interface
        london_penetration_depth: London penetration depth of the superconducting material
        magnification_order: Increase magnification of simulation geometry to accomodate more precise spacial units.
            0 =   no magnification with 1e-3 dbu
            1 =  10x magnification with 1e-4 dbu
            2 = 100x magnification with 1e-5 dbu etc
            Consider setting non-zero value when using oxide layers with < 1e-3 layer thickness or
            taking cross-sections of thin objects

    Returns:
        List of CrossSectionSimulation objects for each Simulation object in simulations
    """
    if isinstance(cuts, Tuple):
        cuts = [cuts] * len(simulations)
    if len(simulations) != len(cuts):
        raise Exception("Number of cuts did not match the number of simulations")
    if any(len(simulation.get_parameters()["face_stack"]) not in (1, 2) for simulation in simulations):
        raise Exception("Only single face and flip chip cross section simulations currently supported")

    xsection_dir = output_path.joinpath("xsection_tmp")
    xsection_dir.mkdir(parents=True, exist_ok=True)

    layout = pya.Layout()
    load_opts = _load_layout_options_for_xsection_output()
    for simulation, cut in zip(simulations, cuts):
        xsection_parameters = _dump_xsection_parameters(xsection_dir, simulation)
        simulation_file = xsection_dir / f"original_{simulation.cell.name}.oas"
        xsection_file   = xsection_dir / f"xsection_{simulation.cell.name}.oas"
        export_layers(str(simulation_file), simulation.layout, [simulation.cell],
                    output_format='OASIS',
                    layers=None)
        xsection_call(simulation_file, xsection_file, cut[0], cut[1], process_path, xsection_parameters)

        layout.read(str(xsection_file), load_opts)
        xsection_cell = layout.top_cells()[-1]
        xsection_cell.name = simulation.cell.name

    _clean_tmp_xsection_directory(xsection_dir, simulations)
    # Collect cross section simulation sweeps
    return [_construct_cross_section_simulation(
                layout,
                xsection_cell,
                simulations[idx],
                ma_permittivity,
                ms_permittivity,
                sa_permittivity,
                ma_thickness,
                ms_thickness,
                sa_thickness,
                london_penetration_depth,
                magnification_order)
        for idx, xsection_cell in enumerate(layout.top_cells())]
# pylint: enable=dangerous-default-value


def separate_signal_layer_shapes(simulation: Simulation, sort_key: Callable[[pya.Shape], float] = None):
    """Separate shapes in signal layer to their own dedicated signal layers for each face

    Args:
        simulation: A Simulation object where the layer will be separated
        sort_key: A function that, given a Shape object, returns a number.
            Shapes are sorted according to the number in increasing order.
            If None, picks a point in shape polygon, sorts points top to bottom then tie-breaks left to right
    """
    if sort_key is None:
        def sort_key(shape):
            point_in_shape = list(shape.polygon.each_point_hull())[0]
            return (-point_in_shape.y, point_in_shape.x)
    signal_index = 1
    gen_free_layer_slots = free_layer_slots(simulation.layout)
    for face in simulation.face_ids:
        signal_layer = find_layer_by_name(f"{face}_signal", simulation.layout)
        if signal_layer is None:
            continue
        signal_layer_idx = simulation.layout.layer(signal_layer)
        for shape in sorted(simulation.cell.each_shape(signal_layer_idx), key=sort_key):
            # Reuse layer if it already used in layout
            signal_layer = find_layer_by_name(f"{face}_signal_{signal_index}", simulation.layout)
            # If no such layer, find next available layer index
            if signal_layer is None:
                layer_index = next(gen_free_layer_slots)
                signal_layer = pya.LayerInfo(layer_index, 0, f"{face}_signal_{signal_index}")
            simulation.cell.shapes(simulation.layout.layer(signal_layer)).insert(shape)
            signal_index += 1
        simulation.cell.clear(signal_layer_idx)


def find_layer_by_name(layer_name, layout):
    """Returns layerinfo if there already is a layer by layer_name in layout. None if no such layer exists"""
    for l in layout.layer_infos():
        if l.datatype == 0 and layer_name == l.name:
            return l
    return None


def free_layer_slots(layout):
    """A generator of available layer slots"""
    layer_index = 0
    reserved_layer_ids = [l.layer for l in layout.layer_infos() if l.datatype == 0]
    while True:
        layer_index += 1
        if layer_index in reserved_layer_ids:
            continue
        yield layer_index


def _load_layout_options_for_xsection_output():
    load_opts = pya.LoadLayoutOptions()
    load_opts.cell_conflict_resolution = pya.LoadLayoutOptions.CellConflictResolution.RenameCell
    return load_opts


def _remap_face(layer_name, faces_of_flipchip):
    """Rename face to b_*, t_* convention based on faces_of_flipchip list"""
    if len(faces_of_flipchip) > 0 and layer_name.startswith(f"{faces_of_flipchip[0]}_"):
        return f"b_{layer_name[len(faces_of_flipchip[0]) + 1:]}"
    if len(faces_of_flipchip) > 1 and layer_name.startswith(f"{faces_of_flipchip[1]}_"):
        return f"t_{layer_name[len(faces_of_flipchip[1]) + 1:]}"
    return layer_name


def _dump_xsection_parameters(xsection_dir, simulation):
    """If we're sweeping xsection specific parameters,
    dump them in external file for xsection process file to pick up
    """
    simulation_params = {param_name: param_value for param_name, param_value in simulation.get_parameters().items()
                            if not isinstance(param_value, pya.DBox)} # Hack: ignore non-serializable params
    # Also dump all used layers in the simulation cell
    sim_layers = {_remap_face(l.name, simulation_params['face_stack']): f"{l.layer}/{l.datatype}"
        for l in simulation.layout.layer_infos()}
    # Find avaiable layer numbers for substrate layers
    gen_free_layer_slots = free_layer_slots(simulation.layout)
    sim_layers["b_substrate"] = f"{next(gen_free_layer_slots)}/0"
    sim_layers["t_substrate"] = f"{next(gen_free_layer_slots)}/0"
    simulation_params['sim_layers'] = sim_layers
    xsection_parameters_file = xsection_dir / f"parameters_{simulation.cell.name}.json"
    with open(xsection_parameters_file, "w") as sweep_file:
        json.dump(simulation_params, sweep_file)
    return xsection_parameters_file


def _clean_tmp_xsection_directory(xsection_dir, simulations):
    for simulation in simulations:
        if os.path.exists(xsection_dir / f"original_{simulation.cell.name}.oas"):
            os.remove(xsection_dir / f"original_{simulation.cell.name}.oas")
        if os.path.exists(xsection_dir / f"xsection_{simulation.cell.name}.oas"):
            os.remove(xsection_dir / f"xsection_{simulation.cell.name}.oas")
        if os.path.exists(xsection_dir / f"parameters_{simulation.cell.name}.json"):
            os.remove(xsection_dir / f"parameters_{simulation.cell.name}.json")
    if os.path.exists(xsection_dir):
        os.rmdir(xsection_dir)


def _combine_region_from_layers(simulation, layers):
    """Produce a region combined from regions in layers list"""
    region = pya.Region()
    for layer in layers:
        region += pya.Region(simulation.cell.shapes(simulation.layout.layer(layer)))
    return region


def _edge_on_the_box_border(edge, box):
    """True if edge is exactly at the rim of the box"""
    return  (edge.x1 == box.p1.x and edge.x2 == box.p1.x) or \
            (edge.x1 == box.p2.x and edge.x2 == box.p2.x) or \
            (edge.y1 == box.p1.y and edge.y2 == box.p1.y) or \
            (edge.y1 == box.p2.y and edge.y2 == box.p2.y)


def _cut_edge(target_edge, source_edge, extra_edges):
    """Cut an end of the target_edge with source_edge.

    If source_edge leaves behind two ends of the target_edge,
    the second edge bit is stored in extra_edges.
    """
    # Copy target_edge to not modify the original edge instance
    result_edge = pya.DEdge(target_edge.p1.x, target_edge.p1.y, target_edge.p2.x, target_edge.p2.y)
    if result_edge.contains_excl(source_edge.p1):
        if result_edge.contains_excl(source_edge.p2) and source_edge.p2 != result_edge.p2:
            extra_edges.append(pya.DEdge(source_edge.p2, result_edge.p2))
        result_edge.p2 = source_edge.p1
    elif result_edge.contains_excl(source_edge.p2):
        result_edge.p1 = source_edge.p2
    return result_edge


def _remove_shared_points(target_edge, acting_edges, is_adjacent):
    """Remove all points shared by target_edge and edges in acting_edges

    Returns a set of continuous edges that are not contained by acting_edges.
    Set is_adjacent to True if the shape of acting_edges is adjacent to the shape
    from which target_edge was taken. Set to False if the shapes are on top of eah other.
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
            extra_edge_bits = [] # Collect extra edge bits here
            edge_bits = [_cut_edge(e, acting_edge, extra_edge_bits) for e in edge_bits]
            edge_bits.extend(extra_edge_bits) # Add extra bits
            edge_bits = [e for e in edge_bits if e.p1 != e.p2] # Remove zero length edge bits
    return edge_bits


def _thicken_edges(edges, thickness, dbu, grow):
    """Take edges and add thickness to produce a region.

    Requires dbu.
    Set grow to True to grow the region outward, False to grow inward
    """
    if thickness <= 0.0: # Don't do anything if no thickness
        return pya.Region()
    # Construct a graph from the edges to find paths
    # Start by finding start points for paths
    start_points = [e.p1 for e in edges if e.p1 not in [e2.p2 for e2 in edges]]
    path_graph = {}
    for edge in edges:
        path_graph[edge.p1] = edge

    result_layer = pya.Region()
    # Take each start_point and follow the path until the end
    for current_point in start_points:
        polygon_points = [current_point]
        normals = []
        while True:
            # First collect path points for the region polygon
            polygon_points.append(path_graph[current_point].p2)
            edge_dir = path_graph[current_point].p2 - path_graph[current_point].p1
            # Store edge normal, assuming edges go clock-wise around the shape hull
            normal = pya.DPoint(-edge_dir.y, edge_dir.x)
            if not grow: # Flip normal if growing inward
                normal = -normal
            # Set normal length to thickness
            normals.append(normal * (thickness / normal.abs()))
            # At the end point, terminate
            if path_graph[current_point].p2 not in path_graph:
                break
            # Otherwise proceed to next point in path
            current_point = path_graph[current_point].p2
        # Connect to the second layer of the path to add thickness
        polygon_points.append(polygon_points[-1] + normals[-1])
        # Backtrack the path for the second layer of the polygon
        for idx in range(len(normals) - 1, 0, -1):
            normal_sum = normals[idx] + normals[idx - 1] # Sum normals of surrounding edges of the point
            polygon_points.append(polygon_points[idx] + normal_sum)
        polygon_points.append(polygon_points[0] + normals[0]) # Last second layer point, copied from the start_point
        result_layer += pya.Region(pya.DPolygon(polygon_points).to_itype(dbu))
    return result_layer


def _oxidise_layers(simulation, ma_thickness, ms_thickness, sa_thickness):
    """Take the cross section geometry and add oxide layers between substrate, metal and vaccuum.
    Will add geometry around metals and etch away substrate to insert oxide geometry.
    """
    substrate_layers = [layer for layer in simulation.layout.layer_infos() if layer.name.endswith("_substrate")]
    substrate = _combine_region_from_layers(simulation, substrate_layers)
    metal_layers  = [layer for layer in simulation.layout.layer_infos() if layer.name in
        ["b_ground", "t_ground", "b_signal", "t_signal"]]
    metal_layers += [layer for layer in simulation.layout.layer_infos() if layer.name.startswith("b_signal_")]
    metal_layers += [layer for layer in simulation.layout.layer_infos() if layer.name.startswith("t_signal_")]
    metals = _combine_region_from_layers(simulation, metal_layers)
    metal_edges = [e.to_dtype(simulation.layout.dbu) for e in metals.edges()]
    substrate_edges = [e.to_dtype(simulation.layout.dbu) for e in substrate.edges()]

    ma_edges = []
    for metal_edge in metal_edges:
        if not _edge_on_the_box_border(metal_edge, simulation.box):
            ma_edges.extend(_remove_shared_points(metal_edge, substrate_edges, True))

    sa_edges, ms_edges = [], []
    for substrate_edge in substrate_edges:
        if not _edge_on_the_box_border(substrate_edge, simulation.box):
            sa_edges.extend(_remove_shared_points(substrate_edge, metal_edges, True))
            ms_edges.extend(_remove_shared_points(substrate_edge, sa_edges, False))

    ma_layer = _thicken_edges(ma_edges, ma_thickness, simulation.layout.dbu, True)
    ms_layer = _thicken_edges(ms_edges, ms_thickness, simulation.layout.dbu, False)
    sa_layer = _thicken_edges(sa_edges, sa_thickness, simulation.layout.dbu, True)
    sa_layer -= ma_layer # MA layer takes precedence over SA layer

    # Etch and replace substrate layer regions
    if ms_thickness > 0.0 or sa_thickness > 0.0:
        for substrate_layer in substrate_layers:
            substrate_region = pya.Region(simulation.cell.shapes(simulation.layout.layer(substrate_layer)))
            simulation.cell.shapes(simulation.layout.layer(substrate_layer)).clear()
            simulation.cell.shapes(simulation.layout.layer(substrate_layer)).insert(
                substrate_region - ms_layer)

    if ma_thickness > 0.0:
        simulation.cell.shapes(simulation.get_sim_layer("ma_layer")).insert(ma_layer)
    if ms_thickness > 0.0:
        simulation.cell.shapes(simulation.get_sim_layer("ms_layer")).insert(ms_layer)
    if sa_thickness > 0.0:
        simulation.cell.shapes(simulation.get_sim_layer("sa_layer")).insert(sa_layer)


def _construct_cross_section_simulation(layout, xsection_cell, simulation,
        ma_permittivity, ms_permittivity, sa_permittivity,
        ma_thickness, ms_thickness, sa_thickness,
        london_penetration_depth, magnification_order):
    """Produce CrossSectionSimulation object"""
    if magnification_order > 0:
        layout.dbu = 10 ** (-3 - magnification_order)
        xsection_cell.transform(pya.DCplxTrans(10 ** magnification_order))
    xsection_parameters = simulation.get_parameters()
    xsection_parameters['london_penetration_depth'] = london_penetration_depth
    cell_bbox = xsection_cell.dbbox()
    # Disabled for single face and flip-chip cases
    #cell_bbox.p1 -= pya.DPoint(0, xsection_parameters['lower_box_height'])
    if len(xsection_parameters['face_stack']) == 1:
        cell_bbox.p2 += pya.DPoint(0, xsection_parameters['upper_box_height'])
    xsection_parameters['box'] = cell_bbox
    xsection_parameters['cell'] = xsection_cell
    xsection_simulation = CrossSectionSimulation(layout, **xsection_parameters)
    # Keep all parameters given in simulations for JSON
    for k, v in xsection_parameters.items():
        setattr(xsection_simulation, k, v)
    xsection_simulation.xsection_source_class = type(simulation)
    xsection_simulation.register_cell_layers_as_sim_layers()

    material_dict = xsection_parameters['material_dict']
    material_dict = ast.literal_eval(material_dict) if isinstance(material_dict, str) else material_dict
    substrate_material = xsection_parameters['substrate_material']
    b_substrate_permittivity = material_dict[substrate_material[0]]['permittivity']
    xsection_simulation.set_permittivity('b_substrate', b_substrate_permittivity)
    if len(xsection_parameters['face_stack']) == 2:
        t_substrate_permittivity = b_substrate_permittivity
        if len(substrate_material) > 1:
            t_substrate_permittivity = material_dict[substrate_material[1]]['permittivity']
        xsection_simulation.set_permittivity('t_substrate', t_substrate_permittivity)
    _oxidise_layers(xsection_simulation, ma_thickness, ms_thickness, sa_thickness)
    if ma_thickness > 0.0:
        xsection_simulation.set_permittivity('ma_layer', ma_permittivity)
    if ms_thickness > 0.0:
        xsection_simulation.set_permittivity('ms_layer', ms_permittivity)
    if sa_thickness > 0.0:
        xsection_simulation.set_permittivity('sa_layer', sa_permittivity)
    return xsection_simulation
