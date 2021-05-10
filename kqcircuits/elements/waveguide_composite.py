# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import ast
from math import degrees, atan2
from importlib import import_module
from scipy.optimize import root_scalar

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.util.library_helper import to_module_name
from kqcircuits.util.geometry_helper import vector_length_and_direction, point_shift_along_vector, \
                                            get_cell_path_length
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
    type that get's inserted in the waveguide. Typically this is an Airbridge, but any element with
    port_a and port_b is supported.

    Args:
        position: The location of the Node. Represented as a DPoint object.
        element: The Element type that get's inserted in the waveguide. None by default.
        **params: Other optional parameters for the inserted element

    Returns:
        A Node.
    """

    position: pya.DPoint
    element: Element

    def __init__(self, position, element=None, **params):
        if type(position) == tuple:
            self.position = pya.DPoint(position[0], position[1])
        else:
            self.position = position
        self.element = element
        self.params = params

    def __str__(self):
        """Textual representation of a Node, needed for storage in KLayout parameters."""

        txt = f"{self.position.x}, {self.position.y}"
        if self.element:
            txt += f", '{self.element.__name__}'"
        if self.params:
            for pn, pv in self.params.items():
                if type(pv) is pya.DPoint:  # encode DPoint as tuple
                    self.params[pn] = (pv.x, pv.y)
            txt += f", {self.params}"
        return "(" + txt + ")"


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
    Used for directly setting the first airbrige in a waveguide or for circumventing scaling issues
    of AirbridgeConnection. See "test_wgc_airbridge.lym" for examples.

    The ``ab_across=True`` parameter places a single airbridge across the node. The ``n_bridges=N``
    parameter puts N airbridges evenly distributed across the preceding edge.

    A notable implementation detail is that every Airbridge (sub)class is done as AirbridgeConnection.
    This way a waveguide taper is automatically inserted before and after the airbridge so the user
    does not have to manually add these. Other Node types do not have this feature.

    For examples see the test_waveguide_composite.lym script.
    """

    nodes = Param(pdt.TypeString, "List of Nodes for the waveguide", "(0, 0, 'Airbridge'), (200, 0)")
    taper_length = Param(pdt.TypeDouble, "Taper length", 100, unit="μm")

    def produce_impl(self):
        """Produce the composite waveguide.

        In practice this becomes an alternating chain of WaveguideCoplanar and some other Element
        subclass. Elements are oriented collinear to the preceding Node and an automatic bend is
        inserted after if the next Node is not collinear.
        """
        self._nodes = self._nodes_from_string()
        if not self._nodes:
            return

        self._wg_start_idx = 0      # next waveguide starts here
        self._wg_start_pos = self._nodes[0].position

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

        if node.element is None:
            self._add_waveguide(i)

    def _nodes_from_string(self):
        """Converts the human readable text representation of Nodes to an actual Node object list.

        Needed for storage in KLayout parameters. The string has to conform to a specific format:
        `(x, y, class_str, parameter_dict)`. For example `(0, 500, 'Airbridge', {'n_bridges': 2})`,
        see also the `Node.__str__` method. Empty class_str or parameter_dict may be omitted.

        Returns:
            list of Node objects
        """

        if type(self.nodes) is list:
            self.nodes = ", ".join(self.nodes)
        node_list = ast.literal_eval(self.nodes + ",")

        nodes = []
        for node in node_list:
            x, y = node[0:2]
            element = None
            params = {}
            if len(node) > 2:
                element = node[2]
                if type(element) is dict:
                    params = element
                    element = None
            if len(node) > 3:
                params = node[3]

            if element:
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

            if params:  # re-create DPoint from tuple
                for pn, pv in params.items():
                    if type(pv) is tuple:
                        params[pn] = pya.DPoint(pv[0], pv[1])

            nodes.append(Node(pya.DPoint(x, y), element, **params))

        return nodes

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
        self._insert_cell_and_waveguide(ind, fc_cell, f'{old_id}_port', f'{new_id}_port')

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

        params['a'], params['b'] = params.pop('_a', a), params.pop('_b', b) # obverride a/b if it looks funny

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
        self._insert_cell_and_waveguide(ind, cell)

    def _insert_cell_and_waveguide(self, ind, cell, before="port_a", after="port_b"):
        """Place a cell and create the preceding waveguide.

        Normally the element is oriented from the previous node towards this one. Except the first
        one, that goes from here towards the next.
        """

        node = self._nodes[ind]
        if ind == 0:
            v_dir = self._nodes[ind+1].position - node.position
        else:
            v_dir = node.position - self._nodes[ind-1].position

        trans = pya.DCplxTrans(1, degrees(atan2(v_dir.y, v_dir.x)), False, node.position)

        if ind == 0 or ind == len(self._nodes) - 1:
            rel_ref = self.get_refpoints(cell, rec_levels=0)
            trans *= pya.DTrans(-rel_ref[before if ind == 0 else after])

        _, ref = self.insert_cell(cell, trans)
        self._add_waveguide(ind, ref[before])
        self._wg_start_pos = ref[after]
        self._wg_start_idx = ind

    def _add_waveguide(self, end, end_pos=None):
        """Finish the WaveguideCoplanar ending here.

        Args:
            end: index of the last Node of the waveguide
            end_pos: alternative endpoint of the waveguide
        """

        start = self._wg_start_idx
        if end == start:
            return
        points = [self._wg_start_pos]

        if not self._collinear_or_end(start):   # add a bend after an inserted element, if needed
            v = points[0] - self._nodes[start-1].position
            points.append(points[0] + v / v.length() * self.r)

        sn = self._nodes[start]
        if not sn.element and "ab_across" in sn.params and sn.params["ab_across"]:
            self._ab_across(self._nodes[start+1].position, sn.position, 0)

        for i in range(start + 1, end + 1):
            node = self._nodes[i]
            points.append(end_pos if end_pos and i == end else node.position)
            if "ab_across" in node.params and node.params["ab_across"]:
                self._ab_across(points[-2], points[-1], 0)
            if "n_bridges" in node.params and node.params["n_bridges"] > 0:
                self._ab_across(points[-2], points[-1], node.params["n_bridges"])

        params = {**self.pcell_params_by_name(WaveguideCoplanar), "path": pya.DPath(points, 1)}

        # no termination if in the middle or if the ends are actual elements
        if start != 0 or self._nodes[start].element:
            params['term1'] = 0
        if end != len(self._nodes) - 1 or self._nodes[end].element:
            params['term2'] = 0

        wg = self.add_element(WaveguideCoplanar, **params)
        self.insert_cell(wg)

    def _ab_across(self, start, end, num):
        """Creates ``num`` airbridge crossings equally distributed between ``start`` and ``end``.
        If ``num == 0`` then one airbridge crossing is created at the node.
        """

        ab_cell = self.add_element(Airbridge, Airbridge, airbridge_type=self.airbridge_type)
        v_dir = end - start
        alpha = degrees(atan2(v_dir.y, v_dir.x))

        if num > 0:
            for i in range(1, num + 1):
                ab_trans = pya.DCplxTrans(1, alpha, False, start + i * v_dir / (num + 1))
                self.insert_cell(ab_cell, ab_trans)
        else:
            ab_trans = pya.DCplxTrans(1, alpha, False, end)
            self.insert_cell(ab_cell, ab_trans)

    def _collinear_or_end(self, ind):
        """Is node at ``ind`` in a straight segment or at one end?"""

        if ind == 0 or ind == len(self._nodes) - 1:
            return True

        p1 = self._nodes[ind - 1].position
        p2 = self._nodes[ind].position
        p3 = self._nodes[ind + 1].position

        _, d1 = vector_length_and_direction(p2 - p1)
        _, d2 = vector_length_and_direction(p3 - p2)

        return (d1 - d2).abs() < 0.001 # TODO close enough?

    def _terminator(self, ind):
        """Terminate a the waveguide ending with an Element."""

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
        inst, ref = element.insert_cell(cell)
    except ValueError:
        raise ValueError("Cannot create a waveguide bend with length {} between points {} and {}".format(
            target_len, point_a, point_b))

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
