# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from enum import Enum
import math

from scipy.optimize import root_scalar

from kqcircuits.pya_resolver import pya
from kqcircuits.defaults import default_layers
from kqcircuits.elements.element import Element
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.elements.airbridge import Airbridge
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.flip_chip_connector.flip_chip_connector_rf import FlipChipConnectorRf
from kqcircuits.util.geometry_helper import point_shift_along_vector


class NodeType(Enum):
    WAVEGUIDE = "wg"
    """Node of the waveguide.

    If not first or last in the series of WAVEGUIDE nodes, then will likely become a curve
    """

    AB_SERIES_SET = "abSeriesSet"
    """Set of three parallel airbridges in series.

    End of the airbridge if first or last element, otherwise center of the airbridge
    """

    AB_SERIES_SINGLE = "abSeriesSingle"
    """Airbridge in series.

    End of the airbridge if first or last element, otherwise center of the airbridge.
    """

    AB_CROSSING_BEFORE = "abCrossingBefore"
    """Node for the waveguide, where last segment will have a airbridge in the middle.

    Should not be first node.
    """

    AB_CROSSING = "abCrossing"
    """Airbridge will cross here, it is only assumed that the waveguide will pass from under."""

    FC_BUMP = "fcBump"
    """Flip-chip Bump bonding.

    Node for flip-chip connection, which automatically changes the active face for consecutive nodes.
    Should not be first of last node.
    """

    @classmethod
    def from_string(cls, type_str: str):
        return cls._value2member_map_[type_str]

    def __str__(self):
        return self.value


class Node:
    """Specifies a single node of a bridged coplanar waveguide.

    Includes a function which allows it to be generated from a string.
    """
    position: pya.DPoint
    type: NodeType
    a: float  # for end nodes
    b: float  # for end nodes
    n_bridges: int  # for AB_CROSSING_BEFORE

    def __init__(self, node_type: NodeType, position: pya.DPoint, a: float = None, b: float = None, n_bridges: int = 1):
        self.type = node_type
        self.position = position
        self.a = a
        self.b = b
        self.n_bridges = n_bridges

    @classmethod
    def from_string(cls, node_def_string: str):
        """Needed for storage in KLayout parameters.

        Arguments:
            node_def_string: Specifies nodes in a format `{node_type};{location};{a};{b}`,
                for example `wg; 0,0; 10, 12`. See `NodeType` for possible string values of `node_type`.
        """
        type_str, pos_str, a, b, n_bridges = node_def_string.split(";")

        def to_float(s):
            if s.strip() == "None":
                return None
            elif s.strip() == "(nil)":
                return None
            else:
                return float(s)

        return cls(NodeType.from_string(type_str), pya.DPoint.from_s(pos_str), to_float(a), to_float(b), int(n_bridges))

    def __str__(self):
        """Needed for storage in KLayout parameters."""
        return "{}; {}; {}; {}; {}".format(self.type, self.position, self.a, self.b, self.n_bridges)


