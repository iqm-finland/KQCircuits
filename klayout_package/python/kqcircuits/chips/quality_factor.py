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
from kqcircuits.elements.waveguide_coplanar_tcross import WaveguideCoplanarTCross
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.util.coupler_lib import produce_library_capacitor
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node


class QualityFactor(Chip):
    """The PCell declaration for a QualityFactor chip."""

    res_lengths = Param(pdt.TypeList, "Resonator lengths", [5434, 5429, 5374, 5412, 5493, 5589])
    n_fingers = Param(pdt.TypeList, "Number of fingers of the coupler", [4, 4, 2, 4, 4, 4])
    l_fingers = Param(pdt.TypeList, "Length of fingers", [23.1, 9.9, 14.1, 10, 21, 28, 3])
    type_coupler = Param(pdt.TypeList, "Coupler type",
                         ["interdigital", "interdigital", "interdigital", "gap", "gap", "gap"])
    n_ab = Param(pdt.TypeList, "Number of resonator airbridges", [5, 0, 5, 5, 5, 5])
    res_term = Param(pdt.TypeList, "Resonator termination type",
        ["galvanic", "galvanic", "galvanic", "airbridge", "airbridge", "airbridge"])
    res_beg = Param(pdt.TypeList, "Resonator beginning type",
        ["galvanic", "galvanic", "galvanic", "airbridge", "airbridge", "airbridge"])
    res_a = Param(pdt.TypeList, "Resonator waveguide center conductor width", [5, 10, 20, 5, 10, 20], unit="[μm]",
                  docstring="Width of the center conductor in the resonators [μm]")
    res_b = Param(pdt.TypeList, "Resonator waveguide gap width", [3, 6, 12, 3, 6, 12], unit="[μm]",
                  docstring="Width of the gap in the resonators [μm]")
    tl_airbridges = Param(pdt.TypeBoolean, "Airbridges on transmission line", True)

    def produce_impl(self):
        # Interpretation of parameter lists
        res_lengths = [float(foo) for foo in self.res_lengths]
        res_a = [float(foo) for foo in self.res_a]
        res_b = [float(foo) for foo in self.res_b]
        n_fingers = [int(foo) for foo in self.n_fingers]
        type_coupler = self.type_coupler
        n_ab = [int(foo) for foo in self.n_ab]
        l_fingers = [float(foo) for foo in self.l_fingers]
        res_term = self.res_term
        res_beg = self.res_beg

        # center the resonators in the chip regardless of size
        max_res_len = max(res_lengths)
        chip_side = self.box.p2.y - self.box.p1.y
        wg_top_y = (chip_side + max_res_len) / 2

        # Non-standard Launchers mimicking SMA8 at 1cm chip size, but keeping fixed distance from the corners
        launchers = self.produce_n_launchers((0, 2, 0, 2), "RF", 300, 180, 800, chip_side - 5600, {4: "WN", 1: "EN"})

        marker_safety = 1.0e3  # depends on the marker size
        points_fl = [launchers["WN"][0],
                     launchers["WN"][0] + pya.DVector(self.r + marker_safety, 0),
                     pya.DPoint(launchers["WN"][0].x + self.r * 2 + marker_safety, wg_top_y)
                     ]
        tl_start = points_fl[-1]

        resonators = len(self.res_lengths)
        v_res_step = (launchers["EN"][0] - launchers["WN"][0] - pya.DVector((self.r * 4 + marker_safety * 2), 0)) * \
                     (1. / resonators)
        cell_cross = self.add_element(WaveguideCoplanarTCross,
            length_extra_side=2 * self.a, a=self.a, b=self.b, a2=self.a, b2=self.b)

        # Airbridge crossing resonators
        cell_ab_crossing = self.add_element(Airbridge)

        for i in range(resonators):
            # Cross
            cross_trans = pya.DTrans(tl_start + v_res_step * (i + 0.5))
            _, cross_refpoints_abs = self.insert_cell(cell_cross, cross_trans)

            # Coupler
            cplr = produce_library_capacitor(self.layout, n_fingers[i], l_fingers[i], type_coupler[i],
                                             a=res_a[i], b=res_b[i], a2=self.a, b2=self.b)
            cplr_refpoints_rel = self.get_refpoints(cplr)
            cplr_pos = cross_refpoints_abs["port_bottom"] - pya.DTrans.R90 * cplr_refpoints_rel["port_b"]
            cplr_trans = pya.DTrans(1, False, cplr_pos.x, cplr_pos.y)
            self.insert_cell(cplr, cplr_trans)

            pos_res_start = cplr_pos + pya.DTrans.R90 * cplr_refpoints_rel["port_a"]
            pos_res_end = pos_res_start + pya.DVector(0, -res_lengths[i])

            # create resonator using WaveguideComposite
            if res_beg[i] == "airbridge":
                node_beg = Node(pos_res_start, AirbridgeConnection, with_side_airbridges=False)
            else:
                node_beg = Node(pos_res_start)

            if res_term[i] == "airbridge":
                node_end = Node(pos_res_end, AirbridgeConnection,
                                with_side_airbridges=False, with_right_waveguide=False, n_bridges=n_ab[i])
            else:
                node_end = Node(pos_res_end, n_bridges=n_ab[i])

            wg = self.add_element(WaveguideComposite, nodes=[node_beg, node_end], a=res_a[i], b=res_b[i])
            self.insert_cell(wg)

            # Feedline
            self.insert_cell(WaveguideCoplanar, **{**self.cell.pcell_parameters_by_name(), **{
                "path": pya.DPath(points_fl + [
                    cross_refpoints_abs["port_left"]
                ], 1),
                "term2": 0
            }})
            points_fl = [cross_refpoints_abs["port_right"]]

            # airbridges on the left and right side of the couplers
            if self.tl_airbridges:
                ab_dist_to_coupler = 60.0
                ab_coupler_left = pya.DPoint((cross_refpoints_abs["port_left"].x) - ab_dist_to_coupler,
                                             (cross_refpoints_abs["port_left"].y))
                ab_coupler_right = pya.DPoint((cross_refpoints_abs["port_right"].x) + ab_dist_to_coupler,
                                              (cross_refpoints_abs["port_right"].y))

                self.insert_cell(cell_ab_crossing, pya.DTrans(0, False, ab_coupler_left))
                self.insert_cell(cell_ab_crossing, pya.DTrans(0, False, ab_coupler_right))

        # Last feedline
        self.insert_cell(WaveguideCoplanar, **{**self.cell.pcell_parameters_by_name(), **{
            "path": pya.DPath(points_fl + [
                pya.DPoint(launchers["EN"][0].x - self.r * 2 - marker_safety, wg_top_y),
                launchers["EN"][0] + pya.DVector(-self.r - marker_safety, 0),
                launchers["EN"][0]
            ], 1),
            "term2": 0
        }})

        # Basis chip with possibly ground plane grid
        super().produce_impl()
