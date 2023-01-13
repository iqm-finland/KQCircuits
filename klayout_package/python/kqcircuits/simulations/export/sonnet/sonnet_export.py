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


import os.path
from pathlib import Path

from kqcircuits.pya_resolver import pya
from kqcircuits.defaults import default_layers
from kqcircuits.simulations.export.sonnet import parser
from kqcircuits.simulations.export.util import find_edge_from_point_in_polygons
from kqcircuits.simulations.port import InternalPort, EdgePort
from kqcircuits.simulations.simulation import Simulation, get_simulation_layer_by_name
from kqcircuits.util.export_helper import write_commit_reference_file


def poly_and_edge_indices(polygons, dbu, port, number, location, group):
    i, j, _ = find_edge_from_point_in_polygons(
        polygons,
        location,
        dbu,
        tolerance=5.0  # hardcoded, feel free to change
        )

    return parser.port(
        portnum=number,
        ipolygon=i + 1,
        ivertex=j,
        port_type=("CUP" if group else "STD"),
        group=group,
        resist=port.resistance,
        react=port.reactance,
        induct=port.inductance,
        capac=port.capacitance
    )


def export_sonnet_son(simulation: Simulation, path: Path, detailed_resonance=False, lower_accuracy=False, current=False,
                      control='ABS', fill_type='Staircase', simulation_safety=0):
    """
    Export simulation into son file.

    Arguments:
        simulation: The simulation to be exported.
        path: Location where to write son files.
        detailed_resonance: More info in
            www.sonnetsoftware.com/support/downloads/techdocs/Enhanced_Resonance_Detection_Feature.pdf
        lower_accuracy: False sets Sonnet to Fine/Edge meshing and True to Coarse/Edge Meshing.
        fill_type: Value 'Staircase' sets the default fill type for polygons. The other option is 'Conformal' which can
            be faster but less accurate. A good workflow could be to set everything to Staircase and then set some
            meanders to Conformal in Sonnet.
        current: True computes currents in Sonnet which adds to simulation time but can used to easily see connection
            errors.
        control: Selects what analysis control is used in Sonnet. Options are 'Simple', 'ABS' and 'Sweep' for parameter
            sweeping.
        simulation_safety: Adds extra ground area to a simulation environment (in µm).

    Returns:
        Path to exported son file.
    """
    if simulation is None or not isinstance(simulation, Simulation):
        raise ValueError("Cannot export without simulation")

    def get_sonnet_strings(material_type, grid_size, symmetry):
        layout = simulation.cell.layout()
        dbu = layout.dbu
        layer_pad = layout.layer(get_simulation_layer_by_name("1t1_airbridge_pads"))
        layer_bridge = layout.layer(get_simulation_layer_by_name("1t1_airbridge_flyover"))
        layer_son = layout.layer(get_simulation_layer_by_name("1t1_signal"))
        layer_son_ground = layout.layer(get_simulation_layer_by_name("1t1_ground"))

        simpolygons = [p.polygon for p in simulation.cell.shapes(layer_son).each()] + \
                      [p.polygon for p in simulation.cell.shapes(layer_son_ground).each()]
        airbridge_polygons = [p.polygon for p in simulation.cell.shapes(layer_bridge).each()]
        airpads_polygons = [p.polygon for p in simulation.cell.shapes(layer_pad).each()]
        for p in airpads_polygons:
            p.isVia = True

        level_iter = iter(len(simpolygons) * [(2 if material_type == "Si+Al" else 0)] +
                          len(airbridge_polygons) * [1] + len(airpads_polygons) * [2])

        polys = parser.polygons(simpolygons + airbridge_polygons + airpads_polygons,
                                pya.DVector(-simulation.box.p1.x, -simulation.box.p2.y), dbu,
                                # get the bottom left corner
                                ilevel=level_iter, fill_type=("V" if (fill_type == "Conformal") else "N")
                                )

        # find port edges
        sstring_ports = ""
        refplane_dirs = []
        port_ipolys = []
        group_ascii = ord('A')
        calgroup = ''

        if simulation.use_ports:
            for port in simulation.ports:
                if isinstance(port, InternalPort):
                    sstring_ports += poly_and_edge_indices(
                        simpolygons + airbridge_polygons, dbu,
                        port, port.number, port.signal_location, chr(group_ascii))
                    sstring_ports += poly_and_edge_indices(
                        simpolygons + airbridge_polygons, dbu,
                        port, -port.number, port.ground_location, chr(group_ascii))
                    calgroup += 'CUPGRP "{}"\nID 28\nGNDREF F\nTWTYPE FEED\nEND\n'.format(chr(group_ascii))
                    group_ascii += 1
                elif isinstance(port, EdgePort):
                    # TODO: re-implement calibration
                    #
                    #     refplane_dirs.append(port.side)
                    #     ipoly = poly_and_edge_indeces(cell, simpolygons + airbridge_polygons, dbu, port, ls)
                    #     logging.info(re.findall(r'POLY (\d+)', ipoly))
                    #     port_ipolys.append(re.findall(r'POLY (\d+)', ipoly)) # scan ipolygon
                    sstring_ports += poly_and_edge_indices(
                        simpolygons + airbridge_polygons, dbu,
                        port, port.number, port.signal_location, "")

        sonnet_box = parser.box(
            xwidth=simulation.box.width(),
            ywidth=simulation.box.height(),
            xcells=int(simulation.box.width() / grid_size),
            ycells=int(simulation.box.height() / grid_size),
            materials_type=material_type
        )

        return {
            "polygons": polys,
            "box": sonnet_box,
            "ports": sstring_ports,
            "calgroup": calgroup,
            "refplanes": parser.refplanes(refplane_dirs, simulation_safety, port_ipolys),
            "symmetry": parser.symmetry(symmetry),
            "nports": len({abs(port.number) for port in simulation.ports}),
            "resonance_abs": "DET_ABS_RES Y" if detailed_resonance else "DET_ABS_RES N",
            "lower_accuracy": "1" if lower_accuracy else "0",
            "current": "j" if current else ""
        }

    # detect airbridges
    shapes_in_air = simulation.layout.begin_shapes(simulation.cell, simulation.layout.layer(
        default_layers["1t1_airbridge_flyover"]))
    materials_type = "Si+Al" if not shapes_in_air.shape().is_null() else "Si BT"

    sonnet_strings = get_sonnet_strings(materials_type, 1, False)
    sonnet_strings["control"] = parser.control(control)

    son_filename = str(path.joinpath(simulation.name + '.son'))
    parser.apply_template(
        os.path.join(os.path.dirname(os.path.abspath(parser.__file__)), "template.son"),
        son_filename,
        sonnet_strings
    )
    return son_filename


