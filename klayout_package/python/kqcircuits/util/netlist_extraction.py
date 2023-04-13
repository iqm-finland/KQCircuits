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
import os.path
from os import cpu_count

from kqcircuits.defaults import default_layers, default_netlist_breakdown, default_faces
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import get_cell_path_length
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder

log = logging.getLogger(__name__)


def export_cell_netlist(cell, filename, pcell=None, alt_netlists=None):
    """Exports netlist(s) in JSON into file(s).

    The file will have four sections:
    ``{"nets": {...}, "subcircuits": {...}, "circuits": {...}, "chip": {...}}``

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
    "...", "subcircuit_location": {"_pya_type": "DPoint", "x": <x>, "y": <y>}, ...}``.
    Where ``cell_name`` is the name of the used Element optionally appended with ``$<n>`` if there
    are more than one Elements of the same type. Different instances of the same cell will have
    different ``subcircuit_id`` but identical ``cell_name``. ``subcircuit_location`` defines the
    center of the bounding box of the subcircuit's geometry in ``base_metal_gap_wo_grid`` layer,
    while ``subcircuit_origin`` defines the center of the bounding box of netlist ports of the cell.

    The ``circuits`` section maps ``cell_name`` to a dictionary of the named Element's parameters.

    If the Cell object is a Chip, the ``chip`` section contains bounding boxes of each face in the chip.

    This function may generate alternative netlists too as specified in the ``alt_netlists``
    dictionary. The keys should be tags that get added to the generated netlist filenames and the
    values are the corresponding Element breakdown lists used to generate them. The default netlist
    is generated regadless of this parameter.

    Args:
        cell: pya Cell object
        filename: absolute path as convertible to string
        pcell: pya PCell object. If None, an attempt is made to treat cell as pcell
        alt_netlists: optional dictionary of file name postfixes and element breakdown lists
    """
    if pcell is None:
        pcell = cell

    _export_cell_netlist_breakdown(cell, filename, pcell, default_netlist_breakdown)

    if isinstance(alt_netlists, dict):
        fn, ext = os.path.splitext(filename)
        for tag, breakdown in alt_netlists.items():
            fnt = f"{fn}_{tag}{ext}"
            _export_cell_netlist_breakdown(cell, fnt, pcell, breakdown)


def _export_cell_netlist_breakdown(cell, filename, pcell, breakdown_list):
    """A helper function of ``export_cell_netlist``, processes a single breakdown list."""

    # get LayoutToNetlist object
    layout = cell.layout()
    faces_with_ports = [face_id for face_id in default_faces if f"{face_id}_ports" in default_layers]
    port_layers = [layout.layer(default_layers[f"{face_id}_ports"]) for face_id in faces_with_ports]
    shapes_iter = pya.RecursiveShapeIterator(layout, cell, port_layers)
    ltn = pya.LayoutToNetlist(shapes_iter)
    # text_enlargement>0 converts the texts into boxes so that their overlaps are detected as connections
    ltn.dss().text_enlargement = 1
    # parallel processing
    ltn.threads = cpu_count()
    # select conducting layers
    for face_id in faces_with_ports:
        connector_region = ltn.make_layer(layout.layer(default_layers[f"{face_id}_ports"]), f"connector_{face_id}")
        ltn.connect(connector_region)
    # extract netlist for the cell
    ltn.extract_netlist()
    # extract cell to circuit map for finding the netlist of interest
    cm = ltn.const_cell_mapping_into(layout, cell)
    reverse_cell_map = {v: k for k, v in cm.table().items()}
    # export the circuit of interest
    circuit = ltn.netlist().circuit_by_cell_index(reverse_cell_map[cell.cell_index()])
    if circuit:
        log.info(f"Exporting netlist to {filename}")
        _export_netlist(circuit, filename, ltn.internal_layout(), layout, cm, pcell, breakdown_list)
    else:
        log.info(f"No circuit found for {cell.display_title()}")


