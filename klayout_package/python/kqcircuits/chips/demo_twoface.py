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


from kqcircuits.chips.chip import Chip
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.elements.finger_capacitor_taper import FingerCapacitorTaper
from kqcircuits.elements.meander import Meander
from kqcircuits.qubits.swissmon import Swissmon
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter, t_cross_parameters
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import point_shift_along_vector
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.chips.demo import Demo

@add_parameters_from(Demo, "readout_res_lengths", "include_couplers", frames_enabled=[0, 1])
class DemoTwoface(Chip):
    """Demonstration chip for 3D-integration (multi-face) features."""

    name_chip = Param(pdt.TypeString, "Name of the chip", "DT")

    def build(self):

        launcher_assignments = {
            # N
            2: "FL-QB1",
            3: "PL-A-IN",
            4: "PL-B-IN",
            5: "FL-QB2",
            # E
            7: "DL-QB2",
            12: "DL-QB4",
            # S
            14: "FL-QB4",
            15: "PL-B-OUT",
            16: "PL-A-OUT",
            17: "FL-QB3",
            # W
            19: "DL-QB3",
            24: "DL-QB1",
        }
        self.produce_launchers("ARD24", launcher_assignments)

        self.produce_qubits()
        if self.include_couplers:
            self.produce_couplers()
        self.produce_control_lines()
        self.produce_readout_structures()
        self.produce_probelines()

    def produce_qubits(self):
        dist_x = 2000  # distance from bottom chip edge
        dist_y = 3200
        self.produce_qubit(pya.DTrans(0, True, dist_x, 1e4 - dist_y), "QB1")
        self.produce_qubit(pya.DTrans(2, False, 1e4 - dist_x, 1e4 - dist_y), "QB2")
        self.produce_qubit(pya.DTrans(0, False, dist_x, dist_y), "QB3")
        self.produce_qubit(pya.DTrans(2, True, 1e4 - dist_x, dist_y), "QB4")

    def produce_qubit(self, trans, inst_name):
        self.insert_cell(Swissmon, trans, inst_name,
            cpl_length=[120, 120, 120],
            port_width=[4, 10, 4],
        )

    def produce_couplers(self):
        self.produce_coupler(1, 2)
        self.produce_coupler(4, 3)

    def produce_coupler(self, qubit_a_nr, qubit_b_nr):
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["QB{}_port_cplr2".format(qubit_a_nr)]),
            Node(self.refpoints["QB{}_port_cplr2".format(qubit_b_nr)]),
        ], a=4, b=9)

    def produce_control_lines(self):
        for qubit_nr in [1, 2, 3, 4]:
            self.produce_driveline(qubit_nr)
            self.produce_fluxline(qubit_nr)

    def produce_driveline(self, qubit_nr):
        port_drive = self.refpoints["QB{}_port_drive".format(qubit_nr)]
        port_corner = self.refpoints["DL-QB{}_port_corner".format(qubit_nr)]
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["DL-QB{}_base".format(qubit_nr)]),
            Node(port_corner),
            Node(port_drive),
        ], term2=self.b)

    def produce_fluxline(self, qubit_nr):
        port_corner = self.refpoints["FL-QB{}_port_corner".format(qubit_nr)]
        port_flux = self.refpoints["QB{}_port_flux".format(qubit_nr)]
        shift = 1500 if qubit_nr in [3, 4] else -1500
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["FL-QB{}_base".format(qubit_nr)]),
            Node(port_corner + pya.DPoint(0, shift)),
            Node((port_flux.x, port_corner.y + shift)),
            Node(self.refpoints["QB{}_port_flux".format(qubit_nr)])
        ])

    def produce_readout_structures(self):
        self.produce_readout_structure(1, False, 7)
        self.produce_readout_structure(2, True, 6)
        self.produce_readout_structure(3, False, 5)
        self.produce_readout_structure(4, True, 4)

    def produce_readout_structure(self, qubit_nr, mirrored, cap_finger_nr):

        # non-meandering part of the resonator

        point_1 = self.refpoints["QB{}_port_cplr1".format(qubit_nr)]
        point_2 = point_shift_along_vector(self.refpoints["QB{}_port_cplr1".format(qubit_nr)],
                                           self.refpoints["QB{}_base".format(qubit_nr)], -700)
        point_3 = point_2 + pya.DPoint(-400 if mirrored else 400, 0)
        point_4 = point_3 + pya.DPoint(-100 if mirrored else 100, 0)

        waveguide_inst, _ = self.insert_cell(WaveguideComposite, nodes=[
            Node(point_1),
            Node(point_2),
            Node(point_3, face_id=self.face_ids[1]),
            Node(point_4),
        ])
        length_nonmeander = waveguide_inst.cell.length()

        # meandering part of the resonator

        meander_start = point_4
        meander_end = point_4 + pya.DPoint(-1300 if mirrored else 1300, 0)

        self.insert_cell(Meander,
            start=meander_start,
            end=meander_end,
            length=float(self.readout_res_lengths[qubit_nr - 1]) - length_nonmeander,
            meanders=5,
            face_ids=[self.face_ids[1]]
        )

        # capacitor and tcross waveguide connecting resonator to probeline

        if mirrored:
            cap_rot = 2
            tcross_rot = 1
        else:
            cap_rot = 0
            tcross_rot = 3
        cap_cell = self.add_element(FingerCapacitorSquare,
            finger_number=cap_finger_nr,
            face_ids=[self.face_ids[1]]
        )
        cap_ref_rel = self.get_refpoints(cap_cell, pya.DTrans(cap_rot, False, 0, 0))
        cap_trans = pya.DTrans(cap_rot, False, meander_end + cap_ref_rel["base"] - cap_ref_rel["port_a"])
        _, cap_ref_abs = self.insert_cell(cap_cell, cap_trans)

        tcross_cell = self.add_element(WaveguideCoplanarSplitter, **t_cross_parameters(
            a=self.a, b=self.b, a2=self.a, b2=self.b, length_extra_side=30, face_ids=[self.face_ids[1]]))
        tcross_ref_rel = self.get_refpoints(tcross_cell, pya.DTrans(tcross_rot, False, 0, 0))
        tcross_trans = pya.DTrans(tcross_rot, False, cap_ref_abs["port_b"] - tcross_ref_rel["port_bottom"])
        self.insert_cell(tcross_cell, tcross_trans, inst_name="PL{}".format(qubit_nr), label_trans=pya.DCplxTrans(0.2))

    def produce_probelines(self):
        self.produce_probeline("PL-A", 1, 3, True, 4)
        self.produce_probeline("PL-B", 2, 4, False, 6)

    def produce_probeline(self, probeline_name, qubit_a_nr, qubit_b_nr, mirrored, cap_finger_nr):

        cap_cell = self.add_element(FingerCapacitorTaper,
            finger_number=cap_finger_nr,
            taper_length=20,
            face_ids=[self.face_ids[1]]
        )
        cap_trans = pya.DTrans(3, False, self.refpoints["PL{}_port_left".format(qubit_a_nr)] + pya.DPoint(0, 700))
        _, cap_ref_abs = self.insert_cell(cap_cell, cap_trans)

        # segment 1
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["{}-IN_base".format(probeline_name)]),
            Node(self.refpoints["{}-IN_port_corner".format(probeline_name)] + pya.DPoint(0, -1000)),
            Node((self.refpoints["PL{}_port_left".format(qubit_a_nr)].x,
                  self.refpoints["{}-IN_port_corner".format(probeline_name)].y - 1000)),
            Node(cap_ref_abs["port_a"] + pya.DPoint(0, 700), face_id=self.face_ids[1]),
            Node(cap_ref_abs["port_a"]),
        ])

        port_1_side = "left" if mirrored else "right"
        port_2_side = "right" if mirrored else "left"

        # segment 2
        self.insert_cell(WaveguideComposite, nodes=[
            Node(cap_ref_abs["port_b"]),
            Node(self.refpoints["PL{}_port_{}".format(qubit_a_nr, port_1_side)]),
        ], face_ids=[self.face_ids[1]])

        # segment 3
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["PL{}_port_{}".format(qubit_a_nr, port_2_side)]),
            Node(self.refpoints["PL{}_port_{}".format(qubit_b_nr, port_1_side)]),
        ], face_ids=[self.face_ids[1]])

        # segment 4
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["{}-OUT_base".format(probeline_name)]),
            Node(self.refpoints["{}-OUT_port_corner".format(probeline_name)] + pya.DPoint(0, 1000)),
            Node((self.refpoints["PL{}_port_right".format(qubit_b_nr)].x,
                  self.refpoints["{}-OUT_port_corner".format(probeline_name)].y + 1000)),
            Node(self.refpoints["PL{}_port_right".format(qubit_b_nr)] + pya.DPoint(0, -1400), face_id=self.face_ids[1]),
            Node(self.refpoints["PL{}_port_{}".format(qubit_b_nr, port_2_side)]),
        ])
