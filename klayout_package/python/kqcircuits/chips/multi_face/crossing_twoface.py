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


from kqcircuits.chips.multi_face.multi_face import MultiFace
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt


class CrossingTwoface(MultiFace):
    """The PCell declaration for an CrossingTwoFace MultiFace chip.

    On the left side of the chip there is a straight vertical waveguide bottom face and a meandering waveguide crossing
    multiple times on the top face. There are transmission lines at different faces at the crossings. On the right side
    there is likewise a straight and a meandering waveguide, but they do not cross at any point.
    """

    crossings = Param(pdt.TypeInt, "Number of double crossings", 3,
        docstring="Number of pairs of flip-chip crossings")
    crossing_length = Param(pdt.TypeDouble, "Crossing waveguide length", 400, unit="μm",
        docstring="Length of the crossing on the top face [μm]")
    cross_talk_distance = Param(pdt.TypeDouble, "Transmission line distance from meander", 300, unit="μm",
        docstring="Distance between the right straight transmission line and meander on the right [μm]")
    meander_face = Param(pdt.TypeString, "Meander face on right side", "single", choices=["Single", "Two Face"])

    def build(self):
        launchers = self.produce_launchers("SMA8")
        self._produce_transmission_lines(launchers)

    def _produce_transmission_lines(self, launchers):
        distance = 700
        right_tr_x = 5000 + distance
        left_tr_x = 5000 - distance
        face1_box = self.get_box(1)

        # Left transmission line
        nodes = [Node(self.refpoints["NW_port"]),
                 Node(self.refpoints["NW_port_corner"] + pya.DPoint(0, - 2 * self.r)),
                 Node((left_tr_x, self.refpoints["NW_port_corner"].y - 2 * self.r)),
                 Node((left_tr_x, face1_box.p2.y), a=self.a_capped, b=self.b_capped),
                 Node((left_tr_x, face1_box.p1.y + 100), a=self.a, b=self.b),
                 Node((left_tr_x, self.refpoints["SW_port_corner"].y + 2 * self.r)),
                 Node(self.refpoints["SW_port_corner"] + pya.DPoint(0, 2 * self.r)),
                 Node(self.refpoints["SW_port"])
                 ]

        self.insert_cell(WaveguideComposite, nodes=nodes)

        # Right transmission line
        nodes = [Node(self.refpoints["NE_port"]),
                 Node(self.refpoints["NE_port_corner"] + pya.DPoint(0, - 2 * self.r)),
                 Node((right_tr_x, self.refpoints["NE_port_corner"].y - 2 * self.r)),
                 Node((right_tr_x, face1_box.p2.y),
                      a=self.a_capped, b=self.b_capped),
                 Node((right_tr_x, face1_box.p1.y + 100), a=self.a, b=self.b),
                 Node((right_tr_x, self.refpoints["SE_port_corner"].y + 2 * self.r)),
                 Node(self.refpoints["SE_port_corner"] + pya.DPoint(0, 2 * self.r)),
                 Node(self.refpoints["SE_port"])
                 ]

        self.insert_cell(WaveguideComposite, nodes=nodes)

        # Crossing transmission line
        nodes = [Node(self.refpoints["WN_port"]),
                 Node((face1_box.p1.x, self.refpoints["WN_port"].y),
                      a=self.a_capped, b=self.b_capped)]
        ref_x = left_tr_x
        ref_x_1 = ref_x - self.crossing_length / 2.
        ref_x_2 = ref_x + self.crossing_length / 2.

        last_y = launchers["WN"][0].y
        crossings = self.crossings  # must be even
        step = (launchers["WN"][0].y - launchers["WS"][0].y) / (crossings - 0.5) / 2
        wiggle = self.crossing_length / 2. + 250

        for i in range(crossings):
            nodes.append(Node((ref_x - wiggle, last_y)))
            nodes.append(Node((ref_x_1, last_y), face_id="t"))
            nodes.append(Node((ref_x_2, last_y), face_id="b"))
            nodes.append(Node((ref_x + wiggle, last_y)))
            last_y -= step
            nodes.append(Node((ref_x + wiggle, last_y)))
            nodes.append(Node((ref_x_2, last_y), face_id="t"))
            nodes.append(Node((ref_x_1, last_y), face_id="b"))
            nodes.append(Node((ref_x - wiggle, last_y)))
            last_y -= step
        nodes.append(Node((face1_box.p1.x + 100, self.refpoints["WS_port"].y), a=self.a, b=self.b))
        nodes.append(Node(self.refpoints["WS_port_corner"]))
        nodes.append(Node(self.refpoints["WS_port"]))
        self.insert_cell(WaveguideComposite, nodes=nodes)

        # cross_talk
        ref_x = right_tr_x + self.cross_talk_distance + wiggle
        last_y = self.refpoints["EN_port"].y
        nodes = [Node(self.refpoints["EN_port"]),
                 Node(self.refpoints["EN_port_corner"]),
                 Node((face1_box.p2.x, self.refpoints["EN_port"].y),
                      a=self.a_capped, b=self.b_capped)]
        for i in range(crossings):
            if i == 0 and self.meander_face == "Two Face":
                nodes.append(
                    Node((ref_x + wiggle, last_y), face_id="t"))
            else:
                nodes.append(Node((ref_x + wiggle, last_y)))
            nodes.append(Node((ref_x - wiggle, last_y)))
            last_y -= step
            nodes.append(Node((ref_x - wiggle, last_y)))
            if i == range(crossings)[-1] and self.meander_face == "Two Face":
                nodes.append(Node((ref_x + wiggle, last_y), face_id="b"))
            else:
                nodes.append(Node((ref_x + wiggle, last_y)))
            last_y -= step
        nodes.append(Node((face1_box.p2.x - 100, self.refpoints["ES_port"].y),
                          a=self.a, b=self.b))
        nodes.append(Node(self.refpoints["ES_port_corner"]))
        nodes.append(Node(self.refpoints["ES_port"]))
        self.insert_cell(WaveguideComposite, nodes=nodes)
