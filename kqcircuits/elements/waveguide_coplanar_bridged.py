# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from enum import Enum
import math
from kqcircuits.pya_resolver import pya
from kqcircuits.elements.element import Element
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.elements.airbridge import Airbridge
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar


class NodeType(Enum):
    WAVEGUIDE = "wg"
    """ Node of the waveguide 
    If not first or last in the series of WAVEGUIDE nodea, then will likely become a curve
    """

    AB_SERIES_SET = "abSeriesSet"
    """ Set of three parallel airbridges in series 
    End of the airbridge if first or last element, otherwise center of the airbridge
    """

    AB_SERIES_SINGLE = "abSeriesSingle"
    """ Airbridge in series 
    End of the airbridge if first or last element, otherwise center of the airbridge
    """

    AB_CROSSING_BEFORE = "abCrossingBefore"
    """ Node for the waveguide, where last segment will have a airbridge in the middle. 
    Should not be first node.
    """

    AB_CROSSING = "abCrossing"
    """ Airbridge will cross here, it is only assumed that the waveguide will pass from under. 
    Should not be first or last node.
    """

    @classmethod
    def from_string(cls, type_str: str):
        return cls._value2member_map_[type_str]

    def __str__(self):
        return self.value


class Node:
    """ Specifies a single node of a bridged coplanar waveguide.

     Includes a function which allows it to be generated from a string."""
    position: pya.DPoint
    type: NodeType
    a: float  # for end nodes
    b: float  # for end nodes

    def __init__(self, node_type: NodeType, position: pya.DPoint, a: float = None, b: float = None):
        self.type = node_type
        self.position = position
        self.a = a
        self.b = b

    @classmethod
    def from_string(cls, node_def_string: str):
        """Needed for storage in KLayout parameters

        Arguments:
            node_def_string: Specifies nodes in a format `{node_type};{location};{a};{b}`,
            for example `wg; 0,0; 10, 12`. See `NodeType` for possible string values of `node_type`.
        """
        type_str, pos_str, a, b = node_def_string.split(";")
        
        def to_float(s):
            if s.strip() == "None":
                return None
            elif s.strip() == "(nil)":
                return None
            else:
                return float(s)
        
        return cls(NodeType.from_string(type_str), pya.DPoint.from_s(pos_str), to_float(a), to_float(b))

    def __str__(self):
        """Needed for storage in KLayout parameters
        """
        return "{}; {}; {}; {}".format(self.type, self.position, self.a, self.b)


