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
from importlib import import_module
from typing import Tuple

from scipy.optimize import root_scalar

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.util.library_helper import to_module_name
from kqcircuits.util.geometry_helper import vector_length_and_direction, point_shift_along_vector, \
    get_cell_path_length, get_angle
from kqcircuits.defaults import default_layers
from kqcircuits.elements.element import Element
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper
from kqcircuits.elements.f2f_connectors.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf


class Node:
    """Specifies a single node of a composite waveguide.

    Node is as a ``position`` and optionally other parameters. The ``element`` argument sets an Element
    type that gets inserted in the waveguide. Typically this is an Airbridge, but any element with
    port_a and port_b is supported.

    Args:
        position: The location of the Node. Represented as a DPoint object.
        element: The Element type that gets inserted in the waveguide. None by default.
        inst_name: If an instance name is supplied, the element refpoints will be exposed with that name. Default None.
        align: Tuple with two refpoint names that correspond the input and output point of element, respectively
               Default value (None) uses ``('port_a', 'port_b')``
        **params: Other optional parameters for the inserted element

    Returns:
        A Node.
    """

    position: pya.DPoint
    element: Element
    inst_name: str
    align: Tuple

    def __init__(self, position, element=None, inst_name=None, align=tuple(), **params):
        if isinstance(position, tuple):
            self.position = pya.DPoint(position[0], position[1])
        else:
            self.position = position
        self.element = element
        self.align = align
        self.inst_name = inst_name
        self.params = params

    def __str__(self):
        """
        String representation of a Node, used for serialization and needed for storage in KLayout parameters.

        The corresponding deserialization is implemented in `Node.deserialize`.
        """

        txt = f"{self.position.x}, {self.position.y}"
        if self.element is not None:
            txt += f", '{self.element.__name__}'"

        magic_params = {}
        if self.align:
            magic_params['align'] = self.align
        if self.inst_name:
            magic_params['inst_name'] = self.inst_name

        all_params = {**self.params, **magic_params}
        if all_params:
            for pn, pv in all_params.items():
                if isinstance(pv, pya.DPoint):  # encode DPoint as tuple
                    all_params[pn] = (pv.x, pv.y)
            txt += f", {all_params}"
        return "(" + txt + ")"

    @classmethod
    def deserialize(cls, node):
        """
        Create a Node object from a serialized form, such that ``from_serialized(ast.literal_eval(str(node_object)))``
        returns an equivalent copy of ``node_obj``.

        Args:
            node: serialized node, consisting of a tuple ``(x, y, element_name, params)``, where ``x`` and ``y`` are the
                node coordinates. The string ``element_name`` and dict ``params`` are optional.

        Returns: a Node

        """
        x, y = node[0:2]
        element = None
        params = {}
        if len(node) > 2:
            if isinstance(node[2], dict):
                params = node[2]
            else:
                element = node[2]
        if len(node) > 3:
            params = node[3]

        if element is not None:
            if element in globals():
                element = globals()[element]
            else:
                name = to_module_name(element)
                path = "kqcircuits.elements."
                if name.startswith("airbridge") and element != "AirbridgeConnection":
                    path += "airbridges."
                module = import_module(path + name)
                element = getattr(module, element)
            # TODO improve library_helper to get Element by name?

        # re-create DPoint from tuple
        magic_params = ('align', 'inst_name')
        for pn, pv in params.items():
            if isinstance(pv, tuple) and pn not in magic_params:
                params[pn] = pya.DPoint(pv[0], pv[1])

        return cls(pya.DPoint(x, y), element, **params)


