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


import json
import logging
from os import cpu_count

from kqcircuits.defaults import default_layers, default_netlist_breakdown
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import get_cell_path_length
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder

log = logging.getLogger(__name__)


def export_cell_netlist(cell, filename):
    """ Exports netlist into `filename` in JSON

    The file will have three sections: ``{"nets": {...}, "subcircuits": {...}, "circuits": {...}}``

    KLayout's `terminology <https://www.klayout.de/doc-qt5/manual/lvs_overview.html>`__ differs
    from the one used in typical EDA tools where we have components (resistors, capacitors, etc.),
    pins (the endpoints of components) and nets (i.e. wires between pins). Components are PCell
    instances, a.k.a. cells, these are called subcircuits in the netlist file.

    The main conceptual difference is that waveguides, that would be analogous to wires, are also
    treated as components. Consequently, a net in the ``nets`` section usually contains exactly two
    overlapping pins that belong to two different components each identified by a unique
    ``subcircuit_id``. One of these is almost always a waveguide. Unconnected pins are not shown
    except for Launchers.

    The ``subcircuits`` section is a dictionary of the used cells: ``<subcircuit_id>: {"cell_name":
    "...", "subcircuit_location": [<x>, <y>]}``. Where ``cell_name`` is the name of the used Element
    optionally appended with ``$<n>`` if there are more than one Elements of the same type.
    Different instances of the same cell will have different ``subcircuit_id`` but identical
    ``cell_name``.

    The ``circuits`` section maps ``cell_name`` to a dictionary of the named Element's parameters.

    Args:
        cell: pya Cell object
        filename: absolute path as convertible to string
    """
    # get LayoutToNetlist object
    layout = cell.layout()
    shapes_iter = layout.begin_shapes(cell, layout.layer(default_layers["b_ports"]))
    ltn = pya.LayoutToNetlist(shapes_iter)
    # parallel processing
    ltn.threads = cpu_count()
    # select conducting layers
    connector_region = ltn.make_layer(layout.layer(default_layers["b_ports"]), "connector")
    ltn.connect(connector_region)
    # extract netlist for the cell
    ltn.extract_netlist()
    # extract cell to circuit map for finding the netlist of interest
    cm = ltn.const_cell_mapping_into(layout, cell)
    reverse_cell_map = {v: k for k, v in cm.table().items()}
    # export the circuit of interest
    circuit = ltn.netlist().circuit_by_cell_index(reverse_cell_map[cell.cell_index()])
    log.info(f"Exporting netlist to {filename}")
    export_netlist(circuit, filename, ltn.internal_layout(), layout, cm)


def export_netlist(circuit, filename, internal_layout, original_layout, cell_mapping):
    """ Exports `circuit` into `filename` in JSON

    Args:
        circuit: pya Circuit object
        filename: absolute path as convertible to string
        internal_layout: pya layout object where the netlist cells are registered
        original_layout: pya Layout object where the original cells and pcells are registered
        cell_mapping: CellMapping object as given by pya LayoutToNetlist object

    """
    # first flatten subcircuits mentioned in elements to breakdown
    # TODO implement an efficient depth first search or similar solution
    for _ in range(internal_layout.top_cell().hierarchy_levels()):
        subcircuits = list(circuit.each_subcircuit())
        for subcircuit in subcircuits:
            internal_cell = internal_layout.cell(subcircuit.circuit_ref().cell_index)
            if internal_cell.name.split('$')[0] in default_netlist_breakdown:
                circuit.flatten_subcircuit(subcircuit)

    nets_for_export = {}
    for net in circuit.each_net():
        nets_for_export[net.expanded_name()] = extract_nets(net)

    subcircuits_for_export = {}
    used_internal_cells = set()
    for subcircuit in circuit.each_subcircuit():
        internal_cell_index = subcircuit.circuit_ref().cell_index
        internal_cell = internal_layout.cell(internal_cell_index)
        used_internal_cells.add(internal_cell)
        subcircuits_for_export[subcircuit.id()] = {
            "cell_name": internal_cell.name,
            "subcircuit_location": subcircuit.circuit_ref().boundary.bbox().center()
        }

    circuits_for_export = {}
    for internal_cell in sorted(used_internal_cells, key=lambda cell: cell.name):
        circuits_for_export[internal_cell.name] =  extract_circuits(cell_mapping, internal_cell, original_layout)

    with open(str(filename), 'w') as fp:
        json.dump({"nets": nets_for_export, "subcircuits": subcircuits_for_export, "circuits": circuits_for_export}, fp,
                  cls=GeometryJsonEncoder, indent=4)


def extract_nets(net):
    """ Extract dictionary for net for JSON export """
    net_for_export = []
    for pin_ref in net.each_subcircuit_pin():
        net_for_export.append({
            "subcircuit_id": pin_ref.subcircuit().id(),
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
            get_cell_path_length(original_cell, layout.layer(default_layers["waveguide_length"]))
    return circuit_for_export
