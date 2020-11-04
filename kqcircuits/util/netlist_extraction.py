# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import json
from kqcircuits.util.geometry_helper import get_cell_path_length
from kqcircuits.defaults import default_layers
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder


def export_netlist(circuit, filename, internal_layout, original_layout, cell_mapping):
    """ Exports `circuit` into `filename` in JSON

    Args:
        circuit: pya Circuit object
        filename: absolute path as convertible to string
        internal_layout: pya layout object where the netlist cells are registered
        original_layout: pya Layout object where the original cells and pcells are registered
        cell_mapping: CellMapping object as given by pya LayoutToNetlist object

    """
    nets_for_export = {}
    for net in circuit.each_net():
        nets_for_export[net.expanded_name()] = \
            extract_nets(net)

    subcircuits_for_export = {}
    used_internal_cells = set()
    for subcircuit in circuit.each_subcircuit():
        subcircuit_for_export, used_internal_cell = extract_subcircuit(internal_layout, subcircuit)
        used_internal_cells.add(used_internal_cell)
        subcircuits_for_export[subcircuit.id()] = subcircuit_for_export

    circuits_for_export = {}
    for internal_cell in used_internal_cells:
        circuits_for_export[internal_cell.name] = \
            extract_circuits(cell_mapping, internal_cell, original_layout)

    with open(str(filename), 'w') as fp:
        json.dump({"nets": nets_for_export, "subcircuits": subcircuits_for_export, "circuits": circuits_for_export}, fp,
                  cls=GeometryJsonEncoder, indent=4)


def extract_subcircuit(internal_layout, subcircuit):
    circuit = subcircuit.circuit_ref()
    internal_cell_index = circuit.cell_index
    internal_cell = internal_layout.cell(internal_cell_index)
    used_internal_cell = internal_cell
    subcircuit_for_export = {
        "cell_name": internal_cell.name,
        "subcircuit_name": subcircuit.expanded_name(),
        "subcircuit_location": circuit.boundary.bbox().center()
    }
    return subcircuit_for_export, used_internal_cell


def extract_nets(net):
    """ Extract dictionary for net for JSON export """
    net_for_export = []
    for pin_ref in net.each_subcircuit_pin():
        net_for_export.append({
            "subcircuit_id": pin_ref.subcircuit().id(),
            "subcircuit_name": pin_ref.subcircuit().expanded_name(),
            "pin": pin_ref.pin().expanded_name()
        })

    return net_for_export


def extract_circuits(cell_mapping, internal_cell, layout):
    """ Extract dictionary for circuit for JSON export """

    circuit_has_cell = cell_mapping.has_mapping(internal_cell.cell_index())
    circuit_for_export = {"circuit_has_cell": circuit_has_cell}

    if circuit_has_cell:
        original_cell_index = cell_mapping.cell_mapping(internal_cell.cell_index())
        original_cell = layout.cell(original_cell_index)
        is_pcell = original_cell.is_pcell_variant()
        circuit_for_export["is_pcell"] = is_pcell
        pcell_parameters = original_cell.pcell_parameters_by_name()

        # remove regardless if exists since it does not actually include more than base anyway
        pcell_parameters.pop('refpoints', None)
        if is_pcell:
            circuit_for_export = {
                **circuit_for_export,
                **pcell_parameters
            }
        circuit_for_export["waveguide_length"] = \
            get_cell_path_length(original_cell, layout.layer(default_layers["annotations"]))
    return circuit_for_export