@add_parameters_from(AirbridgeConnection)
@add_parameters_from(FlipChipConnectorRf)
@add_parameters_from(WaveguideCoplanar, "term1", "term2")
class WaveguideComposite(Element):
    """A composite waveguide made of waveguides and other elements.

    From the user's perspective this is a WaveguideCoplanar that is extended with Airbridge,
    WaveguideCoplanarTaper and FlipChipConnector, so that a signal can be routed over other
    waveguides and several chip faces. As a bonus feature other arbitrary elements like coplanar
    capacitors are also supported.

    A list of Nodes defines the shape of the waveguide. An empty node, i.e. ``Node.element`` is
    ``None``, will set the next "waypoint" of the waveguide. If an Element is given it will be
    placed on the node, except for the first or last node where it will be adjacent to the edge.

    Inserted elements are oriented collinear with the previous node. If the following node is not
    collinear with the previous element then for convenience an automatic bend is inserted in the
    waveguide. Note that back-to-back elements (i.e. without some empty Nodes in between) should
    only be placed collinear with each other.

    Node parameters will be passed to the element. For convenience, empty nodes may also have
    parameters: ``a``, ``b`` or ``face_id``. They insert a WaveguideCoplanarTaper or a
    FlipChipConnector, respectively and change the defaults too.

    Using _a/_b sets a/b for the AirbridgeConnection but does not change the waveguide's defaults.
    Used for directly setting the first airbridge in a waveguide or for circumventing scaling issues
    of AirbridgeConnection. See "test_wgc_airbridge.lym" for examples.

    The ``ab_across=True`` parameter places a single airbridge across the node. The ``n_bridges=N``
    parameter puts N airbridges evenly distributed across the preceding edge.

    A notable implementation detail is that every Airbridge (sub)class is done as AirbridgeConnection.
    This way a waveguide taper is automatically inserted before and after the airbridge so the user
    does not have to manually add these. Other Node types do not have this feature.

    A WaveguideComposite cell has a method ``segment_lengths`` that returns a list of lengths of each individual
    regular waveguide segment. Segments are bounded by any element that is not a standard waveguide, such as Airbridge,
    flip chip, taper or any custom element.

    For examples see the test_waveguide_composite.lym script.
    """

    nodes = Param(pdt.TypeString, "List of Nodes for the waveguide", "(0, 0, 'Airbridge'), (200, 0)")
    taper_length = Param(pdt.TypeDouble, "Taper length", 100, unit="μm")

    @classmethod
    def create(cls, layout, **parameters):
        cell = super().create(layout, **parameters)

        # Measure segment lengths, counting only "regular waveguides"
        layout = cell.layout()
        # Note: Using layout.cell(inst.cell_index) instead of inst.cell to work around KLayout issue #235
        child_cells = [layout.cell(inst.cell_index) for inst in cell.each_inst()]
        annotation_layer = layout.layer(default_layers['waveguide_length'])
        segment_lengths = [get_cell_path_length(child_cell, annotation_layer) for child_cell in child_cells
                           if child_cell.name == "Waveguide Coplanar"]
        setattr(cell, "segment_lengths", lambda: segment_lengths)

        return cell

    def produce_impl(self):
        """Produce the composite waveguide.

        In practice this becomes an alternating chain of WaveguideCoplanar and some other Element
        subclass. Elements are oriented collinear to the preceding Node and an automatic bend is
        inserted after if the next Node is not collinear.
        """
        self._nodes = self._nodes_from_string()
        self._child_refpoints = {}
        if len(self._nodes) < 2:
            return

        self._wg_start_idx = 0      # next waveguide starts here
        self._wg_start_pos = self._nodes[0].position
        _, self._wg_start_dir = vector_length_and_direction(self._nodes[1].position - self._wg_start_pos)

        for i, node in enumerate(self._nodes):
            if node.element is None:
                if 'a' in node.params or 'b' in node.params:
                    self._add_taper(i)
                elif 'face_id' in node.params:
                    self._add_fc_bump(i)
            else:
                if node.element is AirbridgeConnection:
                    self._add_airbridge(i)
                elif issubclass(node.element, Airbridge):
                    if node.element is not Airbridge:   # change default if specific type is used
                        self.airbridge_type = node.element.default_type
                    self._add_airbridge(i, with_side_airbridges=False)
                elif node.element is WaveguideCoplanarTaper:
                    self._add_taper(i)
                elif node.element is FlipChipConnectorRf:
                    self._add_fc_bump(i)
                else:
                    self._add_simple_element(i)

                self._terminator(i)

        # pylint: disable=undefined-loop-variable
        if node.element is None:
            self._add_waveguide(i)

        self.refpoints.update(self._child_refpoints)
        super().produce_impl()

    def _nodes_from_string(self):
        """Converts the human readable text representation of Nodes to an actual Node object list.

        Needed for storage in KLayout parameters. The string has to conform to a specific format:
        `(x, y, class_str, parameter_dict)`. For example `(0, 500, 'Airbridge', {'n_bridges': 2})`,
        see also the `Node.__str__` method. Empty class_str or parameter_dict may be omitted.

        Returns:
            list of Node objects
        """

        if isinstance(self.nodes, list):
            self.nodes = ", ".join(self.nodes)
        node_list = ast.literal_eval(self.nodes + ",")

        return [Node.deserialize(node) for node in node_list]

    def _add_taper(self, ind):
        """Create a WaveguideCoplanarTaper and change default a/b."""

        node = self._nodes[ind]

        params = {**self.pcell_params_by_name(WaveguideCoplanarTaper), **node.params}
        if self.a == params['a'] and self.b == params['b']: # no change, just a Node
            return

        taper_cell = self.add_element(WaveguideCoplanarTaper, **{**params,
                'a1': self.a, 'b1': self.b, 'm1': self.margin,
                'a2': params['a'], 'b2': params['b'], 'm2': self.margin,
                })
        self._insert_cell_and_waveguide(ind, taper_cell)

        self.a = params['a']
        self.b = params['b']

    def _add_fc_bump(self, ind):
        """Add FlipChipConnectorRF and change default face_id."""
        node = self._nodes[ind]
        params = {**self.pcell_params_by_name(FlipChipConnectorRf), **node.params}
        new_id = node.params.pop("face_id")
        old_id = self.face_ids[0]
        if new_id == old_id:  # no change, just a Node
            return
        # TODO support vias?

        fc_cell = self.add_element(FlipChipConnectorRf, **params)
        self._insert_cell_and_waveguide(ind, fc_cell, before=f'{old_id}_port', after=f'{new_id}_port')

        self.face_ids[0] = new_id
        self.face_ids[1] = old_id

    def _add_airbridge(self, ind, **kwargs):
        """Add an airbridge with tapers at both sides and change default a/b if required."""

        node = self._nodes[ind]
        params = {**self.pcell_params_by_name(AirbridgeConnection), **kwargs,
                  'a1': self.a, 'b1': self.b, 'm1': self.margin,
                  'a2': self.a, 'b2': self.b, 'm2': self.margin,
                  'taper_length': AirbridgeConnection.taper_length,
                  **node.params}

        a, b = params['a'], params['b']

        params['a'], params['b'] = params.pop('_a', a), params.pop('_b', b) # override a/b if it looks funny

        if ind == 0:
            if not {'a1', 'b1', 'a', 'b'} & set(node.params):
                params['a1'], params['b1'] = params['a'], params['b']
            # set temporary private variables used in _terminator()
            self._ta, self._tb = params['a1'], params['b1']

        if {'a', 'b'} & set(node.params):
            params['a2'], params['b2'] = a, b

        if ind == len(self._nodes) - 1:
            self._ta, self._tb = params['a2'], params['b2']

        cell = self.add_element(AirbridgeConnection, **params)
        self._insert_cell_and_waveguide(ind, cell)

        self.a, self.b = a, b

    def _add_simple_element(self, ind):
        """Add any other simple Element, that has port_a and port_b."""

        node = self._nodes[ind]
        params = {**self.pcell_params_by_name(Element), 'taper_length': self.taper_length, **node.params}

        cell = self.add_element(node.element, **params)
        self._insert_cell_and_waveguide(ind, cell, node.inst_name, *node.align)

    def _insert_cell_and_waveguide(self, ind, cell, inst_name=None, before="port_a", after="port_b"):
        """Place a cell and create the preceding waveguide.

        Normally the element is oriented from the previous node towards this one. Except the first
        one, that goes from here towards the next.

        If the element has corner points corresponding to ``before`` and ``after`` (e.g. ``port_a_corner``), these are
        used to determine the entry and exit directions of the ports. If these points do not exist, the waveguides will
        extend the line through ``before`` and ``after``.
        """
        before_corner = before + '_corner'
        after_corner = after + '_corner'

        rel_ref = self.get_refpoints(cell, rec_levels=0)
        element_dir = rel_ref[after] - rel_ref[before]

        node = self._nodes[ind]
        if ind == 0:
            waveguide_dir = self._nodes[ind+1].position - node.position
            if after_corner in rel_ref:
                element_dir = rel_ref[after_corner] - rel_ref[after]
        else:
            waveguide_dir = node.position - self._nodes[ind-1].position
            if before_corner in rel_ref:
                element_dir = rel_ref[before] - rel_ref[before_corner]

        trans = pya.DCplxTrans(1, get_angle(waveguide_dir) - get_angle(element_dir), False, node.position)

        if ind in (0, len(self._nodes) - 1):
            trans *= pya.DTrans(-rel_ref[before if ind == 0 else after])

        _, ref = self.insert_cell(cell, trans)
        if inst_name is not None:
            for name, value in ref.items():
                self._child_refpoints[f'{inst_name}_{name}'] = value

        self._add_waveguide(ind, ref[before])
        self._wg_start_pos = ref[after]
        if after_corner in ref:
            _, self._wg_start_dir = vector_length_and_direction(ref[after_corner] - ref[after])
        # else:
        #     _, self._wg_start_dir = vector_length_and_direction(ref[after] - ref[before])
        self._wg_start_idx = ind

    def _add_waveguide(self, end_index, end_pos=None):
        """Finish the WaveguideCoplanar ending here.

        Args:
            end_index: index of the last Node of the waveguide
            end_pos: alternative endpoint of the waveguide
        """

        start_index = self._wg_start_idx
        if end_index <= start_index:
            return
        points = [self._wg_start_pos]

        start_direction = self._wg_start_dir
        _, direction_to_next = vector_length_and_direction(self._nodes[start_index + 1].position - self._wg_start_pos)

        if (start_direction - direction_to_next).length() > 0.001:
            # Direction of next node doesn't align, insert an extra bend as close to the start as possible
            points.append(points[0] + self.r*start_direction)

        sn = self._nodes[start_index]
        if not sn.element and "ab_across" in sn.params and sn.params["ab_across"]:
            ab_len = sn.params['bridge_length'] if "bridge_length" in sn.params else None
            self._ab_across(self._nodes[start_index+1].position, sn.position, 0, ab_len)

        for i in range(start_index + 1, end_index + 1):
            node = self._nodes[i]
            ab_len = node.params['bridge_length'] if "bridge_length" in node.params else None
            points.append(end_pos if end_pos and i == end_index else node.position)
            if "ab_across" in node.params and node.params["ab_across"]:
                self._ab_across(points[-2], points[-1], 0, ab_len)
            if "n_bridges" in node.params and node.params["n_bridges"] > 0:
                self._ab_across(points[-2], points[-1], node.params["n_bridges"], ab_len)

        params = {**self.pcell_params_by_name(WaveguideCoplanar), "path": pya.DPath(points, 1)}

        # no termination if in the middle or if the ends are actual elements
        if start_index != 0 or self._nodes[start_index].element:
            params['term1'] = 0
        if end_index != len(self._nodes) - 1 or self._nodes[end_index].element:
            params['term2'] = 0

        wg = self.add_element(WaveguideCoplanar, **params)
        self.insert_cell(wg)

        self._wg_start_pos = points[-1]
        _, self._wg_start_dir = vector_length_and_direction(points[-1] - points[-2])

    def _ab_across(self, start, end, num, ab_len=None):
        """Creates ``num`` airbridge crossings equally distributed between ``start`` and ``end``.
        If ``num == 0`` then one airbridge crossing is created at the node. ``ab_len`` is the airbridges' lenght.
        """

        params = {'airbridge_type': self.airbridge_type}
        if ab_len:
            params['bridge_length'] = ab_len
        ab_cell = self.add_element(Airbridge, Airbridge, **params)
        v_dir = end - start
        alpha = get_angle(v_dir)

        if num > 0:
            for i in range(1, num + 1):
                ab_trans = pya.DCplxTrans(1, alpha, False, start + i * v_dir / (num + 1))
                self.insert_cell(ab_cell, ab_trans)
        else:
            ab_trans = pya.DCplxTrans(1, alpha, False, end)
            self.insert_cell(ab_cell, ab_trans)

    def _terminator(self, ind):
        """Terminate the waveguide ending with an Element."""

        if ind == 0 and self.term1 > 0:
            p1 = self._nodes[ind + 1].position
            term = self.term1
        elif ind == len(self._nodes) - 1 and self.term2 > 0:
            p1 = self._nodes[ind - 1].position
            term = self.term2
        else:
            return  # Hasta la vista, baby!

        p2 = self._nodes[ind].position
        a, b = self.a, self.b
        if hasattr(self, '_ta'):
            self.a, self.b = self._ta, self._tb
        WaveguideCoplanar.produce_end_termination(self, p1, p2, term)
        self.a, self.b = a, b