def _export_netlist(circuit, filename, internal_layout, original_layout, cell_mapping, pcell, breakdown_list):
    """A helper function of ``export_cell_netlist``,  exports ``circuit`` into ``filename``.

    Args:
        circuit: pya Circuit object
        filename: absolute path as convertible to string
        internal_layout: pya layout object where the netlist cells are registered
        original_layout: pya Layout object where the original cells and pcells are registered
        cell_mapping: CellMapping object as given by pya LayoutToNetlist object
        pcell: pya PCell object from which circuit was extracted
        breakdown_list: a list of Elements to break down for the netlist
    """

    # first flatten subcircuits mentioned in elements to breakdown
    # TODO implement an efficient depth first search or similar solution
    for _ in range(internal_layout.top_cell().hierarchy_levels()):
        subcircuits = list(circuit.each_subcircuit())
        for subcircuit in subcircuits:
            internal_cell = internal_layout.cell(subcircuit.circuit_ref().cell_index)
            if internal_cell.name.split('$')[0].replace('*', ' ') in breakdown_list:
                circuit.flatten_subcircuit(subcircuit)

    nets_for_export = {}
    for net in circuit.each_net():
        nets_for_export[net.expanded_name()] = extract_nets(net)

    subcircuits_for_export = {}
    used_internal_cells = set()

    # selects last cell in the layout, which will contain all instances of all cells with user properties
    *_, last_cell = original_layout.each_cell()

    # retrieve all instances in last_cell hierarchy
    # instances in original layout are identified by cell index and transformation
    # the concatenated transformation of instance's predecessors is stored as tuple's second element
    original_instances = []
    instance_queue = list(last_cell.each_inst())
    instance_queue = [(instance, pya.DCplxTrans.R0) for instance in instance_queue]
    while len(instance_queue) > 0:
        instance, instance_trans = instance_queue.pop(0)
        original_instances.append((instance, instance_trans))
        for child in instance.cell.each_inst():
            instance_queue.append((child, instance_trans * instance.dcplx_trans))

    # Indexing as defined in default_layers is not consistent with layer indexing in original_layout
    base_metal_gap_wo_grid_layer_idx_array = [idx for idx, li in
        enumerate(original_layout.layer_infos()) if li.name.endswith('_base_metal_gap_wo_grid')]

    for subcircuit in circuit.each_subcircuit():
        internal_cell = internal_layout.cell(subcircuit.circuit_ref().cell_index)
        if cell_mapping.has_mapping(internal_cell.cell_index()):
            original_cell_index = cell_mapping.cell_mapping(internal_cell.cell_index())
            possible_instances = [(i,i_trans) for i,i_trans in original_instances
                                                if i.cell.cell_index() == original_cell_index]
        else:
            log.info(('%s element has no cell mapping in %s between circuit layout and orignal layout,'
                    ' using subcircuit center point as subcircuit_location instead'), internal_cell.name, circuit.name)
            possible_instances = []

        used_internal_cells.add(internal_cell)

        if hasattr(subcircuit, "trans"):
            subcircuit_trans = subcircuit.trans
            subcircuit_location = (subcircuit.trans * subcircuit.circuit_ref().boundary).bbox().center()
        else:  # sane defaults for klayout 0.26 as it does not have `subcircuit.trans`
            subcircuit_trans = pya.DCplxTrans.R0
            subcircuit_location = pya.DPoint(0.0, 0.0)

        instances_with_eq_trans = [(i, i_trans) for i, i_trans in possible_instances
                                                if i_trans * i.dcplx_trans == subcircuit_trans]
        property_dict = {}
        correct_instance = None
        if instances_with_eq_trans:
            # Find property_dict if available
            instances_with_property_dict = [(i, i_trans) for i, i_trans in instances_with_eq_trans if i.has_prop_id()]
            if instances_with_property_dict:
                correct_instance, correct_instance_trans = instances_with_property_dict[0]
                property_dict = {key: value for (key, value) in
                    original_layout.properties(correct_instance.prop_id) if key != "id"}
            else:
                correct_instance, correct_instance_trans = instances_with_eq_trans[0]
            # Collect bounding boxes for all *_base_metal_gap_wo_grid layers
            # then construct a bigger bounding box that envelops all of them
            bboxes = []
            for idx in base_metal_gap_wo_grid_layer_idx_array:
                bbox = correct_instance.dbbox_per_layer(idx)
                if not bbox.empty():
                    bboxes.append(bbox)
            if len(bboxes) > 0:
                combined_bbox = pya.DBox(min([bbox.p1.x for bbox in bboxes]), min([bbox.p1.y for bbox in bboxes]),
                                         max([bbox.p2.x for bbox in bboxes]), max([bbox.p2.y for bbox in bboxes]))
                # subcircuit_location is the center of geometry of all *_base_metal_gap_wo_grid layers in the cell
                # we also transform the point by instance's predecessors' transformation
                subcircuit_location = correct_instance_trans * combined_bbox.center()
            else:
                log.info(('%s element has no bounding boxes in *_base_metal_gap_wo_grid layers in %s,'
                    ' using subcircuit center point as subcircuit_location instead'),
                    internal_cell.name, circuit.name)
        elif possible_instances:
            log.info(('Could not find a matching element for %s subcircuit in the orignal layout of %s,'
                    ' using subcircuit center point as subcircuit_location instead'), internal_cell.name, circuit.name)

        subcircuits_for_export[subcircuit.id()] = {
            "cell_name": internal_cell.name,
            "instance_name": correct_instance.property('id') if correct_instance else None,
            "subcircuit_origin": subcircuit_trans.disp,
            "subcircuit_location": subcircuit_location,
            "properties": property_dict,
        }

    circuits_for_export = {}
    for internal_cell in sorted(used_internal_cells, key=lambda cell: cell.name):
        circuits_for_export[internal_cell.name] = extract_circuits(cell_mapping, internal_cell, original_layout)

    chip_for_export = {}
    if pcell.pcell_declaration() is not None:
        chip_params = pcell.pcell_parameters_by_name()
        if {'frames_enabled', 'face_boxes', 'face_ids', 'box'} <= set(chip_params.keys()):
            for face in chip_params['frames_enabled']:
                face_box = chip_params['face_boxes'][int(face)]
                if face_box is None:
                    face_box = chip_params['box']
                face_id = chip_params['face_ids'][int(face)]
                chip_for_export[f'{face_id}_face_dimensions'] = face_box

    with open(str(filename), 'w') as fp:
        json.dump({
            "nets": nets_for_export,
            "subcircuits": subcircuits_for_export,
            "circuits": circuits_for_export,
            "chip": chip_for_export
        }, fp, cls=GeometryJsonEncoder, indent=4)


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
        circuit_for_export["waveguide_length"] = get_cell_path_length(original_cell)
    return circuit_for_export
