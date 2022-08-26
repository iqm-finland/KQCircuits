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


from math import pi

from kqcircuits.chips.chip import Chip
from kqcircuits.elements.meander import Meander
from kqcircuits.qubits.swissmon import Swissmon
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter, t_cross_parameters
from kqcircuits.pya_resolver import pya
from kqcircuits.util.coupler_lib import cap_params
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.junctions.junction import Junction


def _get_num_meanders(meander_length, turn_radius, meander_min_width):
    """Get the required number of meanders to create a meander element with the given parameters."""

    return int((meander_length - turn_radius * (pi - 2)) / (meander_min_width + turn_radius * (pi - 2)))


@add_parameters_from(Junction, "junction_type")
class SingleXmons(Chip):
    """The PCell declaration for a SingleXmons chip.

    The SingleXmons chip has 6 qubits, which are coupled by readout resonators to the same feedline. The feedline
    crosses the center of the chip horizontally.  Half of the qubits are above the feedline and half are below it.
    For each qubit, there is a chargeline connected to a launcher, but no fluxline. There can optionally be four test
    resonators between the qubits.

    Attributes:
        launchers: A dictionary where the keys are names of the launchers and values are tuples whose first elements
            are positions of the launchers.

        qubits_refpoints: A tuple where each element contains the refpoints for one of the qubits. The qubits are
            ordered such that 0,1,2 are the upper qubits (from left to right), while 3,4,5 are the lower qubits (from
            left to right).

    """
    readout_res_lengths = Param(pdt.TypeList, "Readout resonator lengths (six resonators)",
                                [5000, 5100, 5200, 5300, 5400, 5500])
    use_test_resonators = Param(pdt.TypeBoolean, "Use test resonators", True)
    test_res_lengths = Param(pdt.TypeList, "Test resonator lengths (four resonators)", [5200, 5400, 5600, 5800])
    n_fingers = Param(pdt.TypeList, "Number of fingers for test resonator couplers", [4, 4, 2, 4])
    l_fingers = Param(pdt.TypeList, "Length of fingers for test resonator couplers", [23.1, 9.9, 14.1, 10, 21])
    type_coupler = Param(pdt.TypeList, "Coupler type for test resonator couplers",
                         ["interdigital", "interdigital", "interdigital", "gap"])

    def build(self):
        """Produces a SingleXmons PCell."""

        self.produce_junction_tests(self.junction_type)
        self.launchers = self.produce_launchers("SMA8")
        self.qubits_refpoints = self._produce_qubits()

        feedline_x_distance = 1200
        if self.use_test_resonators:
            self._produce_feedline_and_test_resonators(feedline_x_distance)
        else:
            self._produce_feedline(feedline_x_distance)

        self._produce_readout_resonators()
        self._produce_chargelines()

    def _produce_waveguide(self, path, term2=0, turn_radius=None):
        """Produces a coplanar waveguide that follows the given path.

        Args:
            path: a DPath object determining the waveguide path
            term2: term2 of the waveguide
            turn_radius: turn_radius of the waveguide

        Returns:
            length of the produced waveguide

        """
        if turn_radius is None:
            turn_radius = self.r
        waveguide = self.add_element(WaveguideCoplanar,
            path=pya.DPath(path, 1),
            r=turn_radius,
            term2=term2,
        )
        self.insert_cell(waveguide)
        return waveguide

    def _produce_qubit(self, qubit_cell, center_x, center_y, rotation, name=None):
        """Produces a qubit in a SingleXmons chip.

        Args:
            qubit_cell: PCell of the qubit.
            center_x: X-coordinate of the center of the qubit.
            center_y: Y-coordinate of the center of the qubit.
            rotation: An integer which defines the rotation of the qubit in units of 90 degrees.
            name: A string containing the name of this qubit. Used to set the "id" property of the qubit instance.

        Returns:
            refpoints of the qubit.

        """
        qubit_trans = pya.DTrans(rotation, False, center_x, center_y)
        _, refpoints_abs = self.insert_cell(qubit_cell, qubit_trans, name, rec_levels=None)
        return refpoints_abs

    def _produce_qubits(self):
        """Produces six Swissmon qubits in predefined positions in a SingleXmons chip.

        Three qubits are above the feedline and three are below it. The produced qubits are at equal distances
        from the feedline, and the distances between qubits in the x-direction are equal. The qubits are centered around
        the center of the chip.

        Returns:
            A tuple containing the refpoints of the qubits. Each element in the tuple contains the refpoints for a
            single qubit. The qubits are ordered such that 0,1,2 are the upper qubits (from left to right), while
            3,4,5 are the lower qubits (from left to right).

        """
        qubit = self.add_element(Swissmon,
            fluxline_type="none",
            arm_length=[146] * 4,
            arm_width=[24] * 4,
            gap_width=[24] * 4,
            island_r=2,
            cpl_length=[0, 140, 0],
            cpl_width=[60, 24, 60],
            cpl_gap=[110, 102, 110],
            cl_offset=[200, 200],
        )
        qubit_spacing_x = 1100  # shortest x-distance between qubit centers on different sides of the feedline
        qubit_spacing_y = 2600  # shortest y-distance between qubit centers on different sides of the feedline
        qubits_center_x = 5e3 + 400  # the x-coordinate around which qubits are centered
        # qubits above the feedline, from left to right
        y_a = 5e3 + qubit_spacing_y / 2
        qb0_refpoints = self._produce_qubit(qubit, qubits_center_x - qubit_spacing_x * (3 / 2), y_a, 2, "qb_0")
        qb1_refpoints = self._produce_qubit(qubit, qubits_center_x + qubit_spacing_x / 2, y_a, 2, "qb_1")
        qb2_refpoints = self._produce_qubit(qubit, qubits_center_x + qubit_spacing_x * (5 / 2) - 200, y_a, 2, "qb_2")
        # qubits below the feedline, from left to right
        y_b = 5e3 - qubit_spacing_y / 2
        qb3_refpoints = self._produce_qubit(qubit, qubits_center_x - qubit_spacing_x * (5 / 2), y_b, 0, "qb_3")
        qb4_refpoints = self._produce_qubit(qubit, qubits_center_x - qubit_spacing_x * (1 / 2), y_b, 0, "qb_4")
        qb5_refpoints = self._produce_qubit(qubit, qubits_center_x + qubit_spacing_x * (3 / 2), y_b, 0, "qb_5")
        return qb0_refpoints, qb1_refpoints, qb2_refpoints, qb3_refpoints, qb4_refpoints, qb5_refpoints

    def _produce_readout_resonator(self, total_length, coupling_length, pos_start, above_feedline):
        """Produces a readout resonator coupled to a qubit.

        The resonator consists of waveguide going vertically from the qubit towards the feedline, then going along
        the feedline (coupled to feedline) and finally going away from the feedline as a meander.

        Args:
            total_length: A float defining the total length of the resonator waveguide.
            coupling_length: A float defining the length of the part of the resonator coupled to the feedline.
            pos_start: A DPoint defining the start position of the resonator, should be at one of the qubit ports.
            above_feedline: A boolean value telling if the qubit is above the feedline or not.

        """
        # We define a factor depending on which side of the feedline the qubit is on. This lets us define all resonators
        # in the same way.
        if above_feedline:
            factor = 1
        else:
            factor = -1
        turn_radius = 50
        distance_to_feedline = 27
        feedline_coupling_y = 5e3 + factor * distance_to_feedline
        meander_start_x = pos_start.x - (coupling_length + 2 * turn_radius)
        meander_start = pya.DPoint(meander_start_x, 5e3 + factor * distance_to_feedline +
                                   factor * 2 * turn_radius)
        # non-meandering part of the resonator
        coupler_waveguide = self._produce_waveguide([
            pos_start,
            pya.DPoint(pos_start.x, feedline_coupling_y),
            pya.DPoint(meander_start_x, feedline_coupling_y),
            meander_start
        ], turn_radius=turn_radius)
        len_coupler = coupler_waveguide.length()
        # meandering part of the resonator
        meander_length = total_length - len_coupler
        w = 350
        num_meanders = _get_num_meanders(meander_length, turn_radius, w)
        self.insert_cell(Meander,
            start=meander_start,
            end=meander_start + pya.DPoint(0, 2 * factor * turn_radius * (num_meanders + 1)),
            length=meander_length,
            meanders=num_meanders,
            r=turn_radius,
        )

    def _produce_readout_resonators(self):
        """Produces readout resonators for all the qubits in a SingleXmons chip."""
        readout_res_lengths = [float(length) for length in self.readout_res_lengths]  # from strings to floats
        self._produce_readout_resonator(readout_res_lengths[0], 400, self.qubits_refpoints[0]["port_cplr1"], True)
        self._produce_readout_resonator(readout_res_lengths[1], 400, self.qubits_refpoints[1]["port_cplr1"], True)
        self._produce_readout_resonator(readout_res_lengths[2], 400, self.qubits_refpoints[2]["port_cplr1"], True)
        self._produce_readout_resonator(readout_res_lengths[3], 400, self.qubits_refpoints[3]["port_cplr1"], False)
        self._produce_readout_resonator(readout_res_lengths[4], 400, self.qubits_refpoints[4]["port_cplr1"], False)
        self._produce_readout_resonator(readout_res_lengths[5], 400, self.qubits_refpoints[5]["port_cplr1"], False)

    def _produce_chargeline(self, pos_launcher, pos_port_drive, y_distance):
        """Produces a chargeline from a launcher to a qubit.

        The chargeline is defined in such a way that it works well for the geometry of the a SingleXmons chip.

        Args:
            pos_launcher: A DPoint representing the position of the launcher.
            pos_port_drive: A DPoint representing the position of "port_drive" of the qubit.
            y_distance: A float defining the y-distance of the second point of the chargeline from the launcher.

        """
        points = [pos_launcher, pya.DPoint(pos_port_drive.x, pos_launcher.y + y_distance), pos_port_drive]
        # if y_distance!=0, we use four points to define the chargeline, otherwise three points
        if y_distance != 0:
            points = [points[0]] + [pya.DPoint(pos_launcher.x, pos_launcher.y + y_distance)] + points[1:3]
        self._produce_waveguide(points, term2=self.b)

    def _produce_chargelines(self):
        """Produces chargelines for all of the qubits in a SingleXmons chip."""
        self._produce_chargeline(self.launchers["NW"][0], self.qubits_refpoints[0]["port_drive"], -1300)
        self._produce_chargeline(self.launchers["NE"][0], self.qubits_refpoints[1]["port_drive"], -1300)
        self._produce_chargeline(self.launchers["EN"][0], self.qubits_refpoints[2]["port_drive"], 0)
        self._produce_chargeline(self.launchers["WS"][0], self.qubits_refpoints[3]["port_drive"], 0)
        self._produce_chargeline(self.launchers["SW"][0], self.qubits_refpoints[4]["port_drive"], 1300)
        self._produce_chargeline(self.launchers["SE"][0], self.qubits_refpoints[5]["port_drive"], 1300)

    def _produce_test_resonator(self, capacitor, capacitor_dtrans, res_idx):

        factor = (2*(res_idx % 2) - 1)  # -1 for resonators below feedline, +1 for resonators above feedline
        total_length = float(self.test_res_lengths[res_idx])
        turn_radius = 50

        # non-meandering part of the resonator
        pos_start = self.get_refpoints(capacitor, capacitor_dtrans)["port_a"]
        x1 = 500
        y1 = factor * 300
        y2 = factor * 100
        meander_start = pos_start + pya.DPoint(x1, y1 + y2)
        nonmeander_waveguide = self._produce_waveguide([
            pos_start,
            pos_start + pya.DPoint(0, y1),
            pos_start + pya.DPoint(x1, y1),
            meander_start,
        ], turn_radius=turn_radius)
        len_nonmeander = nonmeander_waveguide.length()

        # meandering part of the resonator
        meander_length = total_length - len_nonmeander
        w = 250
        num_meanders = _get_num_meanders(meander_length, turn_radius, w)
        self.insert_cell(Meander,
            start=meander_start,
            end=meander_start + pya.DPoint(0, 2 * factor * turn_radius * (num_meanders + 1)),
            length=meander_length,
            meanders=num_meanders,
            r=turn_radius,
        )

    def _produce_feedline(self, x_distance):
        """Produces a feedline for a SingleXmons chip.

        The feedline is a waveguide connecting launcher "WN" to launcher "ES". It goes horizontally from the
        launchers towards the center of the chip until it is clear of the junction test pads. Then it goes vertically
        to the center horizontal line, after which it follows the horizontal line until the two sides are connected.

        Args:
            x_distance: A float defining the x-distance of the vertical parts from the launchers. This is used to stay
                clear from the junction test pads.

        """
        self._produce_waveguide([
            self.launchers["WN"][0],
            pya.DPoint(self.launchers["WN"][0].x + x_distance, self.launchers["WN"][0].y),
            pya.DPoint(self.launchers["WN"][0].x + x_distance, 5e3),
            pya.DPoint(self.launchers["ES"][0].x - x_distance, 5e3),
            pya.DPoint(self.launchers["ES"][0].x - x_distance, self.launchers["ES"][0].y),
            self.launchers["ES"][0]
        ])

    def _produce_feedline_and_test_resonators(self, x_distance):
        """Produces a feedline and test resonators for a SingleXmons chip.

        The feedline is a waveguide connecting launcher "WN" to launcher "ES". It goes horizontally from the
        launchers towards the center of the chip until it is clear of the junction test pads. Then it goes vertically
        to the center horizontal line, after which it follows the horizontal line until the two sides are connected.
        There are four test resonators, located between the qubit pairs.

        Args:
            x_distance: A float defining the x-distance of the vertical parts from the launchers. This is used to stay
                clear from the junction test pads.

        """
        x_offset = -700
        test_resonator_positions = [
            pya.DPoint((self.qubits_refpoints[3]["base"].x + self.qubits_refpoints[4]["base"].x) / 2 + x_offset, 5e3),
            pya.DPoint((self.qubits_refpoints[1]["base"].x + self.qubits_refpoints[0]["base"].x) / 2 + x_offset, 5e3),
            pya.DPoint((self.qubits_refpoints[5]["base"].x + self.qubits_refpoints[4]["base"].x) / 2 + x_offset, 5e3),
            pya.DPoint((self.qubits_refpoints[2]["base"].x + self.qubits_refpoints[1]["base"].x) / 2 + x_offset, 5e3)
        ]

        # feedline couplings with test resonators

        cell_cross = self.add_element(WaveguideCoplanarSplitter, **t_cross_parameters(
            a=self.a, b=self.b, a2=self.a, b2=self.b, length_extra_side=2 * self.a))
        inst_crosses = []

        for i in range(4):
            # Cross
            cross_trans = pya.DTrans(2 * (i % 2), False, test_resonator_positions[i])
            inst_cross, _ = self.insert_cell(cell_cross, cross_trans)
            inst_crosses.append(inst_cross)
            cross_refpoints_abs = self.get_refpoints(cell_cross, inst_crosses[i].dtrans)

            # Coupler
            cplr_params = cap_params(float(self.n_fingers[i]), float(self.l_fingers[i]), self.type_coupler[i])
            cplr = self.add_element(**cplr_params)
            cplr_refpoints_rel = self.get_refpoints(cplr)
            if i % 2 == 0:
                cplr_pos = cross_refpoints_abs["port_bottom"] - pya.DTrans.R90 * cplr_refpoints_rel["port_b"]
            else:
                cplr_pos = cross_refpoints_abs["port_bottom"] + pya.DTrans.R90 * cplr_refpoints_rel["port_b"]
            cplr_dtrans = pya.DTrans(2 * (i % 2) + 1, False, cplr_pos.x, cplr_pos.y)
            self.insert_cell(cplr, cplr_dtrans)

            self._produce_test_resonator(cplr, cplr_dtrans, i)

        # feedline

        self._produce_waveguide([
            self.launchers["WN"][0],
            pya.DPoint(self.launchers["WN"][0].x + x_distance, self.launchers["WN"][0].y),
            pya.DPoint(self.launchers["WN"][0].x + x_distance, 5e3),
            self.get_refpoints(cell_cross, inst_crosses[0].dtrans)["port_left"],
            ])
        self._produce_waveguide([
            self.get_refpoints(cell_cross, inst_crosses[0].dtrans)["port_right"],
            self.get_refpoints(cell_cross, inst_crosses[1].dtrans)["port_right"],
           ])
        self._produce_waveguide([
            self.get_refpoints(cell_cross, inst_crosses[1].dtrans)["port_left"],
            self.get_refpoints(cell_cross, inst_crosses[2].dtrans)["port_left"],
            ])
        self._produce_waveguide([
            self.get_refpoints(cell_cross, inst_crosses[2].dtrans)["port_right"],
            self.get_refpoints(cell_cross, inst_crosses[3].dtrans)["port_right"],
        ])
        self._produce_waveguide([
            self.get_refpoints(cell_cross, inst_crosses[3].dtrans)["port_left"],
            pya.DPoint(self.launchers["ES"][0].x - x_distance, 5e3),
            pya.DPoint(self.launchers["ES"][0].x - x_distance, self.launchers["ES"][0].y),
            self.launchers["ES"][0]
        ])
