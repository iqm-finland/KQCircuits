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


import ast
import re

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.waveguide_composite import Node, WaveguideComposite
from kqcircuits.util.library_helper import load_libraries, element_by_class_name


def get_nodes_near_position(top_cell, position, box_size=10, require_gui_editing_enabled=True):
    """Find all WaveguideComposite nodes near a specified position.

    Considers only waveguides that are a direct child of the specified ``top_cell``.

    Args:
        top_cell: cell in which to search for WaveguideComposite instances
        position: pya.DPoint position where to search for nodes
        box_size: capture distance in x,y away from ``position`` where the node can be
        require_gui_editing_enabled: if True, only instances with ``enable_gui_editing==True`` are considered.

    Returns:
        a list of tuples ``(instance, node, node_index)`` where ``instance`` is the WaveguideComposite Instance,
        ``node`` is the ``Node`` object that ``node_index`` is the index of ``node`` in the ``nodes`` parameter of
        the waveguide.
    """
    box = pya.DBox(pya.DPoint(-box_size, -box_size), pya.DPoint(box_size, box_size)).moved(pya.DVector(position))

    found_nodes = []

    for inst in top_cell.each_inst():
        if inst.is_pcell() and isinstance(inst.pcell_declaration(), WaveguideComposite):
            if (not require_gui_editing_enabled) or inst.pcell_parameter('enable_gui_editing'):
                dtrans = inst.dcplx_trans

                nodes = Node.nodes_from_string(inst.pcell_parameter("nodes"))
                for i, node in enumerate(nodes):
                    node_position = dtrans * node.position
                    if box.contains(node_position):
                        found_nodes.append((inst, node, i))
    return found_nodes


def node_to_text(node):
    """Convert ``Node`` object to text fields that can be used for GUI editing.

    The inverse of this function is ``node_from_text``.

    Args:
        node: Node to convert

    Returns:
        tuple of strings ``(x, y, element, inst_name, angle, length_before, length_increment, align, parameters)``
    """

    x = str(node.position.x)
    y = str(node.position.y)
    inst_name = node.inst_name if node.inst_name is not None else ""
    angle = str(node.angle) if node.angle is not None else ""
    length_before = str(node.length_before) if node.length_before is not None else ""
    length_increment = str(node.length_increment) if node.length_increment is not None else ""
    element = node.element.__name__ if node.element is not None else ""
    align = ",".join(node.align) if node.align is not None else ""
    parameters = "\n".join([f'{key}={repr(value)}' for key, value in node.params.items()])

    return (x, y, element, inst_name, angle, length_before, length_increment, align, parameters)


def node_from_text(x, y, element, inst_name, angle, length_before, length_increment, align, parameters):
    """Create Node from text inputs.

    This is the inverse of ``node_to_text``.

    For all arguments except x and y, an empty string is treated as default value. Spaces are stripped from the inputs.
    For ``parameters``, the values will be parsed by ``ast.literal_eval``, which accepts most standard python literals.

    Args:
        x (str): x position, will be converted to float
        y (str): y position, will be converted to float
        element (str): class name of the element, must exist in the `kqcircuits.elements` namespace
        inst_name (str): instance name to use for the element
        angle (str): angle of the node, will be converted to float
        length_before (str): length before this node, will be converted to float
        length_increment (str): length increment produced by meander before this node, will be converted to float
        align (str): input and output refpoint to use for aligning the element, separated by a comma
        parameters (str): multiline string, where each line contains a parameter=value pair.

    Returns: Node

    Raises:
        ValueError: if an input value cannot be converted to the correct type.
    """
    x = float(x)
    y = float(y)

    params = {}
    if inst_name != "":
        params['inst_name'] = inst_name.strip()
    if angle != "":
        params['angle'] = float(angle)
    if length_before != "":
        params['length_before'] = float(length_before)
    if length_increment != "":
        params['length_increment'] = float(length_increment)
    element = element.strip()
    if element == "":
        element = None
    if align != "":
        params['align'] = tuple(s.strip() for s in align.split(','))

    param_lines = parameters.split('\n')
    for param_line in param_lines:
        param_line = param_line.strip()
        if param_line != "":
            m = re.fullmatch(r'([a-zA-Z0-9_]+)\s*=\s*(.*)', param_line)
            if not m:
                raise ValueError('Element parameters should be one key=value pair on each line')

            key = m.groups()[0]
            value = ast.literal_eval(m.groups()[1])
            params[key] = value

    return Node.deserialize((x, y, element, params))


def replace_node(waveguide_instance, node_index, node):
    """Replace a Node in a WaveguideComposite by index.

    Args:
        waveguide_instance: Instance of the waveguide
        node_index: (int) index of the node to replace
        node: new Node
    """
    nodes = Node.nodes_from_string(waveguide_instance.pcell_parameter('nodes'))
    nodes[node_index] = node
    waveguide_instance.change_pcell_parameter('nodes', [str(node) for node in nodes])

    # Update gui_path and gui_path_shadow to reflect possible position changes in the node
    if waveguide_instance.pcell_parameter("enable_gui_editing"):
        path = pya.DPath([node.position for node in nodes], 1)
        # Round to database units since the KLayout partial tool also works in database units
        dbu = waveguide_instance.layout().dbu
        path = path.to_itype(dbu).to_dtype(dbu)
        waveguide_instance.change_pcell_parameter("gui_path", path)
        waveguide_instance.change_pcell_parameter("gui_path_shadow", path)


def get_all_node_elements():
    """Returns all class names from PCells in the Element library which can be used in WaveguideComposite nodes

    Returns:
        List of class names (str)
    """
    valid_elements = ['Airbridge']

    layout = load_libraries(path='elements')['Element Library'].layout()
    for pcell_id in layout.pcell_ids():
        pcell = layout.pcell_declaration(pcell_id)
        valid_elements.append(pcell.__class__.__name__)

    return valid_elements


def get_valid_node_elements():
    """Returns a list of all element class names which would be, at least in principle, usable as ```Node.element```.

    An element is considered valid if it has at least two refpoint pairs ```X``` and ```X_corner```, for any value of
    x.

    Note: this function creates each element with default parameter values. Since this is generally slow and clumsy,
    this function is not used at startup. Instead, a curated list ```node_editor_valid_elements``` is kept in
    ```kqcircuits.defaults```.

    Returns:
        List of class names (str)
    """
    layout = pya.Layout()

    all_elements = get_all_node_elements()
    valid_elements = []

    for classname in all_elements:
        element = element_by_class_name(classname)
        if element is not None:
            cell, refp = element.create_with_refpoints(layout)

            refpoints_with_corner = [name.rstrip('_corner') for name in refp
                                     if name.endswith('_corner') and name.rstrip('_corner') in refp]

            layout.delete_cell(cell.cell_index())

            if len(refpoints_with_corner) > 1:
                valid_elements.append(classname)
        else:
            valid_elements.append(classname)

    return valid_elements
