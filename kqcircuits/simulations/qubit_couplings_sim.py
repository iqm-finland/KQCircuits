# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from abc import ABCMeta, abstractmethod

from kqcircuits.defaults import default_layers
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_bridged import WaveguideCoplanarBridged, Node, NodeType
from kqcircuits.simulations.port import EdgePort, InternalPort
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.pya_resolver import pya


class QubitCouplingsSim(Simulation, metaclass=ABCMeta):

    PARAMETERS_SCHEMA = \
        {
            "use_internal_ports": {
                "type": pya.PCellParameterDeclaration.TypeBoolean,
                "description": "Use internal (lumped) ports. The alternative is wave ports.",
                "default": True
            },
            "waveguide_length": {
                "type": pya.PCellParameterDeclaration.TypeDouble,
                "description": "Length of waveguide stubs or distance between couplers and waveguide turning point",
                "default": 100
            }
        }

    def produce_waveguide_to_port(self, location, towards, port_nr, side,
                                  use_internal_ports=None, waveguide_length=None,
                                  term1=0, turn_radius=None,
                                  a = None, b = None,
                                  airbridge=False, airbridge_a=None, airbridge_b=None):
        """
        Create a waveguide connection from some `location` to a port, and add the corresponding port to
        `simulation.ports`.

        Arguments:
            location (pya.DPoint): Point where the waveguide connects to the simulation
            towards (pya.DPoint): Point that sets the direction of the waveguide.
                The waveguide will start from `location` and go towards `towards`
            port_nr (int): Port index for the simulation engine starting from 1
            side (str): Indicate on which edge the port should be located. Ignored for internal ports.
                Must be one of `left`, `right`, `top` or `bottom`
            use_internal_ports (bool, optional): if True, ports will be inside the simulation. If False, ports will be
                brought out to an edge of the box, determined by `side`.
                Defaults to the value of the `use_internal_ports` parameter
            waveguide_length (float, optional): length of the waveguide [μm], used only for internal ports
                Defaults to the value of the `waveguide_length` parameter
            term1 (float, optional): Termination gap [μm] at `location`. Default 0
            turn_radius (float, optional): Turn radius of the waveguide. Not relevant for internal ports.
                Defaults to the value of the `r` parameter
            a (float, optional): Center conductor width. Defaults to the value of the `a` parameter
            b (float, optional): Gap conductor width. Defaults to the value of the `a` parameter
            airbridge (bool, optional): if True, an airbridge will be inserted at `location`. Default False.
            airbridge_a (float, optional): Center conductor width for the airbridge part of the waveguide.
                Defaults to the value of the `a` parameter
            airbridge_b (float, optional): Gap conductor width for the airbridge part of the waveguide.
                Defaults to the value of the `a` parameter
        """

        waveguide_safety_overlap = 0.005  # Extend waveguide by this amount to avoid gaps due to nm-scale rounding errors
        waveguide_gap_extension = 1  # Extend gaps beyond waveguides into ground plane to define the ground port edge

        if turn_radius is None:
            turn_radius = self.r
        if a is None:
            a = self.a
        if b is None:
            b = self.b
        if airbridge_a is None:
            airbridge_a = self.a
        if airbridge_b is None:
            airbridge_b = self.b
        if use_internal_ports is None:
            use_internal_ports = self.use_internal_ports
        if waveguide_length is None:
            waveguide_length = self.waveguide_length

        # Create a new path in the direction of path but with length waveguide_length
        direction = towards-location
        direction = direction/direction.length()

        # First node may be an airbridge
        if airbridge:
            first_node = Node(NodeType.AB_SERIES_SINGLE, location, a=airbridge_a, b=airbridge_b)
        else:
            first_node = Node(NodeType.WAVEGUIDE, location)

        if use_internal_ports:
            signal_point = location + (waveguide_length) * direction
            ground_point = location + (waveguide_length + a) * direction

            nodes = [
                first_node,
                Node(NodeType.WAVEGUIDE, signal_point),
            ]
            port = InternalPort(port_nr, signal_point, ground_point)

            extension_nodes = [
                Node(NodeType.WAVEGUIDE, ground_point - waveguide_safety_overlap * direction),
                Node(NodeType.WAVEGUIDE, ground_point + waveguide_gap_extension * direction)
            ]
        else:
            corner_point = location + (waveguide_length + turn_radius) * direction
            port_edge_point = {
                "left": pya.DPoint(self.box.left, corner_point.y),
                "right": pya.DPoint(self.box.right, corner_point.y),
                "top": pya.DPoint(corner_point.x, self.box.top),
                "bottom": pya.DPoint(corner_point.x, self.box.bottom)
            }[side]

            nodes = [
                first_node,
                Node(NodeType.WAVEGUIDE, corner_point),
                Node(NodeType.WAVEGUIDE, port_edge_point),
            ]
            port = EdgePort(port_nr, port_edge_point)

        tl = self.add_element(WaveguideCoplanarBridged,
            nodes=nodes,
            r=turn_radius,
            term1=term1,
            term2=0,
            a=a,
            b=b
        )

        self.cell.insert(pya.DCellInstArray(tl.cell_index(), pya.DTrans()))
        feedline_length = WaveguideCoplanar.get_length(tl, self.layout.layer(default_layers["annotations"]))

        if use_internal_ports:
            port_end_piece = self.add_element(WaveguideCoplanarBridged,
                nodes=extension_nodes,
                a=a,
                b=b,
                term1=a,
                term2=0,
            )
            self.cell.insert(pya.DCellInstArray(port_end_piece.cell_index(), pya.DTrans()))
        else:
            port.deembed_len = feedline_length

        self.ports.append(port)

    @abstractmethod
    def build(self):
        pass