class WaveguideCoplanarBridged(Element):
    """ PCell definition for a set of coplanar waveguides with airbridge connections for signals
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
        }
    }

    def produce_impl(self):
        if type(self.nodes[0]) is str:
            nodes = [Node.from_string(s) for s in self.nodes]
        else:
            nodes = self.nodes

        self._produce_crossing_waveguide(nodes)

    def _produce_crossing_waveguide(self, nodes):
        """ Helper function for adding waveguide with airbridge connections for signals or grounds

        Attributes:
            nodes: list of Node objects
        """

        # airbridge
        pad_length = 14
        pad_extra = 2
        self.ab_params = {
            "pad_length": pad_length,
            "pad_extra": pad_extra
        }
        if self.bridge_width_series not in [None, 'nil']:
            self.ab_params["bridge_width"] = self.bridge_width_series
            self.ab_params["pad_width"] = self.bridge_width_series
        if self.bridge_length_series not in [None, 'nil']:
            self.ab_params["bridge_length"] = self.bridge_length_series

        # handle first node
        # special, since series airbridge connections at the start are handled differently
        if nodes[0].type in [NodeType.AB_SERIES_SET, NodeType.AB_SERIES_SINGLE]:
            ab_start_point, first_path_point = self._produce_airbridge_connection(nodes[0], nodes[1],
                                                                                  center_placing=False)
            tl_path = [first_path_point]
        else:
            tl_path = [nodes[0].position]  # TODO, implement end node tapering
            
        # we assume at least three nodes
        # first node is handled
        # last node will be handled later
        for last_node, node, next_node in zip(nodes[0:-2], nodes[1:-1], nodes[2:]):
            if node.type in [NodeType.WAVEGUIDE, NodeType.AB_CROSSING_BEFORE]:
                # just a kink in the waveguide
                tl_path.append(node.position)
                if node.type is NodeType.AB_CROSSING_BEFORE:
                    self._produce_airbridge_crossing(last_node, node, center_placing=True)
            elif node.type is NodeType.AB_CROSSING:
                self._produce_airbridge_crossing(last_node, node, center_placing=False)
            elif node.type in [NodeType.AB_SERIES_SET, NodeType.AB_SERIES_SINGLE]:
                # place the airbridge at the node in the direction of the last waveguide
                # this effectively assumes, that last and next segment are collinear
                end_last_pos, start_next_pos = self._produce_airbridge_connection(node, next_node)

                # finish the waveguide
                tl_path.append(end_last_pos)
                wg = WaveguideCoplanar.create_cell(self.layout, {**self.cell.pcell_parameters_by_name(), **{
                    "path": pya.DPath(tl_path, 1),
                }})
                self.insert_cell(wg)

                # start new waveguide
                tl_path = [start_next_pos]
            else:
                raise ValueError("Unknown node type {}".format(node.type))

        # finish the last waveguide
        # handle the airbridge connection in the end of the waveguide
        if nodes[-1].type in [NodeType.AB_SERIES_SET, NodeType.AB_SERIES_SINGLE]:
            ab_end_point, last_path_point = self._produce_airbridge_connection(nodes[-1], nodes[-2],
                                                                               center_placing=False)
            tl_path.append(last_path_point)
        else:
            tl_path.append(nodes[-1].position)        
            
        wg = WaveguideCoplanar.create_cell(self.layout, {**self.cell.pcell_parameters_by_name(), **{
            "path": pya.DPath(tl_path, 1),
        }})
        self.insert_cell(wg)

    def _produce_airbridge_crossing(self, last_node, node, center_placing=True):
        ab_cell = Airbridge.create_cell(self.layout, {
            "with_side_airbridges": True, **self.ab_params,
        })

        v_dir = node.position - last_node.position
        alpha = math.atan2(v_dir.y, v_dir.x)

        if center_placing:
            ab_trans = pya.DCplxTrans(1, alpha / math.pi * 180., False, last_node.position + v_dir/2)
        else:
            ab_trans = pya.DCplxTrans(1, alpha / math.pi * 180., False, node.position)

        self.insert_cell(ab_cell, ab_trans)

    def _produce_airbridge_connection(self, node_a, node_b, center_placing=True):
        """Helper for adding airbridge connection at node_a towards node_b.

        Node_a is assumed to be of airbridge_series type.

        Returns:
            DPoints at `port_a` and `port_b` of the airbridge connection at `node_a`.
        """
        ab_wg_params = {"a2": self.a, "b2": self.b}

        if node_a.a is None:
            ab_wg_params["a1"] = self.a
        else:
            ab_wg_params["a1"] = node_a.a

        if node_a.b is None:
            ab_wg_params["b1"] = self.b
        else:
            ab_wg_params["b1"] = node_a.b

        if node_a.type is NodeType.AB_SERIES_SET:
            ab_cell = AirbridgeConnection.create_cell(self.layout, {
               **ab_wg_params, "with_side_airbridges": True, **self.ab_params,
                })
        else:
            ab_cell = AirbridgeConnection.create_cell(self.layout, {
               **ab_wg_params,  "with_side_airbridges": False, **self.ab_params,
                })
        ab_rel_ref = self.get_refpoints(ab_cell, rec_levels=0)

        v_dir = node_b.position - node_a.position
        alpha = math.atan2(v_dir.y, v_dir.x)

        if center_placing:
            # node_a at the center
            ab_trans = pya.DCplxTrans(1, alpha / math.pi * 180., False, node_a.position)
        else:
            # node_a at the start
            ab_trans = pya.DCplxTrans(1, alpha / math.pi * 180., False, node_a.position)*pya.DTrans(-ab_rel_ref["port_a"])

        ab_inst, ab_abs_ref = self.insert_cell(ab_cell, ab_trans)
        ab_abs_ref_top = self.get_refpoints(ab_cell, ab_inst.dcplx_trans, rec_levels=0)

        return ab_abs_ref_top["port_a"], ab_abs_ref_top["port_b"]  # TODO implement corners
