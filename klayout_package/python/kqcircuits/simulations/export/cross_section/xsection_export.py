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
import json
import os
import subprocess
from pathlib import Path
from typing import Callable
from kqcircuits.defaults import STARTUPINFO, XSECTION_PROCESS_PATH
from kqcircuits.pya_resolver import pya, klayout_executable_command
from kqcircuits.simulations.export.cross_section.cross_section_export import (
    _check_metal_heights,
    _iterate_layers_and_modify_region,
    _oxidise_layers,
)
from kqcircuits.util.load_save_layout import load_layout, save_layout
from kqcircuits.simulations.cross_section_simulation import CrossSectionSimulation
from kqcircuits.simulations.simulation import Simulation, to_1d_list
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder


### DEPRECATED!
### This file contains utility functions that use XSection as an external tool to produce cross sections
### for sweeped simulations.
### Active development should instead be done on kqcircuits.simulations.export.cross_section_export,
### which uses KQCircuits native implementation to produce cross sections.


def xsection_call(
    input_oas: Path,
    output_oas: Path,
    cut1: pya.DPoint,
    cut2: pya.DPoint,
    process_path: Path = XSECTION_PROCESS_PATH,
    parameters_path: Path = None,
) -> None:
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
    subprocess.run(
        [
            klayout_executable_command(),
            input_oas.absolute(),
            "-z",
            "-nc",
            "-rx",
            "-r",
            xsection_plugin_path,
            "-rd",
            f"xs_run={xs_run}",
            "-rd",
            f"xs_params={xs_params}",
            "-rd",
            f"xs_cut={cut_string}",
            "-rd",
            f"xs_out={output_oas.absolute()}",
        ],
        check=True,
        startupinfo=STARTUPINFO,
    )


def create_xsections_from_simulations(
    simulations: list[Simulation],
    output_path: Path,
    cuts: tuple[pya.DPoint, pya.DPoint] | list[tuple[pya.DPoint, pya.DPoint]],
    process_path: Path = XSECTION_PROCESS_PATH,
    post_processing_function: Callable[[CrossSectionSimulation], None] = None,
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
        output_path: Path for the exported simulation files
        cuts: 1. A tuple (p1, p2), where p1 and p2 are endpoints of a cross-section cut or
              2. a list of such tuples such that each Simulation object gets an individual cut
        process_path: XSection process file that defines cross-section etching depths etc
        post_processing_function: Additional function to post-process the cross-section geometry.
            Defaults to None, in which case no post-processing is performed.
            The function takes a CrossSectionSimulation object as argument
        oxidise_layers_function: Set this argument if you have a custom way of introducing
            oxidization layers to the cross-section metal deposits and substrate.
            See expected function signature from pyhints
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
            Consider setting non-zero value when using oxide layers with < 1e-3 layer thickness or
            taking cross-sections of thin objects
        layout: predefined layout for the cross-section simulation (optional)

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

    xsection_dir = output_path.joinpath("xsection_tmp")
    xsection_dir.mkdir(parents=True, exist_ok=True)

    if layout is None:
        layout = pya.Layout()
    xsection_cells = []
    for simulation, cut in zip(simulations, cuts):
        _check_metal_heights(simulation)
        xsection_parameters = _dump_xsection_parameters(xsection_dir, simulation)
        simulation_file = xsection_dir / f"original_{simulation.cell.name}.oas"
        xsection_file = xsection_dir / f"xsection_{simulation.cell.name}.oas"
        save_layout(simulation_file, simulation.layout, [simulation.cell], no_empty_cells=True)
        xsection_call(simulation_file, xsection_file, cut[0], cut[1], process_path, xsection_parameters)

        load_layout(xsection_file, layout)
        for i in layout.layer_indexes():
            if all(layout.begin_shapes(cell, i).at_end() for cell in layout.top_cells()):
                layout.delete_layer(i)  # delete empty layers caused by bug in klayout 0.29.0
        xsection_cells.append(layout.top_cells()[-1])
        xsection_cells[-1].name = simulation.cell.name

    _clean_tmp_xsection_directory(xsection_dir, simulations)
    # Collect cross-section simulation sweeps
    return [
        _construct_cross_section_simulation(
            layout,
            xsection_cell,
            simulations[idx],
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
            magnification_order,
        )
        for idx, xsection_cell in enumerate(xsection_cells)
    ]


def _dump_xsection_parameters(xsection_dir, simulation):
    """If we're sweeping xsection specific parameters,
    dump them in external file for xsection process file to pick up
    """
    simulation_params = {
        param_name: param_value
        for param_name, param_value in simulation.get_parameters().items()
        if not isinstance(param_value, pya.DBox)
    }  # Hack: ignore non-serializable params
    simulation_params["chip_distance"] = to_1d_list(simulation_params["chip_distance"])
    # Also dump all used layers in the simulation cell
    simulation_params["sim_layers"] = {l.name: f"{l.layer}/{l.datatype}" for l in simulation.layout.layer_infos()}
    xsection_parameters_file = xsection_dir / f"parameters_{simulation.cell.name}.json"
    with open(xsection_parameters_file, "w", encoding="utf-8") as sweep_file:
        json.dump(simulation_params, sweep_file, cls=GeometryJsonEncoder)
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


def _construct_cross_section_simulation(
    layout,
    xsection_cell,
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
    magnification_order,
):
    """Produce CrossSectionSimulation object"""
    if magnification_order > 0:
        layout.dbu = 10 ** (-3 - magnification_order)
        xsection_cell.transform(pya.DCplxTrans(10**magnification_order))
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