def export_sonnet(simulations, path: Path, detailed_resonance=False, lower_accuracy=False, current=False, control='ABS',
                  fill_type='Staircase', simulation_safety=0):
    """
    Export Sonnet simulations by writing son files.

    Arguments:
        simulations: List of simulations to be exported.
        path: Location where to write export files.
        detailed_resonance: More info in
            www.sonnetsoftware.com/support/downloads/techdocs/Enhanced_Resonance_Detection_Feature.pdf
        lower_accuracy: False sets Sonnet to Fine/Edge meshing and True to Coarse/Edge Meshing.
        fill_type: Value 'Staircase' sets the default fill type for polygons. The other option is 'Conformal' which can
            be faster but less accurate. A good workflow could be to set everything to Staircase and then set some
            meanders to Conformal in Sonnet.
        current: True computes currents in Sonnet which adds to simulation time but can used to easily see connection
            errors.
        control: Selects what analysis control is used in Sonnet. Options are 'Simple', 'ABS' and 'Sweep' for parameter
            sweeping.
        simulation_safety: Adds extra ground area to a simulation environment (in µm).

    Returns:
        List of paths to exported son files.
    """
    write_commit_reference_file(path)
    son_filenames = []
    for simulation in simulations:
        son_filenames.append(export_sonnet_son(simulation, path, detailed_resonance=detailed_resonance,
                                               lower_accuracy=lower_accuracy, current=current, control=control,
                                               fill_type=fill_type, simulation_safety=simulation_safety))
    return son_filenames
