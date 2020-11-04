# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import sys
from importlib import reload

from kqcircuits.pya_resolver import pya

from kqcircuits.chips.multi_face.multi_face import MultiFace
from kqcircuits.elements.waveguide_coplanar_bridged import WaveguideCoplanarBridged, Node, NodeType

reload(sys.modules[MultiFace.__module__])

version = 1


class CrossingTwoface(MultiFace):
    """The PCell declaration for an CrossingTwoFace MultiFace chip.

    On the left side of the chip there is a straight vertical waveguide bottom face and a meandering waveguide crossing
    multiple times on the top face. There are transmission lines at different faces at the crossings. On the right side
    there is likewise a straight and a meandering waveguide, but they do not cross at any point.
    """

    PARAMETERS_SCHEMA = {
        "crossings": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Number of double crossings",
            "docstring": "Number of pairs of flip-chip crossings",
            "default": 3
        },
        "crossing_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Crossing waveguide length [μm]",
            "docstring": "Length of the crossing on the top face [μm]",
            "default": 400
        },
        "cross_talk_distance": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Transmission line distance from meander [μm]",
            "docstring": "Distance between the right straight transmission line and meander on the right [μm]",
            "default": 300
        },
        "meander_face": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Meander face on right side",
            "default": "single",
            "choices": [["Single", "Single"], ["Two Face", "Two Face"]]
        },
    }

    def produce_impl(self):
        launchers = self.produce_launchers_SMA8()
        self._produce_transmission_lines(launchers)
        super().produce_impl()

    def _produce_transmission_lines(self, launchers):
        distance = 700
        right_tr_x = 5000 + distance
        left_tr_x = 5000 - distance

        # Left transmission line
        nodes = [Node(NodeType.WAVEGUIDE, self.refpoints["NW_port"]),
                 Node(NodeType.WAVEGUIDE, self.refpoints["NW_port_corner"] + pya.DPoint(0, - 2 * self.r)),
                 Node(NodeType.WAVEGUIDE, pya.DPoint(left_tr_x, self.refpoints["NW_port_corner"].y - 2 * self.r)),
                 Node(NodeType.WAVEGUIDE, pya.DPoint(left_tr_x, self.face1_box.p2.y), a=self.a_capped, b=self.b_capped),
                 Node(NodeType.WAVEGUIDE, pya.DPoint(left_tr_x, self.face1_box.p1.y + 100), a=self.a, b=self.b),
                 Node(NodeType.WAVEGUIDE, pya.DPoint(left_tr_x, self.refpoints["SW_port_corner"].y + 2 * self.r)),
                 Node(NodeType.WAVEGUIDE, self.refpoints["SW_port_corner"] + pya.DPoint(0, 2 * self.r)),
                 Node(NodeType.WAVEGUIDE, self.refpoints["SW_port"])
                 ]

        self.insert_cell(WaveguideCoplanarBridged, nodes=nodes, connector_type=self.connector_type, margin=self.margin)

        # Right transmission line
        nodes = [Node(NodeType.WAVEGUIDE, self.refpoints["NE_port"]),
                 Node(NodeType.WAVEGUIDE, self.refpoints["NE_port_corner"] + pya.DPoint(0, - 2 * self.r)),
                 Node(NodeType.WAVEGUIDE, pya.DPoint(right_tr_x, self.refpoints["NE_port_corner"].y - 2 * self.r)),
                 Node(NodeType.WAVEGUIDE, pya.DPoint(right_tr_x, self.face1_box.p2.y),
                      a=self.a_capped, b=self.b_capped),
                 Node(NodeType.WAVEGUIDE, pya.DPoint(right_tr_x, self.face1_box.p1.y + 100), a=self.a, b=self.b),
                 Node(NodeType.WAVEGUIDE, pya.DPoint(right_tr_x, self.refpoints["SE_port_corner"].y + 2 * self.r)),
                 Node(NodeType.WAVEGUIDE, self.refpoints["SE_port_corner"] + pya.DPoint(0, 2 * self.r)),
                 Node(NodeType.WAVEGUIDE, self.refpoints["SE_port"])
                 ]

        self.insert_cell(WaveguideCoplanarBridged, nodes=nodes, connector_type=self.connector_type, margin=self.margin)

        # Crossing transmission line
        nodes = [Node(NodeType.WAVEGUIDE, self.refpoints["WN_port"], a=self.a, b=self.b),
                 Node(NodeType.WAVEGUIDE, pya.DPoint(self.face1_box.p1.x, self.refpoints["WN_port"].y),
                      a=self.a_capped, b=self.b_capped)]
        ref_x = left_tr_x
        ref_x_1 = ref_x - self.crossing_length / 2.
        ref_x_2 = ref_x + self.crossing_length / 2.

        last_y = launchers["WN"][0].y
        crossings = self.crossings  # must be even
        step = (launchers["WN"][0].y - launchers["WS"][0].y) / (crossings - 0.5) / 2
        wiggle = self.crossing_length / 2. + 250

        for i in range(crossings):
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x - wiggle, last_y)))
            nodes.append(Node(NodeType.FC_BUMP, pya.DPoint(ref_x_1, last_y)))
            nodes.append(Node(NodeType.FC_BUMP, pya.DPoint(ref_x_2, last_y)))
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x + wiggle, last_y)))
            last_y -= step
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x + wiggle, last_y)))
            nodes.append(Node(NodeType.FC_BUMP, pya.DPoint(ref_x_2, last_y)))
            nodes.append(Node(NodeType.FC_BUMP, pya.DPoint(ref_x_1, last_y)))
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x - wiggle, last_y)))
            last_y -= step
        nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(self.face1_box.p1.x + 100, self.refpoints["WS_port"].y),
                          a=self.a, b=self.b)),
        nodes.append(Node(NodeType.WAVEGUIDE, self.refpoints["WS_port_corner"]))
        nodes.append(Node(NodeType.WAVEGUIDE, self.refpoints["WS_port"]))
        self.insert_cell(WaveguideCoplanarBridged,
                         nodes=nodes,
                         connector_type=self.connector_type,
                         margin=self.margin,
                         a=self.a_capped,
                         b=self.b_capped
                         )

        # cross_talk
        ref_x = right_tr_x + self.cross_talk_distance + wiggle
        last_y = self.refpoints["EN_port"].y
        nodes = [Node(NodeType.WAVEGUIDE, self.refpoints["EN_port"]),
                 Node(NodeType.WAVEGUIDE, self.refpoints["EN_port_corner"]),
                 Node(NodeType.WAVEGUIDE, pya.DPoint(self.face1_box.p2.x, self.refpoints["EN_port"].y),
                      a=self.a_capped, b=self.b_capped)]
        for i in range(crossings):
            if i == 0 and self.meander_face == "Two Face":
                nodes.append(
                    Node(NodeType.FC_BUMP, pya.DPoint(ref_x + wiggle, last_y)))
            else:
                nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x + wiggle, last_y)))
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x - wiggle, last_y)))
            last_y -= step
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x - wiggle, last_y)))
            if i == range(crossings)[-1] and self.meander_face == "Two Face":
                nodes.append(Node(NodeType.FC_BUMP, pya.DPoint(ref_x + wiggle, last_y)))
            else:
                nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x + wiggle, last_y)))
            last_y -= step
        nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(self.face1_box.p2.x - 100, self.refpoints["ES_port"].y),
                          a=self.a, b=self.b))
        nodes.append(Node(NodeType.WAVEGUIDE, self.refpoints["ES_port_corner"]))
        nodes.append(Node(NodeType.WAVEGUIDE, self.refpoints["ES_port"]))
        self.insert_cell(WaveguideCoplanarBridged, nodes=nodes, connector_type=self.connector_type, margin=self.margin)
