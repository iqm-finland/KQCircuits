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
from kqcircuits.util.parameters import Param, pdt, add_parameters_from

from kqcircuits.chips.chip import Chip
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.elements.finger_capacitor_taper import FingerCapacitorTaper
from kqcircuits.elements.meander import Meander
from kqcircuits.qubits.swissmon import Swissmon
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter, t_cross_parameters
from kqcircuits.test_structures.junction_test_pads.junction_test_pads import JunctionTestPads
from kqcircuits.util.geometry_helper import point_shift_along_vector


@add_parameters_from(Chip, name_chip="Demo")
class Demo(Chip):
    """Demonstration chip with a four qubits, four readout resonators, two probe lines, charge- and fluxlines."""

    readout_res_lengths = Param(pdt.TypeList, "Readout resonator lengths", [5000, 5100, 5200, 5300], unit="[μm]")
    include_couplers = Param(pdt.TypeBoolean, "Include couplers between qubits", True)

    def build(self):

        launcher_assignments = {
            # N
            2: "FL-QB1",
            3: "PL-1-IN",
            4: "PL-1-OUT",
            5: "FL-QB2",
            # E
            7: "DL-QB2",
            12: "DL-QB4",
            # S
            14: "FL-QB4",
            15: "PL-2-IN",
            16: "PL-2-OUT",
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
        self.produce_junction_tests()

    def produce_qubits(self):
        dist_x = 3220  # x-distance from chip edge
        dist_y = 3000  # y-distance from chip edge
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
        self.produce_coupler(1, 2, 2)
        self.produce_coupler(2, 4, 0)
        self.produce_coupler(4, 3, 2)
        self.produce_coupler(3, 1, 0)

    def produce_coupler(self, qubit_a_nr, qubit_b_nr, port_nr):
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["QB{}_port_cplr{}".format(qubit_a_nr, port_nr)]),
            Node(point_shift_along_vector(self.refpoints["QB{}_port_cplr{}".format(qubit_a_nr, port_nr)],
                                          self.refpoints["QB{}_base".format(qubit_a_nr)], -400)),
            Node(point_shift_along_vector(self.refpoints["QB{}_port_cplr{}".format(qubit_b_nr, port_nr)],
                                          self.refpoints["QB{}_base".format(qubit_b_nr)], -400),
                 n_bridges=3
                 ),
            Node(self.refpoints["QB{}_port_cplr{}".format(qubit_b_nr, port_nr)]),
        ], a=4, b=9)

    def produce_control_lines(self):
        for qubit_nr in [1, 2, 3, 4]:
            self.produce_driveline(qubit_nr)
            self.produce_fluxline(qubit_nr)

    def produce_driveline(self, qubit_nr):
        self.insert_cell(
            WaveguideCoplanar,
            path=pya.DPath([
                self.refpoints["DL-QB{}_base".format(qubit_nr)],
                self.refpoints["DL-QB{}_port_corner".format(qubit_nr)],
                self.refpoints["QB{}_port_drive".format(qubit_nr)],
            ], 0),
            term2=self.b
        )

    def produce_fluxline(self, qubit_nr):
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["FL-QB{}_base".format(qubit_nr)]),
            Node(self.refpoints["FL-QB{}_port_corner".format(qubit_nr)]),
            Node(self.refpoints["QB{}_port_flux_corner".format(qubit_nr)], n_bridges=4),
            Node(self.refpoints["QB{}_port_flux".format(qubit_nr)])
        ])

    def produce_readout_structures(self):
        self.produce_readout_structure(1, False, 4)
        self.produce_readout_structure(2, True, 8)
        self.produce_readout_structure(3, False, 5)
        self.produce_readout_structure(4, True, 7)

    def produce_readout_structure(self, qubit_nr, mirrored, cap_finger_nr):

        # non-meandering part of the resonator

        point_1 = self.refpoints["QB{}_port_cplr1".format(qubit_nr)]
        point_2 = point_shift_along_vector(self.refpoints["QB{}_port_cplr1".format(qubit_nr)],
                                           self.refpoints["QB{}_base".format(qubit_nr)], -600)
        point_3 = point_2 + pya.DPoint(-300 if mirrored else 300, 0)

        waveguide_inst, _ = self.insert_cell(WaveguideComposite, nodes=[
            Node(point_1),
            Node(point_2),
            Node(point_3),
        ])
        length_nonmeander = waveguide_inst.cell.length()

        # meandering part of the resonator

        meander_start = point_3
        meander_end = point_3 + pya.DPoint(-1100 if mirrored else 1100, 0)

        self.insert_cell(Meander,
                         start=meander_start,
                         end=meander_end,
                         length=float(self.readout_res_lengths[qubit_nr - 1]) - length_nonmeander,
                         )

        # capacitor and tcross waveguide connecting resonator to probeline

        if mirrored:
            cap_rot = 2
            tcross_rot = 1
        else:
            cap_rot = 0
            tcross_rot = 3

        _, cap_ref_abs = self.insert_cell(FingerCapacitorSquare, pya.DTrans(cap_rot), align_to=meander_end,
                                          align="port_a", finger_number=cap_finger_nr)

        self.insert_cell(WaveguideCoplanarSplitter, pya.DTrans(tcross_rot, False, 0, 0),
                         inst_name="PL{}".format(qubit_nr),
                         label_trans=pya.DCplxTrans(0.2), align_to=cap_ref_abs["port_b"], align="port_bottom",
                         **t_cross_parameters(a=self.a, b=self.b, a2=self.a, b2=self.b, length_extra_side=30))

    def produce_probelines(self):
        self.produce_probeline("PL-1", 1, 2, False, 6)
        self.produce_probeline("PL-2", 4, 3, True, 3)

    def produce_probeline(self, probeline_name, qubit_a_nr, qubit_b_nr, mirrored, cap_finger_nr):

        if mirrored:
            cap_rot = 1
            cap_pos_shift = pya.DPoint(0, -2000)
        else:
            cap_rot = 3
            cap_pos_shift = pya.DPoint(0, 2000)

        cap_trans = pya.DTrans(cap_rot, False, self.refpoints["PL{}_port_left".format(qubit_a_nr)] + cap_pos_shift)
        _, cap_ref_abs = self.insert_cell(FingerCapacitorTaper, cap_trans, finger_number=cap_finger_nr, taper_length=20)

        # segment 1
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["{}-IN_base".format(probeline_name)]),
            Node(self.refpoints["{}-IN_port_corner".format(probeline_name)]),
            Node((self.refpoints["PL{}_port_left".format(qubit_a_nr)].x,
                  self.refpoints["{}-IN_port_corner".format(probeline_name)].y)),
            Node(cap_ref_abs["port_a"]),
        ])

        # segment 2
        self.insert_cell(WaveguideComposite, nodes=[
            Node(cap_ref_abs["port_b"]),
            Node((self.refpoints["PL{}_port_left".format(qubit_a_nr)].x,
                  self.refpoints["QB{}_base".format(qubit_a_nr)].y),
                 AirbridgeConnection if self.include_couplers else None
                 ),
            Node(self.refpoints["PL{}_port_left".format(qubit_a_nr)]),
        ])

        # segment 3
        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["PL{}_port_right".format(qubit_a_nr)]),
            Node(point_shift_along_vector(self.refpoints["PL{}_port_right".format(qubit_a_nr)],
                                          self.refpoints["PL{}_port_right_corner".format(qubit_a_nr)], 600)),
            Node(point_shift_along_vector(self.refpoints["PL{}_port_left".format(qubit_b_nr)],
                                          self.refpoints["PL{}_port_left_corner".format(qubit_b_nr)], 600),
                 n_bridges=1
                 ),
            Node(self.refpoints["PL{}_port_left".format(qubit_b_nr)]),
        ])

        self.insert_cell(WaveguideComposite, nodes=[
            Node(self.refpoints["{}-OUT_base".format(probeline_name)]),
            Node(self.refpoints["{}-OUT_port_corner".format(probeline_name)]),
            Node((self.refpoints["PL{}_port_right".format(qubit_b_nr)].x,
                  self.refpoints["{}-OUT_port_corner".format(probeline_name)].y)),
            Node((self.refpoints["PL{}_port_right".format(qubit_b_nr)].x,
                  self.refpoints["QB{}_base".format(qubit_b_nr)].y),
                 AirbridgeConnection if self.include_couplers else None
                 ),
            Node(self.refpoints["PL{}_port_right".format(qubit_b_nr)]),
        ])

    def produce_junction_tests(self):
        junction_test_cell = self.add_element(JunctionTestPads, margin=50, area_height=2500)
        label_trans = pya.DCplxTrans(0.5)
        self.insert_cell(junction_test_cell, pya.DTrans(0, False, 900, 3750), "testarray_w", label_trans=label_trans)
        self.insert_cell(junction_test_cell, pya.DTrans(0, False, 7800, 3750), "testarray_e", label_trans=label_trans)
