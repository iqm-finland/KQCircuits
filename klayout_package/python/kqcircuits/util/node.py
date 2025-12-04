# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

import ast
from typing import Tuple, Type

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.element import Element
from kqcircuits.util.library_helper import element_by_class_name

from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter

# Speed up lookup for elements most commonly used as Node.element
COMMON_ELEMENTS = {
    cls.__name__: cls for cls in [Airbridge, AirbridgeConnection, FlipChipConnectorRf, WaveguideCoplanarSplitter]
}


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
    """

    position: pya.DPoint
    element: Type[Element] | None
    inst_name: str | None
    align: Tuple
    angle: float | None
    length_before: float | None
    length_increment: float | None
    meander_direction: int

    def __init__(
        self,
        position: pya.DPoint,
        element: Type[Element] | None = None,
        inst_name: str | None = None,
        align: tuple = tuple(),
        angle: float | None = None,
        length_before: float | None = None,
        length_increment: float | None = None,
        meander_direction: int = 1,
        **params,
    ):
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
        self.meander_direction = meander_direction
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
            magic_params["align"] = self.align
        if self.inst_name:
            magic_params["inst_name"] = self.inst_name
        if self.angle is not None:
            magic_params["angle"] = self.angle
        if self.length_before is not None:
            magic_params["length_before"] = self.length_before
        if self.length_increment is not None:
            magic_params["length_increment"] = self.length_increment
        if self.meander_direction != 1:
            magic_params["meander_direction"] = self.meander_direction

        all_params = {**self.params, **magic_params}
        if all_params:
            for pn, pv in all_params.items():
                if isinstance(pv, pya.DPoint):  # encode DPoint as tuple
                    all_params[pn] = (pv.x, pv.y)
            txt += f", {all_params}"
        return "(" + txt + ")"

    @classmethod
    def deserialize(
        cls,
        serialized_node: (
            tuple[float, float] | tuple[float, float, str | None | dict] | tuple[float, float, str | None, dict]
        ),
    ):
        """
        Create a Node object from a serialized form, such that ``from_serialized(ast.literal_eval(str(node_object)))``
        returns an equivalent copy of ``node_obj``.

        Args:
            serialized_node: serialized node, consisting of a tuple ``(x, y, element_name, params)``, where ``x`` and
            ``y`` are the node coordinates. The string ``element_name`` and dict ``params`` are optional.

        Returns: a Node

        """
        x, y = float(serialized_node[0]), float(serialized_node[1])
        element = None
        params = {}
        if len(serialized_node) > 2:
            if isinstance(serialized_node[2], dict):
                params = serialized_node[2]
            else:
                element = serialized_node[2]
        if len(serialized_node) > 3:
            params = serialized_node[3]

        if element is not None:
            if element in COMMON_ELEMENTS:
                element = COMMON_ELEMENTS[element]
            else:
                element = element_by_class_name(element)

        # re-create DPoint from tuple
        magic_params = ("align", "inst_name", "angle")
        for pn, pv in params.items():
            if isinstance(pv, tuple) and pn not in magic_params:
                if len(pv) < 2:
                    raise ValueError(f"Point parameter {pn} should have two elements")
                params[pn] = pya.DPoint(float(pv[0]), float(pv[1]))

        return cls(pya.DPoint(x, y), element, **params)

    @staticmethod
    def nodes_from_string(nodes: list[str] | str) -> list["Node"]:
        """Converts the human-readable text representation of Nodes to an actual Node object list.

        Needed for storage in KLayout parameters. The string has to conform to a specific format:
        `(x, y, class_str, parameter_dict)`. For example `(0, 500, 'Airbridge', {'n_bridges': 2})`,
        see also the `Node.__str__` method. Empty class_str or parameter_dict may be omitted.

        Returns:
            list of Node objects
        """

        nlas = ", ".join(nodes) if isinstance(nodes, list) else nodes
        node_list = ast.literal_eval(nlas + ",")

        return [Node.deserialize(node) for node in node_list]