# TODO technical debt: refactor this to be more straightforward and efficient

def produce_fixed_length_bend(element, target_len, point_a, point_a_corner, point_b, point_b_corner, bridges):
    """Inserts a waveguide bend with the given length to the chip.

    Args:
        element: The element to which the waveguide is inserted
        target_len: Target length of the waveguide
        point_a: Endpoint 1 of the waveguide
        point_a_corner: Point towards which the waveguide goes from endpoint 1
        point_b: Endpoint 2 of the waveguide
        point_b_corner: Point towards which the waveguide goes from endpoint 2
        bridges: String determining where airbridges are created, "no" | "middle" | "middle and ends"

    Returns:
        Instance of the created waveguide

    Raises:
        ValueError, if a bend with the given target length and points cannot be created.

    """
    def objective(x):
        return _length_of_var_length_bend(element.layout, x, point_a, point_a_corner, point_b, point_b_corner,
                                          bridges) - target_len
    try:
        # floods the database with PCell variants :(
        root = root_scalar(objective, bracket=(element.r, target_len / 2))
        cell = _var_length_bend(element.layout, root.root, point_a, point_a_corner, point_b, point_b_corner, bridges)
        inst, _ = element.insert_cell(cell)
    except ValueError as e:
        raise ValueError("Cannot create a waveguide bend with length {} between points {} and {}".format(
            target_len, point_a, point_b)) from e

    return inst


def _length_of_var_length_bend(layout, corner_dist, point_a, point_a_corner, point_b, point_b_corner, bridges):
    cell = _var_length_bend(layout, corner_dist, point_a, point_a_corner, point_b, point_b_corner, bridges)
    length = get_cell_path_length(cell, layout.layer(default_layers["waveguide_length"]))
    return length


def _var_length_bend(layout, corner_dist, point_a, point_a_corner, point_b, point_b_corner, bridges):
    cell = WaveguideComposite.create(layout, nodes=[
        Node(point_a, ab_across=bridges.endswith("ends")),
        Node(point_shift_along_vector(point_a, point_a_corner, corner_dist)),
        Node(point_shift_along_vector(point_b, point_b_corner, corner_dist), n_bridges=bridges.startswith("middle")),
        Node(point_b, ab_across=bridges.endswith("ends")),
    ])
    return cell
