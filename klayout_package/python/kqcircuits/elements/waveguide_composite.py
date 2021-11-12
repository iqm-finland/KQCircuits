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
from math import pi, tan
from autologging import logged

from scipy.optimize import root_scalar

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.util.library_helper import to_module_name
from kqcircuits.util.geometry_helper import vector_length_and_direction, point_shift_along_vector, \
    get_cell_path_length, get_angle, get_direction
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
        angle: Angle of waveguide direction in degrees
        **params: Other optional parameters for the inserted element

    Returns:
        A Node.
    """

    position: pya.DPoint
    element: Element
    inst_name: str
    align: Tuple
    angle: float

    def __init__(self, position, element=None, inst_name=None, align=tuple(), angle=None, **params):
        if isinstance(position, tuple):
            self.position = pya.DPoint(position[0], position[1])
        else:
            self.position = position
        self.element = element
        self.align = align
        self.inst_name = inst_name
        self.angle = angle
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
        if self.angle is not None:
            magic_params['angle'] = self.angle

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
        magic_params = ('align', 'inst_name', 'angle')
        for pn, pv in params.items():
            if isinstance(pv, tuple) and pn not in magic_params:
                params[pn] = pya.DPoint(pv[0], pv[1])

        return cls(pya.DPoint(x, y), element, **params)

    @staticmethod
    def nodes_from_string(nodes):
        """Converts the human readable text representation of Nodes to an actual Node object list.

        Needed for storage in KLayout parameters. The string has to conform to a specific format:
        `(x, y, class_str, parameter_dict)`. For example `(0, 500, 'Airbridge', {'n_bridges': 2})`,
        see also the `Node.__str__` method. Empty class_str or parameter_dict may be omitted.

        Returns:
            list of Node objects
        """

        nlas = ", ".join(nodes) if isinstance(nodes, list) else nodes
        node_list = ast.literal_eval(nlas + ",")

        return [Node.deserialize(node) for node in node_list]


@add_parameters_from(AirbridgeConnection, "taper_length", "airbridge_type")
@add_parameters_from(FlipChipConnectorRf)
@add_parameters_from(WaveguideCoplanar, "term1", "term2")
@logged
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
    tight_routing = Param(pdt.TypeBoolean, "Tight routing for corners", False)

    @classmethod
    def create(cls, layout, library=None, **parameters):
        cell = super().create(layout, library, **parameters)

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
        self._nodes = Node.nodes_from_string(self.nodes)
        self._child_refpoints = {}
        if len(self._nodes) < 2:
            self.raise_error_on_cell("Need at least 2 Nodes for a WaveguideComposite.",
                                     self._nodes[0].position if len(self._nodes) == 1 else pya.DPoint())

        self._wg_start_idx = 0      # next waveguide starts here
        self._wg_start_pos = self._nodes[0].position
        self._wg_start_dir = self._node_entrance_direction(0)

        for i, node in enumerate(self._nodes):
            self.__log.debug(f' Node #{i}: ({node.position.x:.2f}, {node.position.y:.2f}), {node.element.__class__},'
                              ' {node.params}')
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

        # Create airbridge on each node that has `ab_across=True` in params
        for i, node in enumerate(self._nodes):
            if "ab_across" in node.params and node.params["ab_across"]:
                ab_len = node.params['bridge_length'] if "bridge_length" in node.params else None
                self._ab_across(node.position - self._node_entrance_direction(i), node.position, 0, ab_len)

        # Reference points
        self.refpoints.update(self._child_refpoints)
        self.add_port("a", self._nodes[0].position, -self._node_entrance_direction(0))
        self.add_port("b", self._wg_start_pos, self._wg_start_dir)

        super().produce_impl()

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
        params = {**self.pcell_params_by_name(node.element), 'taper_length': self.taper_length, **node.params}

        cell = self.add_element(node.element, **params)
        self._insert_cell_and_waveguide(ind, cell, node.inst_name, *node.align)

    def _insert_cell_and_waveguide(self, ind, cell, inst_name=None, before="port_a", after="port_b"):
        """Place a cell and create the preceding waveguide.

        Normally the element is oriented from the previous node towards this one. Except the first
        one, that goes from here towards the next. The orientation can be also manually fixed by using
        the node parameter `angle`.

        If the element has corner points corresponding to ``before`` and ``after`` (e.g. ``port_a_corner``), these are
        used to determine the entry and exit directions of the ports. If these points do not exist, the waveguides will
        extend the line through ``before`` and ``after``.
        """
        before_corner = before + '_corner'
        after_corner = after + '_corner'

        # Compute cell relative entrance direction
        rel_ref = self.get_refpoints(cell, rec_levels=0)
        if before_corner in rel_ref:
            element_dir = rel_ref[before] - rel_ref[before_corner]
        else:
            element_dir = rel_ref[after] - rel_ref[before]

        # Compute transformation for the cell
        waveguide_dir = self._node_entrance_direction(ind)
        trans = pya.DCplxTrans(1, get_angle(waveguide_dir) - get_angle(element_dir), False, self._nodes[ind].position)
        if ind in (0, len(self._nodes) - 1):
            trans *= pya.DTrans(-rel_ref[before if ind == 0 else after])

        # Insert element cell with computed transformation
        _, ref = self.insert_cell(cell, trans)
        if inst_name is not None:
            for name, value in ref.items():
                self._child_refpoints[f'{inst_name}_{name}'] = value

        # Add waveguide from previous element until this element
        self._add_waveguide(ind, ref[before], waveguide_dir)

        # Keep track of current position, direction, and index for the future elements
        self._wg_start_pos = ref[after]
        if after_corner in ref:
            _, self._wg_start_dir = vector_length_and_direction(ref[after_corner] - ref[after])
        self._wg_start_idx = ind

    def _node_entrance_direction(self, ind):
        """Returns element entrance direction at node index `ind`."""
        fixed_angle = self._nodes[ind].angle
        if fixed_angle is None:
            prev = max(0, ind - 1)
            return vector_length_and_direction(self._nodes[prev + 1].position - self._nodes[prev].position)[1]
        return get_direction(fixed_angle)

    def _add_waveguide(self, end_index, end_pos=None, end_dir=None):
        """Creates waveguide from `self._wg_start_idx` until `end_index`.

        Args:
            end_index: the last node index taken into account in the waveguide
            end_pos: endpoint position of the waveguide (optional, overwrites `self._nodes[end_index].position`)
            end_dir: endpoint direction of the waveguide (optional)
        """

        def get_corner_lengths(segment_vector, dir_start=pya.DVector(), dir_end=pya.DVector()):
            """Returns distances from segment end points to corner points depending on value of self.tight_routing.
            Returns zero length, if the corner point is not necessary.

            Args:
                segment_vector (pya.DVector): vector from start point to end point
                dir_start (pya.DVector): segment start direction as unit vector (or use zero vector if free direction)
                dir_end (pya.DVector): segment end direction as unit vector (or use zero vector if free direction)

            Returns:
                tuple of lengths
            """
            if not self.tight_routing:
                # Use corner points self.r away from end points.
                _, d = vector_length_and_direction(segment_vector)
                if self.r * abs(d.vprod(dir_start) / 2) < 0.001 and self.r * abs(d.vprod(dir_end) / 2) < 0.001:
                    return 0.0, 0.0
                _, d = vector_length_and_direction(segment_vector - self.r * dir_end)
                if self.r * abs(d.vprod(dir_start) / 2) < 0.001:
                    return 0.0, self.r
                _, d = vector_length_and_direction(segment_vector - self.r * dir_start)
                if self.r * abs(d.vprod(dir_end) / 2) < 0.001:
                    return self.r, 0.0
                return self.r, self.r

            # Use optimal corner routing
            s = segment_vector
            for _ in range(100):  # iterate at most 100 times
                _, d = vector_length_and_direction(s)
                start_len = self.r * abs(d.vprod(dir_start) / (1.0 + d.sprod(dir_start)))
                end_len = self.r * abs(d.vprod(dir_end) / (1.0 + d.sprod(dir_end)))

                # check if converged
                prev_s = s
                s = segment_vector - start_len * dir_start - end_len * dir_end
                if (s - prev_s).length() < 1e-5:
                    return 0.0 if start_len < 0.001 else start_len, 0.0 if end_len < 0.001 else end_len

            # Not converged to up here
            self.raise_error_on_cell("Cannot find suitable routing using 'tight' corners.", self._wg_start_pos)
            return 0.0, 0.0

        # Check if segment has any points
        start_index = self._wg_start_idx
        if end_index <= start_index:
            return

        # Create waveguide path and create airbridges determined by parameter `n_bridges`.
        points = [self._wg_start_pos]
        for i in range(start_index, end_index):
            node0 = self._nodes[i]
            node1 = self._nodes[i + 1]

            # Determine segment endpoint positions
            pos0 = self._wg_start_pos if i == start_index else node0.position
            dir0 = self._wg_start_dir if i == start_index else \
                pya.DVector() if node0.angle is None else get_direction(node0.angle)
            pos1 = end_pos if i + 1 == end_index and end_pos is not None else node1.position
            dir1 = end_dir if i + 1 == end_index and end_dir is not None else \
                pya.DVector() if node1.angle is None else get_direction(node1.angle)

            # Add corner points
            len0, len1 = get_corner_lengths(pos1 - pos0, dir0, dir1)
            if len0 > 0:
                points.append(pos0 + len0 * dir0)
            points.append(pos1 - len1 * dir1)

            # Add airbridges on the straight segment
            if "n_bridges" in node1.params and node1.params["n_bridges"] > 0:
                ab_len = node1.params['bridge_length'] if "bridge_length" in node1.params else None
                self._ab_across(points[-2], points[-1], node1.params["n_bridges"], ab_len)

            # Add final point if it's not already added
            if i + 1 == end_index and len1 > 0:
                points.append(pos1)

        # Create and insert waveguide cell
        # Avoid termination if in the middle or if the ends are actual elements
        params = {**self.pcell_params_by_name(WaveguideCoplanar), "path": pya.DPath(points, 1)}
        if start_index != 0 or self._nodes[start_index].element:
            params['term1'] = 0
        if end_index != len(self._nodes) - 1 or self._nodes[end_index].element:
            params['term2'] = 0
        wg = self.add_element(WaveguideCoplanar, **params)
        self.insert_cell(wg)

        # Keep track of current position, direction, and index for the future elements
        self._wg_start_pos = points[-1]
        if self._nodes[end_index].angle is None:
            _, self._wg_start_dir = vector_length_and_direction(points[-1] - points[-2])
        else:
            self._wg_start_dir = get_direction(self._nodes[end_index].angle)
        self._wg_start_idx = end_index

    def _ab_across(self, start, end, num, ab_len=None):
        """Creates ``num`` airbridge crossings equally distributed between ``start`` and ``end``.
        If ``num == 0`` then one airbridge crossing is created at the node. ``ab_len`` is the airbridges' lenght.
        """

        params = {'airbridge_type': self.airbridge_type}
        if ab_len:
            params['bridge_length'] = ab_len
        ab_cell = self.add_element(Airbridge, **params)
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
        return _length_of_var_length_bend(element.layout, element.LIBRARY_NAME, x, point_a, point_a_corner, point_b,
                                          point_b_corner, bridges, element.r) - target_len
    try:
        # floods the database with PCell variants :(
        root = root_scalar(objective, bracket=(element.r, target_len / 2))
        cell = _var_length_bend(element.layout, element.LIBRARY_NAME, root.root, point_a, point_a_corner, point_b,
                                point_b_corner, bridges)
        inst, _ = element.insert_cell(cell)
    except ValueError as e:
        raise ValueError("Cannot create a waveguide bend with length {} between points {} and {}".format(
            target_len, point_a, point_b)) from e

    return inst


def _length_of_var_length_bend(layout, library, corner_dist, point_a, point_a_corner, point_b, point_b_corner,
                               bridges, r):
    # This function shouldn't raise exception, so we have to manually test if waveguide doesn't fit.
    # These tests do not cover all cases, but are enough in most cases
    point_a_shift = point_shift_along_vector(point_a, point_a_corner, corner_dist)
    point_b_shift = point_shift_along_vector(point_b, point_b_corner, corner_dist)
    v1, v2, alpha1, alpha2, _ = WaveguideCoplanar.get_corner_data(point_a, point_a_shift, point_b_shift, r)
    _, v3, _, alpha3, _ = WaveguideCoplanar.get_corner_data(point_a_shift, point_b_shift, point_b, r)
    cut_dist1 = r * tan((pi - abs(pi - abs(alpha2 - alpha1))) / 2)
    cut_dist2 = r * tan((pi - abs(pi - abs(alpha3 - alpha2))) / 2)
    if v1.length() < cut_dist1 or v3.length() < cut_dist2:
        return -1e30  # straight doesn't fit at the ends -> corner_dist is probably too short
    if v2.length() < cut_dist1 + cut_dist2:
        return 1e30  # straight doesn't fit between corners -> corner_dist is probably too large
    b_crosses_a = (v1.vprod_sign(point_b - point_a) * v1.vprod_sign(point_b_shift - point_a)) < 0
    a_crosses_b = (v3.vprod_sign(point_a - point_b) * v3.vprod_sign(point_a_shift - point_b)) < 0
    if b_crosses_a and a_crosses_b:
        return 1e30  # waveguide is crossing itself -> corner_dist is probably too large

    # Create waveguide and measure it's length
    cell = _var_length_bend(layout, library, corner_dist, point_a, point_a_corner, point_b, point_b_corner, bridges)
    length = get_cell_path_length(cell, layout.layer(default_layers["waveguide_length"]))
    return length


def _var_length_bend(layout, library, corner_dist, point_a, point_a_corner, point_b, point_b_corner, bridges):
    cell = WaveguideComposite.create(layout, library, nodes=[
        Node(point_a, ab_across=bridges.endswith("ends")),
        Node(point_shift_along_vector(point_a, point_a_corner, corner_dist)),
        Node(point_shift_along_vector(point_b, point_b_corner, corner_dist), n_bridges=bridges.startswith("middle")),
        Node(point_b, ab_across=bridges.endswith("ends")),
    ])
    return cell
