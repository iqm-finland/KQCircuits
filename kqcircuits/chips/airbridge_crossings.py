# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import sys
import math
from importlib import reload

from kqcircuits.pya_resolver import pya

from kqcircuits.chips.chip import Chip
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.airbridge import Airbridge
from kqcircuits.elements.waveguide_coplanar_bridged import WaveguideCoplanarBridged, Node, NodeType

reload(sys.modules[Chip.__module__])

version = 1


class AirbridgeCrossings(Chip):
    """The PCell declaration for an AirbridgeCrossings chip.

    On the left side of the chip there is a straight vertical waveguide and a meandering waveguide crossing it multiple
    times. There are airbridges at the crossings. On the right side there is likewise a straight and a meandering
    waveguide, but they do not cross at any point. In the center of the chip there is an array of mechanical tests of
    airbridges with different lengths and widths.

    Parameters:
        crossings: Number of pairs of airbridge crossings (int)
        b_number: Number of airbridges in one element of the mechanical test array (int)
        bridge_width: Width of crossing airbridges (um) (float)
        bridge_length: Length of crossing airbridges (um) (float)

    """

    PARAMETERS_SCHEMA = {
        "crossings": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Number of double crossings",
            "default": 10
        },
        "b_number": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Number of bridges",
            "default": 5
        },
        "bridge_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Crossing airbridge width (um)",
            "default": 20
        },
        "bridge_length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Crossing airbridge length (um)",
            "default": 60
        },
    }

    def __init__(self):
        super().__init__()

    def produce_impl(self):

        launchers = self.produce_launchers_SMA8()
        self._produce_transmission_lines(launchers)
        self._produce_mechanical_test_array()
        super().produce_impl()

    def _produce_transmission_lines(self, launchers):

        # Left transmission line
        tl_1 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                launchers["NW"][0],
                launchers["SW"][0]
            ], 1)
        })
        self.insert_cell(tl_1)

        # Right transmission line
        tl_2 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                launchers["NE"][0],
                launchers["SE"][0]
            ], 1)
        })
        self.insert_cell(tl_2)

        # Crossing transmission line
        nodes = [Node(node_type=NodeType.WAVEGUIDE, position=launchers["WN"][0])]
        ref_x = launchers["NW"][0].x
        last_y = launchers["WN"][0].y
        crossings = self.crossings  # must be even
        step = (launchers["WN"][0].y - launchers["WS"][0].y) / (crossings - 0.5) / 2
        wiggle = 250
        for i in range(crossings):
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x - wiggle, last_y)))
            nodes.append(Node(NodeType.AB_SERIES_SET, pya.DPoint(ref_x, last_y)))
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x + wiggle, last_y)))
            last_y -= step
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x + wiggle, last_y)))
            nodes.append(Node(NodeType.AB_SERIES_SET, pya.DPoint(ref_x, last_y)))
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x - wiggle, last_y)))
            last_y -= step
        nodes.append(Node(NodeType.WAVEGUIDE, launchers["WS"][0]))
        waveguide_cell = WaveguideCoplanarBridged.create_cell(self.layout, {"nodes": nodes,
                                                           "bridge_width_series": self.bridge_width,
                                                           "bridge_length_series": self.bridge_length
                                                           })
        self.insert_cell(waveguide_cell)


        # TL without crossings
        nodes = [Node(NodeType.WAVEGUIDE, launchers["EN"][0])]
        ref_x = launchers["NE"][0].x + 2 * wiggle + 50
        last_y = launchers["EN"][0].y
        for i in range(crossings):
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x + wiggle, last_y)))
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x - wiggle, last_y)))
            last_y -= step
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x - wiggle, last_y)))
            nodes.append(Node(NodeType.WAVEGUIDE, pya.DPoint(ref_x + wiggle, last_y)))
            last_y -= step
        nodes.append(Node(NodeType.WAVEGUIDE, launchers["ES"][0]))
        waveguide_cell = WaveguideCoplanarBridged.create_cell(self.layout, {"nodes": nodes,
                                                           "bridge_width_series": self.bridge_width,
                                                           "bridge_length_series": self.bridge_length
                                                           })
        self.insert_cell(waveguide_cell)


    def _produce_mechanical_test_array(self):

        p_test_origin = pya.DPoint(3600, 9650)
        v_distance_step = pya.DVector(0, -2350)
        v_length_step = pya.DVector(0, -121)
        v_width_step = pya.DVector(400, 0)

        for i, length in enumerate(range(22, 60, 2)):
            for j, width in enumerate(range(5, 20, 2)):
                for k, distance in enumerate(range(2, 22, 5)):
                    loc = p_test_origin + v_length_step * i + v_width_step * j + v_distance_step * k
                    self._produce_mechanical_test(loc, distance, self.b_number, length, width)

    def _produce_mechanical_test(self, loc, distance, number, length, width):

        wg_len = ((number * (distance + width)) * 2) + 4
        wg_start = loc + pya.DVector(-wg_len / 2, 0)
        wg_end = loc + pya.DVector(+wg_len / 2, 0)
        v_step = pya.DVector((distance + width) * 2, 0)

        ab = Airbridge.create_cell(self.layout, {
            "pad_width": 1.1 * width,
            "pad_length": 1 * width,
            "bridge_length": length,
            "bridge_width": width,
            "pad_extra": 2
        })
        for i in range(number):
            ab_trans = pya.DCplxTrans(1, 0, False, wg_start + v_step * (i + 0.5))
            self.insert_cell(ab, ab_trans)

        # waveguide
        wg = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([wg_start, wg_end], 1)
        })
        self.insert_cell(wg)
