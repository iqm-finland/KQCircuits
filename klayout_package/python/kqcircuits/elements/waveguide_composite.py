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
from itertools import zip_longest
from typing import Tuple
from math import pi, tan
from autologging import logged

from scipy.optimize import root_scalar

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.util.library_helper import element_by_class_name
from kqcircuits.util.geometry_helper import vector_length_and_direction, point_shift_along_vector, \
    get_cell_path_length, get_angle, get_direction
from kqcircuits.elements.element import Element
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.elements.meander import Meander
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf


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
        length_before: Length of the waveguide segment before this node
        length_increment: Waveguide length increment produced by meander before this node
        **params: Other optional parameters for the inserted element

    Returns:
        A Node.

    .. MARKERS_FOR_PNG 180,1.2
    """

    position: pya.DPoint
    element: Element
    inst_name: str
    align: Tuple
    angle: float
    length_before: float
    length_increment: float

    def __init__(self, position, element=None, inst_name=None, align=tuple(), angle=None, length_before=None,
                 length_increment=None, **params):
        if isinstance(position, tuple):
            self.position = pya.DPoint(position[0], position[1])
        else:
            self.position = position
        self.element = element
        self.align = align
        self.inst_name = inst_name
        self.angle = angle
        self.length_before = length_before
        self.length_increment = length_increment
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
        if self.length_before is not None:
            magic_params['length_before'] = self.length_before
        if self.length_increment is not None:
            magic_params['length_increment'] = self.length_increment

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
        x, y = float(node[0]), float(node[1])
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
                element = element_by_class_name(element)

        # re-create DPoint from tuple
        magic_params = ('align', 'inst_name', 'angle')
        for pn, pv in params.items():
            if isinstance(pv, tuple) and pn not in magic_params:
                if len(pv) < 2:
                    raise ValueError(f'Point parameter {pn} should have two elements')
                params[pn] = pya.DPoint(float(pv[0]), float(pv[1]))

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


@add_parameters_from(WaveguideCoplanarTaper, taper_length=100)
@add_parameters_from(Airbridge, "airbridge_type")
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

    The ``ab_across=True`` parameter places a single airbridge across the node. The ``n_bridges=N``
    parameter puts N airbridges evenly distributed across the preceding edge.

    The ``length_before`` parameter of a node can be specified to automatically set the length of
    the waveguide between that node and the previous one. It will in fact create a Meander element
    instead of a normal waveguide between those nodes to achieve the correct length. Alternative parameter
    ``length_increment`` sets the waveguide length increment compared to normal waveguide.

    A notable implementation detail is that every Airbridge (sub)class is done as AirbridgeConnection.
    This way a waveguide taper is automatically inserted before and after the airbridge so the user
    does not have to manually add these. Other Node types do not have this feature.

    A WaveguideComposite cell has a method ``segment_lengths`` that returns a list of lengths of each individual
    regular waveguide segment. Segments are bounded by any element that is not a standard waveguide, such as Airbridge,
    flip chip, taper or any custom element.

    For examples see the test_waveguide_composite.lym script.
    """

    nodes = Param(pdt.TypeString, "List of Nodes for the waveguide", "(0, 0, 'Airbridge'), (200, 0)")
    enable_gui_editing = Param(pdt.TypeBoolean, "Enable GUI editing of the waveguide path", True)
    gui_path = Param(pdt.TypeShape, "", pya.DPath([pya.DPoint(0, 0), pya.DPoint(200, 0)], 1))
    gui_path_shadow = Param(pdt.TypeShape, "Hidden path to detect GUI operations",
                            pya.DPath([pya.DPoint(0, 0), pya.DPoint(200, 0)], 1), hidden=True)
    tight_routing = Param(pdt.TypeBoolean, "Tight routing for corners", False)

    @classmethod
    def create(cls, layout, library=None, **parameters):
        # For code-generated cells, make sure the gui path matches te node definition.
        if parameters.get("enable_gui_editing", True):
            if "nodes" in parameters:
                path = pya.DPath([node.position for node in parameters["nodes"]], 1)
                # Round to database units since the KLayout partial tool also works in database units
                path = path.to_itype(layout.dbu).to_dtype(layout.dbu)
                parameters["gui_path"] = path
                parameters["gui_path_shadow"] = path
        else:
            parameters["gui_path"] = pya.DPath()
            parameters["gui_path_shadow"] = pya.DPath()

        cell = super().create(layout, library, **parameters)
        setattr(cell, "segment_lengths", lambda: WaveguideComposite.get_segment_lengths(cell))

        return cell

    @staticmethod
    def get_segment_cells(cell):
        """Get the subcells of a ``WaveguideComposite`` cell, ordered by node index.

        The subcells include ``WaveguideCoplanar``, ``WaveguideCoplanarTaper`` and ``Meander`` cells for straight,
        tapered and meandering segments, respectively, and any element cells that were inserted explicitly
        (``element`` argument) or implicitly (changing ``a``, ``b`` or ``face_id``) at any ``Node``.

        The ``node_index`` returned with each subcell is an index to the ``nodes`` parameter of the
        ``WaveguideComposite`` cell. It points to the node that _created_ the subcell, which is the node following a
        segment for regular ``WaveguideCoplanar`` segments, and the node that specified the element or parameter change
        otherwise.

        Note that there may be multiple subcells per node, and some nodes may not have associated subcells (in
        particular, regular ``WaveguideCoplanar`` segments are merged when possible). Subscells are returned in the
        order in which they appear in the waveguide.

        Args:
            cell: A WaveguideComposite cell. Can be a PCell or static cell created from a PCell.

        Returns: A list of tuples (node_index: int, subcell: pya.Cell) ordered by node_index.
        """
        layout = cell.layout()

        segment_data = []

        for inst in cell.each_inst():
            # Note: Using layout.cell(inst.cell_index) instead of inst.cell to work around KLayout issue #235
            child_cell = layout.cell(inst.cell_index)

            node_index = inst.property("waveguide_composite_node_index")
            if node_index is not None:
                segment_data.append((node_index, child_cell))

        return list(sorted(reversed(segment_data), key=lambda x: x[0]))

    @staticmethod
    def get_segment_lengths(cell):
        """ Retrieves the segment lengths of each waveguide segment in a WaveguideComposite cell.

        Waveguide segments are ``WaveguideCoplanar``, ``WaveguideCoplanarTaper`` and ``Meander`` subcells.
        This method returns a list with the same length as the ``nodes`` parameter, where each element is the total
        length of all waveguides directly preceding and/or defined in that node. For example, for a taper node both the
        preceding regular waveguide and the taper itself are counted.

        Note that ``WaveguideComposite`` merges consecutive waveguide segments if they have no special elements. As
        a consequence, the corresponding waveguide lengths all accumulate in the next index which has a taper, meander
        or other element, and the length for nodes that contain ony ``WaveguideCoplanar`` is reported as 0.

        Args:
            cell: A WaveguideComposite cell. Can be a PCell or static cell created from a PCell.

        Returns: A list waveguide lengths per node
        """

        # Measure segment lengths, counting only "regular waveguides"
        waveguide_segment_types = {"Waveguide Coplanar", "Waveguide Coplanar Taper", "Meander"}

        segment_data = WaveguideComposite.get_segment_cells(cell)
        if len(segment_data) == 0:
            return []

        segment_lengths = [0] * (segment_data[-1][0] + 1)
        for node_index, child_cell in segment_data:
            if child_cell.name.split('$')[0] in waveguide_segment_types:
                segment_lengths[node_index] += get_cell_path_length(child_cell)

        return segment_lengths

    @staticmethod
    def produce_fixed_length_waveguide(chip, route_function, initial_guess=0.0, length=0.0, **waveguide_params):
        """
        Produce a waveguide composite with fixed length. `route_function` should be a single-argument function that
        returns route, and its argument is an adjustable length in µm.
        Note that this is not a minimization, but a single-step adjustment that only corrects for the offset in
        length.

        Args:
            chip: Chip in which the element is added (self if called within chip code)
            route_function: a function lambda x: [Node(f(x))...] where x can be for instance a meander length or a
            DPoint coordinate (if more than one component is tuned in the Node list, the correction length must be
            weighted)
            initial_guess: float that allows to draw an initial waveguide of a reasonable length
            length: target desired length for the final waveguide
            waveguide_params: kwargs to be passed to the WaveguideComposite element, such as a, b, term1, term2 etc.

        Returns: The waveguide instance, refpoints and the final length
        """

        wg_tmp = chip.add_element(WaveguideComposite, nodes=[
            *route_function(initial_guess),
        ], **waveguide_params)
        offset_length = wg_tmp.length()
        correction = length - offset_length
        wg = chip.add_element(WaveguideComposite, nodes=[
            *route_function(correction+initial_guess),
        ], **waveguide_params)
        inst, ref = chip.insert_cell(wg)
        return inst, ref, wg.length()

    def snap_point(self, point: pya.DPoint) -> pya.DPoint:  # pylint: disable=no-self-use
        """
        Interface to define snap behavior for GUI editing in derived classes.

        Args:
            point: DPoint that has been moved in the GUI

        Returns: DPoint representing the snapped location for the input point. Return the point unmodified if no
            snapping is required
        """

        # Default implementation always returns
        return point

    def coerce_parameters_impl(self):
        if self.enable_gui_editing:
            nodes = Node.nodes_from_string(self.nodes)

            # If gui_path was edited by the user, it is now different from gui_path_shadow. Detect changes
            changed = self.gui_path != self.gui_path_shadow

            if changed:
                new_points = list(self.gui_path.each_point())
                old_points = list(self.gui_path_shadow.each_point())

                length_change = len(new_points) - len(old_points)
                if length_change == 0:
                    # One or more points were moved; update node positions of the moved points
                    for node, new_position, old_position in zip(nodes, new_points, old_points):
                        if new_position != old_position:
                            new_position = self.snap_point(new_position)
                            node.position = new_position
                    self.nodes = [str(node) for node in nodes]
                elif length_change == 1:
                    # One node was added. Figure out which node it was.
                    added_index = None
                    added_point = None
                    for i, (new_point, old_point) in enumerate(zip_longest(new_points, old_points)):
                        if old_point is None or new_point != old_point:
                            added_index = i
                            added_point = new_point
                            break

                    if added_index is not None:
                        nodes.insert(added_index, Node(added_point))
                        self.nodes = [str(node) for node in nodes]
                elif length_change < 0 and self.gui_path.num_points() >= 2:
                    # One or more points deleted; delete corresponding nodes. We require at least two remaining nodes.
                    remaining_indices = []
                    new_indices = []

                    for i, old_point in enumerate(old_points):
                        if old_point in new_points:
                            remaining_indices.append(i)
                            new_indices.append(new_points.index(old_point))

                    # Verify we found the right number of remaining indices, and the order is correct
                    new_indices_monotonic = all(i < j for i, j in zip(new_indices, new_indices[1:]))
                    if len(remaining_indices) == len(new_points) and new_indices_monotonic:
                        nodes = [nodes[i] for i in remaining_indices]
                        self.nodes = [str(node) for node in nodes]

            # After coerce the gui_path and gui_path_shadow should both match the nodes.
            new_path = pya.DPath([node.position for node in nodes], 1)
            # Force rounding to integer database units since the KLayout Partial tool also rounds to database units.
            new_path = new_path.to_itype(self.layout.dbu).to_dtype(self.layout.dbu)
            self.gui_path = new_path
            self.gui_path_shadow = new_path
        else:
            # Use an empty path to disable editing with the Partial tool
            self.gui_path = pya.DPath()
            self.gui_path_shadow = pya.DPath()

        super().coerce_parameters_impl()

    def build(self):
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
                             f' {node.params}')
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


    def _add_taper(self, ind):
        """Create a WaveguideCoplanarTaper and change default a/b."""

        node = self._nodes[ind]

        params = {**self.pcell_params_by_name(WaveguideCoplanarTaper), **node.params}
        a, b = params.pop('a', self.a), params.pop('b', self.b)
        if self.a == a and self.b == b: # no change, just a Node
            return

        taper_cell = self.add_element(WaveguideCoplanarTaper, **{**params, 'a2': a, 'b2': b, 'm2': self.margin})
        self._insert_cell_and_waveguide(ind, taper_cell)

        self.a = a
        self.b = b

    def _add_fc_bump(self, ind):
        """Add FlipChipConnectorRF and change default face_id."""
        node = self._nodes[ind]
        if "face_id" not in node.params:
            node.params["face_id"] = self.face_ids[1]
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
                  'a2': self.a, 'b2': self.b, 'm2': self.margin,
                  'taper_length': AirbridgeConnection.taper_length,
                  **node.params}

        a, b = params.pop('a', self.a), params.pop('b', self.b)

        if ind == 0:  # set temporary private variables used in _terminator()
            self._ta, self._tb = self.a, self.b

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
        cell_inst, ref = self.insert_cell(cell, trans)
        cell_inst.set_property("waveguide_composite_node_index", ind)
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

    def _insert_wg_cell(self, points, start_index, end_index):
        """Create and insert waveguide cell.
        Avoid termination if in the middle or if the ends are actual elements.
        """
        if len(points) < 2:
            return
        params = {**self.pcell_params_by_name(WaveguideCoplanar), "path": points}
        if start_index != 0 or self._nodes[start_index].element:
            params['term1'] = 0
        if end_index != len(self._nodes) - 1 or self._nodes[end_index].element:
            params['term2'] = 0
        wg_cell = self.add_element(WaveguideCoplanar, **params)
        cell_inst, _ = self.insert_cell(wg_cell)
        cell_inst.set_property("waveguide_composite_node_index", end_index)

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

        def curve_length_and_end_points(pnts, p):
            """Returns curve length, curve start point, and curve end point, for given point pnts[p] in list pnts."""
            if p == 0 or p + 1 >= len(pnts):
                return 0.0, pnts[p], pnts[p]
            v1, v2, alpha1, alpha2, _ = WaveguideCoplanar.get_corner_data(pnts[p-1], pnts[p], pnts[p+1], self.r)
            abs_turn = pi - abs(pi - abs(alpha2 - alpha1))
            cut_dist = self.r * tan(abs_turn / 2)
            return self.r * abs_turn, pnts[p] + (-cut_dist / v1.length()) * v1, pnts[p] + (cut_dist / v2.length()) * v2

        # Create waveguide path and create airbridges determined by parameter `n_bridges`.
        points = [self._wg_start_pos]
        straights = {}
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
            straights[i + 1] = len(points)
            points.append(pos1 + (-len1) * dir1)

            # Add final point if it's not already added
            if i + 1 == end_index and len1 > 0:
                points.append(pos1)

        # Create and insert waveguide cell from points
        # Possibly insert meanders or airbridges on straights
        # Inserting meanders requires splitting of waveguide
        p0 = 0
        n0 = start_index
        point0 = []
        for n1, p1 in straights.items():
            node1 = self._nodes[n1]
            if node1.length_before is not None or node1.length_increment is not None:
                start_len, turn_start, meander_start = curve_length_and_end_points(points, p1-1)
                end_len, meander_end, turn_end = curve_length_and_end_points(points, p1)
                if node1.length_increment is not None:
                    meander_len = (meander_end - meander_start).length() + node1.length_increment
                else:
                    meander_len = node1.length_before
                    if n1 == end_index:
                        meander_len -= end_len + (points[-1] - turn_end).length()
                    elif node1.angle is None:
                        meander_len -= end_len / 2
                    else:
                        meander_len -= end_len + (node1.position - turn_end).length()
                    if n1 - 1 == start_index:
                        meander_len -= start_len + (points[0] - turn_start).length()
                    elif self._nodes[n1-1].angle is None:
                        meander_len -= start_len / 2
                    else:
                        meander_len -= start_len + (self._nodes[n1-1].position - turn_start).length()

                cell_inst, _ = self.insert_cell(Meander, start=[meander_start.x, meander_start.y],
                                                end=[meander_end.x, meander_end.y], length=meander_len, **node1.params)
                cell_inst.set_property("waveguide_composite_node_index", end_index)
                wg_points = point0 + points[p0:p1] + ([] if start_len < 1e-4 else [meander_start])
                self._insert_wg_cell(wg_points, n0, n1)
                n0 = n1
                p0 = p1
                point0 = [] if end_len < 1e-4 else [meander_end]
            elif "n_bridges" in node1.params and node1.params["n_bridges"] > 0:
                ab_len = node1.params['bridge_length'] if "bridge_length" in node1.params else None
                self._ab_across(points[p1-1], points[p1], node1.params["n_bridges"], ab_len)
        self._insert_wg_cell(point0 + points[p0:], n0, end_index)

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
    return get_cell_path_length(cell)


def _var_length_bend(layout, library, corner_dist, point_a, point_a_corner, point_b, point_b_corner, bridges):
    cell = WaveguideComposite.create(layout, library, nodes=[
        Node(point_a, ab_across=bridges.endswith("ends")),
        Node(point_shift_along_vector(point_a, point_a_corner, corner_dist)),
        Node(point_shift_along_vector(point_b, point_b_corner, corner_dist), n_bridges=bridges.startswith("middle")),
        Node(point_b, ab_across=bridges.endswith("ends")),
    ])
    return cell
