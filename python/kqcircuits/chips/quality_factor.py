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
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper
from kqcircuits.elements.waveguide_coplanar_tcross import WaveguideCoplanarTCross
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.util.coupler_lib import produce_library_capacitor


# v1.1
# With this version of the qfactor, airbridges to the left and right parts of the resonators are added.
# -The padding size for layer_3 has been changed to 25 um * 23 um.
# -The bridge measurements on the layer_4 changed to 42 um * 18 um.
# -The pad measurements layer_4 has been changed to 21 um * 19 um.

version = 1.1


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
    res_a = Param(pdt.TypeDouble, "Resonator waveguide center conductor width", 10, unit="[μm]")
    res_b = Param(pdt.TypeDouble, "Resonator waveguide gap width", 6, unit="[μm]")
    tl_airbridges = Param(pdt.TypeBoolean, "Airbridges on transmission line", True)

    def produce_impl(self):
        # Interpretation of parameter lists
        res_lengths = [float(foo) for foo in self.res_lengths]
        n_fingers = [int(foo) for foo in self.n_fingers]
        type_coupler = self.type_coupler
        n_ab = [int(foo) for foo in self.n_ab]
        l_fingers = [float(foo) for foo in self.l_fingers]
        res_term = self.res_term
        res_beg = self.res_beg

        # Launchers
        launchers = self.produce_launchers_SMA8(enabled=["WN", "EN"])

        marker_safety = 1.0e3  # depends on the marker size
        points_fl = [launchers["WN"][0],
                     launchers["WN"][0] + pya.DVector(self.r + marker_safety, 0),
                     launchers["WN"][0] + pya.DVector(self.r + marker_safety, 1.1e3),
                     launchers["WN"][0] + pya.DVector(self.r * 2 + marker_safety, 1.1e3)
                     ]
        tl_start = points_fl[-1]

        resonators = len(self.res_lengths)
        v_res_step = (launchers["EN"][0] - launchers["WN"][0] - pya.DVector((self.r * 4 + marker_safety * 2), 0)) * \
                     (1. / resonators)
        cell_cross = self.add_element(WaveguideCoplanarTCross,
            length_extra_side=2 * self.a)

        # Airbridge crossing resonators
        cell_ab_crossing = self.add_element(Airbridge)

        # todo
        # Airbridge for beginning of a resonator
        cell_ab_beginning = self.add_element(Airbridge,
            pad_width=self.a - 2,
            pad_length=self.a * 2,
            bridge_length=self.b * 1 + 4 + 19,
            bridge_width=self.a - 2,
            pad_extra=0,

        )

        for i in range(resonators):
            # Cross
            cross_trans = pya.DTrans(tl_start + v_res_step * (i + 0.5))
            _, cross_refpoints_abs = self.insert_cell(cell_cross, cross_trans)

            # Coupler
            cplr = produce_library_capacitor(self.layout, n_fingers[i], l_fingers[i], type_coupler[i])
            cplr_refpoints_rel = self.get_refpoints(cplr)
            cplr_pos = cross_refpoints_abs["port_bottom"] - pya.DTrans.R90 * cplr_refpoints_rel["port_b"]
            cplr_trans = pya.DTrans(1, False, cplr_pos.x, cplr_pos.y)
            self.insert_cell(cplr, cplr_trans)

            pos_res_start = cplr_pos + pya.DTrans.R90 * cplr_refpoints_rel["port_a"]
            pos_res_end = pos_res_start + pya.DVector(0, -res_lengths[i])

            # todo
            if res_beg[i] == "airbridge":
                pos_res_start = cplr_pos + pya.DTrans.R90 * cplr_refpoints_rel["port_a"] + \
                    pya.DVector(0, self.a - 65)  # todo
                pos_res_end = pos_res_start + pya.DVector(0, -res_lengths[i]) + pya.DVector(0, self.a + 45)  # todo

                pos_beg_ab = pos_res_start + pya.DVector(0, -self.b / 2 + 16)  # todo
                self.insert_cell(cell_ab_beginning, pya.DTrans(0, False, pos_beg_ab))

                pos_conn_start = cplr_pos + pya.DTrans.R90 * cplr_refpoints_rel["port_a"]

                self.insert_cell(WaveguideCoplanar,
                    path=pya.DPath([
                        pos_conn_start,
                        pos_conn_start + pya.DVector(0, self.a - 40),
                    ], 1),
                    term2=self.b,
                    term1=0,
                    a=self.res_a,
                    b=self.res_b,
                )

                end_term_1 = self.b
            else:

                # waveguide taper for connecting resonator to capacitor
                if self.res_a != self.a or self.res_b != self.b:
                    taper_length = 100
                    self.insert_cell(WaveguideCoplanarTaper, pya.DTrans(3, False, pos_res_start),
                        taper_length=taper_length,
                        a1=self.a,
                        b1=self.b,
                        m1=self.margin,
                        a2=self.res_a,
                        b2=self.res_b,
                        m2=self.margin,
                    )
                    pos_res_start -= pya.DPoint(0, taper_length)

                end_term_1 = 0

            if res_term[i] == "airbridge":
                # add airbridge termination
                cell_ab_terminate = self.add_element(AirbridgeConnection,
                    with_side_airbridges=False,
                    with_right_waveguide=False,
                )
                ab_terminate_params = cell_ab_terminate.pcell_parameters_by_name()
                bridge_length = ab_terminate_params["bridge_length"]
                pad_length = ab_terminate_params["pad_length"]
                taper_length = ab_terminate_params["taper_length"]
                pos_term_ab = pos_res_end + pya.DVector(0, bridge_length/2)
                self.insert_cell(cell_ab_terminate, pya.DTrans(3, False, pos_term_ab))
                # end point of even-width part of the resonator waveguide
                pos_even_width_end = pos_term_ab + pya.DVector(0, bridge_length/2 + 2*pad_length + taper_length)
            else:
                pos_even_width_end = pos_res_end  # end point of even-width part of the resonator waveguide

            # the even-width part of the resonator between possible tapers at the ends
            self.insert_cell(WaveguideCoplanar,
                path=pya.DPath([
                    pos_res_start,
                    pos_even_width_end,
                ], 1),
                term1=end_term_1,
                a=self.res_a,
                b=self.res_b,
            )

            # Feedline
            self.insert_cell(WaveguideCoplanar, **{**self.cell.pcell_parameters_by_name(), **{
                "path": pya.DPath(points_fl + [
                    cross_refpoints_abs["port_left"]
                ], 1),
                "term2": 0
            }})
            points_fl = [cross_refpoints_abs["port_right"]]

            # Airbridges
            if n_ab[i]:
                ab_step = (pos_res_end - pos_res_start) * (1. / n_ab[i])
                for j in range(n_ab[i]):
                    pos_ab = pos_res_start + ab_step * (j + 0.5)
                    self.insert_cell(cell_ab_crossing, pya.DTrans(1, False, pos_ab))

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
                launchers["EN"][0] + pya.DVector(-self.r * 2 - marker_safety, 1.1e3),
                launchers["EN"][0] + pya.DVector(-self.r - marker_safety, 1.1e3),
                launchers["EN"][0] + pya.DVector(-self.r - marker_safety, 0),
                launchers["EN"][0]
            ], 1),
            "term2": 0
        }})

        # Basis chip with possibly ground plane grid
        super().produce_impl()
