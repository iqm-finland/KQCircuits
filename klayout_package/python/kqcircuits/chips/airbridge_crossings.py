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


from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.chips.chip import Chip
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node


class AirbridgeCrossings(Chip):
    """The PCell declaration for an AirbridgeCrossings chip.

    On the left side of the chip there is a straight vertical waveguide and a meandering waveguide crossing it multiple
    times. There are airbridges at the crossings. On the right side there is likewise a straight and a meandering
    waveguide, but they do not cross at any point. In the center of the chip there is an array of mechanical tests of
    airbridges with different lengths and widths.
    """

    crossings = Param(pdt.TypeInt, "Number of double crossings", 10,
        docstring="Number of pairs of airbridge crossings")
    b_number = Param(pdt.TypeInt, "Number of bridges", 5,
        docstring="Number of airbridges in one element of the mechanical test array")

    def build(self):

        launchers = self.produce_launchers("SMA8")
        self._produce_transmission_lines(launchers)
        self._produce_mechanical_test_array()

    def _produce_transmission_lines(self, launchers):

        # Left transmission line
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                launchers["NW"][0],
                launchers["SW"][0]
            ], 1)
        )

        # Right transmission line
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                launchers["NE"][0],
                launchers["SE"][0]
            ], 1)
        )

        # Crossing transmission line
        nodes = [Node(launchers["WN"][0])]
        ref_x = launchers["NW"][0].x
        last_y = launchers["WN"][0].y
        crossings = self.crossings  # must be even
        step = (launchers["WN"][0].y - launchers["WS"][0].y) / (crossings - 0.5) / 2
        wiggle = 250
        for _ in range(crossings):
            nodes.append(Node((ref_x - wiggle, last_y)))
            nodes.append(Node((ref_x, last_y), AirbridgeConnection))
            nodes.append(Node((ref_x + wiggle, last_y)))
            last_y -= step
            nodes.append(Node((ref_x + wiggle, last_y)))
            nodes.append(Node((ref_x, last_y), AirbridgeConnection))
            nodes.append(Node((ref_x - wiggle, last_y)))
            last_y -= step
        nodes.append(Node(launchers["WS"][0]))
        waveguide_cell = self.add_element(WaveguideComposite, nodes=nodes)
        self.insert_cell(waveguide_cell)

        # TL without crossings
        nodes = [Node(launchers["EN"][0])]
        ref_x = launchers["NE"][0].x + 2 * wiggle + 50
        last_y = launchers["EN"][0].y
        for _ in range(crossings):
            nodes.append(Node((ref_x + wiggle, last_y)))
            nodes.append(Node((ref_x - wiggle, last_y)))
            last_y -= step
            nodes.append(Node((ref_x - wiggle, last_y)))
            nodes.append(Node((ref_x + wiggle, last_y)))
            last_y -= step
        nodes.append(Node(launchers["ES"][0]))
        waveguide_cell = self.add_element(WaveguideComposite, nodes=nodes)
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
                    create_airbridges = ((i + k) % 2 == 1)  # airbridges only at every second row
                    self._produce_mechanical_test(loc, distance, self.b_number, length, width, create_airbridges)

    def _produce_mechanical_test(self, loc, distance, number, length, width, create_airbridges):
        # pylint: disable=unused-argument
        wg_len = ((number * (distance + width)) * 2) + 4
        wg_start = loc + pya.DVector(-wg_len / 2, 0)
        wg_end = loc + pya.DVector(+wg_len / 2, 0)
        # v_step = pya.DVector((distance + width) * 2, 0)

        ab = self.add_element(Airbridge,
            # pad_length=1 * width,
            # bridge_length=length,
            # bridge_width=width,
        )
        for i in range(number):
            # ab_trans = pya.DCplxTrans(1, 0, False, wg_start + v_step * (i + 0.5))
            # self.insert_cell(ab, ab_trans)
            if 1000 < loc.y < 9000 and create_airbridges:
                ab_trans = pya.DCplxTrans(1, 0, False, loc + pya.DVector(50*(i - (number-1)/2), 0))
                self.insert_cell(ab, ab_trans)

        # waveguide
        wg = self.add_element(WaveguideCoplanar,
            path=pya.DPath([wg_start, wg_end], 1)
        )
        self.insert_cell(wg)