class WaveguideCoplanarBridged(Element):
    """PCell definition for a set of coplanar waveguides with airbridge connections for signals
    and grounds
    """

    PARAMETERS_SCHEMA = {
        "nodes": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "List of nodes for the waveguide",
            "default": [()]
        },
        "bridge_width_series": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Width of the airbridges in series",
            "default": None
        },
        "bridge_length_series": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Length of the airbridge in series",
            "default": None
        },
        "term1": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Termination length start [μm]",
            "default": 0
        },
        "term2": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Termination length end [μm]",
            "default": 0
        },
        "connector_type": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Face to face connector type",
            "default": "Coax",
            "choices": [["Single", "Single"], ["GSG", "GSG"], ["Coax", "Coax"]]
        },
        "taper_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Taper length",
            "default": 100,
        },
    }

    def produce_impl(self):
        if type(self.nodes[0]) is str:
            nodes = [Node.from_string(s) for s in self.nodes]
        else:
            nodes = self.nodes

        self._produce_crossing_waveguide(nodes)

    get_length = WaveguideCoplanar.get_length

    def _produce_crossing_waveguide(self, nodes):
        """Helper function for adding waveguide with airbridge connections for signals or grounds.

        Attributes:
            nodes: list of Node objects
        """
        # default value for face index
        active_face_idx = 0

        # airbridge
        pad_length = 14
        pad_extra = 2
        self.ab_params = {
            "pad_length": pad_length,
            "pad_extra": pad_extra,
        }
        if self.bridge_width_series not in [None, 'nil']:
            self.ab_params["bridge_width"] = self.bridge_width_series
            self.ab_params["pad_width"] = self.bridge_width_series
        if self.bridge_length_series not in [None, 'nil']:
            self.ab_params["bridge_length"] = self.bridge_length_series

        termination_settings = {}

        # handle first node
        # special, since series airbridge connections at the start are handled differently
        if nodes[0].type in [NodeType.AB_SERIES_SET, NodeType.AB_SERIES_SINGLE]:
            ab_start_point, first_path_point = self._produce_airbridge_connection(nodes[0], nodes[1],
                                                                                  center_placing=False)
            tl_path = [first_path_point]
        else:
            tl_path = [nodes[0].position]  # TODO, implement end node tapering
            termination_settings["term1"] = self.term1
            if nodes[0].type == NodeType.AB_CROSSING:
                self._produce_airbridge_crossing(nodes[1], nodes[0], before_node=False)

        # we keep track of a and b which are used until a node redefines them
        # here they are initialized based on first node
        old_a, old_b = a, b = self.a, self.b
        if nodes[0].type in [NodeType.WAVEGUIDE, NodeType.AB_CROSSING_BEFORE]:
            if nodes[0].a is not None:
                old_a = a = nodes[0].a
            if nodes[0].b is not None:
                old_b = b = nodes[0].b

        # we assume at least three nodes
        # first node is handled
        # last node will be handled later
        for last_node, node, next_node in zip(nodes[0:-2], nodes[1:-1], nodes[2:]):

            if node.type in [NodeType.WAVEGUIDE, NodeType.AB_CROSSING_BEFORE]:

                # handle the possible redefinition of a and b in the node
                changed_a = changed_b = False
                if (node.a is not None) and (node.a != old_a):
                    changed_a = True
                    a = node.a
                if (node.b is not None) and (node.b != old_b):
                    changed_b = True
                    b = node.b

                # add tapering if a and b change
                if (changed_a or changed_b) and node.type in [NodeType.WAVEGUIDE, NodeType.AB_CROSSING_BEFORE]:
                    start_next_pos = self._produce_waveguide_taper(last_node, node, tl_path, old_a, old_b, a,
                                                                   b, active_face_idx, termination_settings)
                    old_a = a
                    old_b = b
                    tl_path = [start_next_pos]
                else:
                    tl_path.append(node.position)

                if node.type == NodeType.AB_CROSSING_BEFORE:
                    self._produce_airbridge_crossing(last_node, node, before_node=True)

            elif node.type is NodeType.AB_CROSSING:
                self._produce_airbridge_crossing(last_node, node, before_node=False)
            elif node.type in [NodeType.AB_SERIES_SET, NodeType.AB_SERIES_SINGLE, NodeType.FC_BUMP]:
                # place the airbridge at the node in the direction of the last waveguide
                # this effectively assumes, that last and next segment are collinear
                if node.type is NodeType.FC_BUMP:
                    end_last_pos, start_next_pos = self._produce_flip_chip_crossing(last_node, node, active_face_idx,
                                                                                    a, b)
                else:
                    end_last_pos, start_next_pos = self._produce_airbridge_connection(node, next_node)

                # finish the waveguide
                tl_path.append(end_last_pos)
                wg = self.add_element(WaveguideCoplanar, **{**self.cell.pcell_parameters_by_name(), **{
                    "path": pya.DPath(tl_path, 1),
                    "face_ids": self.face_ids[active_face_idx],
                    "a": a,
                    "b": b,
                    **termination_settings
                }})
                self.insert_cell(wg)

                termination_settings = {}  # reset

                # start new waveguide
                tl_path = [start_next_pos]

                # switch active face between 0 and 1
                if node.type is NodeType.FC_BUMP:
                    active_face_idx = 1 - active_face_idx
            else:
                raise ValueError("Unknown node type {}".format(node.type))

        # finish the last waveguide
        # handle the airbridge connection in the end of the waveguide
        if nodes[-1].type in [NodeType.AB_SERIES_SET, NodeType.AB_SERIES_SINGLE]:
            ab_end_point, last_path_point = self._produce_airbridge_connection(nodes[-1], nodes[-2],
                                                                               center_placing=False)
            tl_path.append(last_path_point)
        else:
            if nodes[-1].type == NodeType.AB_CROSSING_BEFORE:
                self._produce_airbridge_crossing(nodes[-2], nodes[-1], before_node=True)
            if nodes[-1].type == NodeType.AB_CROSSING:
                self._produce_airbridge_crossing(nodes[-2], nodes[-1], before_node=False)
            tl_path.append(nodes[-1].position)
            termination_settings["term2"] = self.term2
        wg = self.add_element(WaveguideCoplanar, **{**self.cell.pcell_parameters_by_name(), **{
            "path": pya.DPath(tl_path, 1),
            "a": a,
            "b": b,
            "face_ids": self.face_ids[active_face_idx],
            **termination_settings
        }})

        self.insert_cell(wg)

    def _produce_flip_chip_crossing(self, last_node, node, face_idx, a, b):
        fc_cell = self.add_element(FlipChipConnectorRf,
                                connector_type=self.connector_type,
                                face_ids=[self.face_ids[face_idx], self.face_ids[1 - face_idx]],
                                a=a, b=b)
        v_dir = node.position - last_node.position
        alpha = math.atan2(v_dir.y, v_dir.x)
        fc_trans = pya.DCplxTrans(1, alpha / math.pi * 180., False, node.position)
        fc_inst, fc_abs_ref = self.insert_cell(fc_cell, fc_trans)
        return fc_abs_ref["{}_port".format(self.face_ids[face_idx])], fc_abs_ref[
            "{}_port".format(self.face_ids[1 - face_idx])]

    def _produce_airbridge_crossing(self, last_node, node, before_node=True):
        """
        If before node=True, creates node.n_bridge airbridge crossings equally distributed between last_node.position
        and node.position. Otherwise creates an airbridge crossing at node.
        """
        ab_cell = self.add_element(Airbridge, **{
            "with_side_airbridges": True, **self.ab_params,
        })

        v_dir = node.position - last_node.position
        alpha = math.atan2(v_dir.y, v_dir.x)

        if before_node:
            n = node.n_bridges
            for i in range(1, n + 1):
                ab_trans = pya.DCplxTrans(1, alpha / math.pi * 180., False, last_node.position + i * v_dir / (n + 1))
                self.insert_cell(ab_cell, ab_trans)
        else:
            ab_trans = pya.DCplxTrans(1, alpha / math.pi * 180., False, node.position)
            self.insert_cell(ab_cell, ab_trans)

    def _produce_waveguide_taper(self, last_node, node, tl_path, old_a, old_b, current_a, current_b, active_face_idx,
                                 termination_settings):
        """Produces a waveguide taper starting at node.position.

        Returns:
            DPoint at `port_b` of the waveguide taper.
        """
        tl_path.append(node.position)
        wg = self.add_element(WaveguideCoplanar, **{**self.cell.pcell_parameters_by_name(), **{
            "path": pya.DPath(tl_path, 1),
            "face_ids": self.face_ids[active_face_idx],
            "a": old_a,
            "b": old_b,
            **termination_settings
        }})
        self.insert_cell(wg)

        taper_cell = self.add_element(WaveguideCoplanarTaper,
            taper_length=self.taper_length,
            a1=old_a,
            b1=old_b,
            m1=self.margin,
            a2=current_a,
            b2=current_b,
            m2=self.margin,
        )

        v_dir = node.position - last_node.position
        alpha = math.atan2(v_dir.y, v_dir.x)
        taper_trans = pya.DCplxTrans(1, alpha / math.pi * 180., False, node.position)
        taper_inst, taper_ref = self.insert_cell(taper_cell, taper_trans)

        return taper_ref["port_b"]

    def _produce_airbridge_connection(self, node_a, node_b, center_placing=True):
        """Helper for adding airbridge connection at node_a towards node_b.

        Node_a is assumed to be of airbridge_series type.

        Returns:
            DPoints at `port_a` and `port_b` of the airbridge connection at `node_a`.
        """
        ab_wg_params = {
            "a": self.a,
            "a1": self.a,
            "a2": self.a,
            "b1": self.b,
            "b2": self.b,
            "b": self.b
        }

        if node_a.a is not None:
            ab_wg_params["a1"] = node_a.a
            ab_wg_params["a"] = node_a.a

        if node_a.b is not None:
            ab_wg_params["b1"] = node_a.b
            ab_wg_params["b"] = node_a.b

        if node_a.type is NodeType.AB_SERIES_SET:
            ab_cell = self.add_element(AirbridgeConnection, **{
                **ab_wg_params, "with_side_airbridges": True, **self.ab_params,
            })
        else:
            ab_cell = self.add_element(AirbridgeConnection, **{
                **ab_wg_params, "with_side_airbridges": False, **self.ab_params,
            })
        ab_rel_ref = self.get_refpoints(ab_cell, rec_levels=0)

        v_dir = node_b.position - node_a.position
        alpha = math.atan2(v_dir.y, v_dir.x)

        if center_placing:
            # node_a at the center
            ab_trans = pya.DCplxTrans(1, alpha / math.pi * 180., False, node_a.position)
        else:
            # node_a at the start
            ab_trans = pya.DCplxTrans(1, alpha / math.pi * 180., False, node_a.position) * pya.DTrans(
                -ab_rel_ref["port_a"])

        ab_inst, ab_abs_ref = self.insert_cell(ab_cell, ab_trans)
        ab_abs_ref_top = self.get_refpoints(ab_cell, ab_inst.dcplx_trans, rec_levels=0)

        return ab_abs_ref_top["port_a"], ab_abs_ref_top["port_b"]  # TODO implement corners


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
    length = WaveguideCoplanarBridged.get_length(
        cell, layout.layer(default_layers["annotations"]))
    return length


def _var_length_bend(layout, corner_dist, point_a, point_a_corner, point_b, point_b_corner, bridges):
    cell = WaveguideCoplanarBridged.create(layout, nodes=[
        Node(NodeType.AB_CROSSING if bridges == "middle and ends" else NodeType.WAVEGUIDE, point_a),
        Node(NodeType.WAVEGUIDE,
             point_shift_along_vector(point_a, point_a_corner, distance=corner_dist)),
        Node(NodeType.AB_CROSSING_BEFORE if bridges.startswith("middle") else NodeType.WAVEGUIDE,
             point_shift_along_vector(point_b, point_b_corner, distance=corner_dist)),
        Node(NodeType.AB_CROSSING if bridges == "middle and ends" else NodeType.WAVEGUIDE, point_b)
    ])
    return cell
