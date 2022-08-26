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

from kqcircuits.chips.chip import Chip
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.elements.meander import Meander
from kqcircuits.junctions.squid import Squid
from kqcircuits.qubits.swissmon import Swissmon
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter, t_cross_parameters
from kqcircuits.util.coupler_lib import cap_params


class Shaping(Chip):
    """The PCell declaration for a Shaping chip."""

    tunable = Param(pdt.TypeBoolean, "Tunable", False)

    def build(self):

        # Launcher
        launchers = self.produce_launchers("SMA8")

        # Finnmon
        _, finnmon_refpoints_abs = self.insert_cell(Swissmon, pya.DTrans(3, False, 4000, 5000),
            arm_width=[30, 23, 30, 23],
            arm_length=[190, 96, 160, 96],
            gap_width=[29.5, 33, 29.5, 33],
            island_r=2,
            cpl_length=[235, 0, 205],
            cpl_width=[60, 42, 60],
            cpl_gap=[110, 112, 110],
            cl_offset=[150, 150]
        )

        port_qubit_dr = finnmon_refpoints_abs["port_drive"]
        port_qubit_fl = finnmon_refpoints_abs["port_flux"]
        port_qubit_ro = finnmon_refpoints_abs["port_cplr0"]
        port_qubit_sh = finnmon_refpoints_abs["port_cplr2"]

        # Chargeline
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                launchers["WN"][0],
                launchers["WN"][0] + pya.DVector(self.r, 0),
                pya.DPoint((launchers["WN"][0] + pya.DVector(self.r, 0)).x, port_qubit_dr.y),
                port_qubit_dr - pya.DVector(self.r, 0),
                port_qubit_dr
            ], 1),
            term2=self.b,
        )

        # Fluxline
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                launchers["WS"][0],
                launchers["WS"][0] + pya.DVector(self.r, 0),
                pya.DPoint((launchers["WS"][0] + pya.DVector(self.r, 0)).x, port_qubit_fl.y),
                port_qubit_fl - pya.DVector(self.r, 0),
                port_qubit_fl
            ], 1),
        )

        ####### Readout resonator with the purcell filter

        segment_length_target_rr = [611.586, 1834.76, 611.586]  # from qubit to shorted end
        segment_length_target_pr = [3158.32, 789.581]  # from output to shorted end
        caps_fingers = [4, 4, 4]  # J, kappa, drive
        caps_length = [37.5, 67.9, 36.2]  # J, kappa, drive
        caps_type = ["gap", "interdigital", "gap"]  # J, kappa, drive

        # Waveguide t-cross used in multiple locations
        cross1 = self.add_element(WaveguideCoplanarSplitter, **t_cross_parameters(
            a=self.a, b=self.b, a2=self.a, b2=self.b, length_extra_side=2 * self.a, length_extra=50))
        cross1_refpoints_rel = self.get_refpoints(cross1, pya.DTrans(0, False, 0, 0))
        cross1_length = cross1_refpoints_rel["port_right"].distance(cross1_refpoints_rel["port_left"])

        # Readout resonator first segment
        wg1_end = port_qubit_ro + pya.DVector(0, segment_length_target_rr[0] - cross1_length)
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                port_qubit_ro,
                port_qubit_ro + pya.DVector(0, self.r),
                wg1_end + pya.DVector(0, -self.r),
                wg1_end,
            ], 1),
        )

        waveguide_length = cross1_length + cross1_refpoints_rel["base"].distance(cross1_refpoints_rel["port_bottom"])
        _, cross1_refpoints_abs = self.insert_cell(
            cross1,
            pya.DTrans(1, False, wg1_end - pya.DTrans(1, False, 0, 0) * cross1_refpoints_rel["port_left"])
        )

        meander2_end = cross1_refpoints_abs["port_bottom"] + pya.DVector(630, 0)
        self.insert_cell(Meander,
            start=cross1_refpoints_abs["port_bottom"],
            end=meander2_end,
            length=segment_length_target_rr[1] - waveguide_length,
            meanders=2,
        )

        cross2_refpoints_rel = self.get_refpoints(cross1, pya.DTrans(2, False, 0, 0))
        port_rel_cross2_wg2 = cross2_refpoints_rel["port_right"]
        _, port_abs_cross2 = self.insert_cell(
            cross1, pya.DTrans(2, False, meander2_end - port_rel_cross2_wg2))

        # Last bit of the readout resonator
        waveguide_length = cross1_refpoints_rel["base"].distance(cross1_refpoints_rel["port_bottom"])
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                port_abs_cross2["port_bottom"],
                port_abs_cross2["port_bottom"] + pya.DVector(0, (segment_length_target_rr[2] - waveguide_length))
            ], 1),
        )

        # Capacitor J
        capj = self.add_element(**cap_params(caps_fingers[0], caps_length[0], caps_type[0]))
        port_rel_capj = self.get_refpoints(capj, pya.DTrans())
        self.insert_cell(capj, pya.DTrans(port_abs_cross2["port_left"] - port_rel_capj["port_a"]))

        _, port_abs_cross3 = self.insert_cell(
            cross1, pya.DTrans(2, False, port_abs_cross2["port_left"] -
                               port_rel_capj["port_a"] + port_rel_capj["port_b"] - port_rel_cross2_wg2))
        waveguide_length = cross1_length

        meander3_end = port_abs_cross3["port_left"] + pya.DVector(900, 0)

        waveguide2 = self.add_element(WaveguideCoplanar,
            path=pya.DPath([
                meander3_end,
                meander3_end + pya.DVector(self.r, 0),
                meander3_end + pya.DVector(self.r, 400),
                meander3_end + pya.DVector(self.r, 400 + self.r),
            ], 1),
        )
        self.insert_cell(waveguide2)

        waveguide_length += waveguide2.length()

        self.insert_cell(Meander,
                         start=port_abs_cross3["port_left"],
                         end=meander3_end,
                         length=segment_length_target_pr[0] - waveguide_length,
                         meanders=3,
                         )

        # Last bit of the Purcell filter of RR
        waveguide_length = cross1_refpoints_rel["base"].distance(cross1_refpoints_rel["port_bottom"])
        wg6_end = port_abs_cross3["port_bottom"] + pya.DVector(0, (segment_length_target_pr[1] - waveguide_length))
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                port_abs_cross3["port_bottom"],
                wg6_end
            ], 1),
            term2=(40 if self.tunable else 0)
        )

        # Purcell resonator SQUID
        if self.tunable:
            # SQUID refpoint at the ground plane edge
            transf = pya.DTrans(2, False, wg6_end + pya.DVector(0, 40))
            self.insert_cell(Squid, transf)

            self.insert_cell(WaveguideCoplanar,
                path=pya.DPath([
                    wg6_end + pya.DVector(-20, 40 + 15),
                    wg6_end + pya.DVector(+20 + self.r, 40 + 15),
                    pya.DPoint((wg6_end + pya.DVector(+20 + self.r, 40 + 15)).x, (launchers["NE"][0]).y - self.r),
                    launchers["NE"][0] + pya.DVector(0, -self.r),
                    launchers["NE"][0] + pya.DVector(0, 0),
                ], 1),
            )

        # Capacitor Kappa
        capk = self.add_element(**cap_params(caps_fingers[1], caps_length[1], caps_type[1]))
        port_rel_capk = self.get_refpoints(capk, pya.DTrans(1, False, 0, 0))
        _, port_abs_capk = self.insert_cell(capk, pya.DTrans(1, False,
                                           meander3_end + pya.DVector(self.r, 400 + self.r) -
                                           port_rel_capk["port_a"]))

        # Output port of the purcell resonator
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                port_abs_capk["port_b"],
                port_abs_capk["port_b"] + pya.DVector(0, self.r),
                pya.DPoint((port_abs_capk["port_b"] + pya.DVector(0, self.r)).x, launchers["EN"][0].y),
                launchers["EN"][0] + pya.DVector(-self.r, 0),
                launchers["EN"][0],
            ], 1),
        )

        # Capacitor for the driveline
        capi = self.add_element(**cap_params(caps_fingers[2], caps_length[2], caps_type[2]))
        port_rel_capi = self.get_refpoints(capi, pya.DTrans(1, False, 0, 0))
        _, port_abs_capi = self.insert_cell(capi, pya.DTrans(1, False, cross1_refpoints_abs["port_right"] -
                                                             port_rel_capi["port_a"]))

        # Driveline of the readout resonator
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                port_abs_capi["port_b"],
                port_abs_capi["port_b"] + pya.DVector(0, self.r),
                pya.DPoint(launchers["NW"][0].x, (port_abs_capi["port_b"] + pya.DVector(0, self.r)).y),
                launchers["NW"][0] + pya.DVector(0, -self.r),
                launchers["NW"][0] + pya.DVector(0, 0),
            ], 1),
        )

        ####### Shaping resonator with the purcell filter

        segment_length_target_rr = [634.71, 1904.13, 634.71]  # from qubit to shorted end
        segment_length_target_pr = [3253.65, 813.413]  # from output to shorted end
        caps_fingers = [4, 4, 4]  # J, kappa, drive
        caps_length = [36.8, 71.5, 36.2]  # J, kappa, drive
        caps_type = ["gap", "interdigital", "gap"]  # J, kappa, drive

        # Readout resonator first segment
        wg1_end = port_qubit_sh + pya.DVector(0, -(segment_length_target_rr[0] - cross1_length))
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                port_qubit_sh,
                port_qubit_sh + pya.DVector(0, -self.r),
                wg1_end + pya.DVector(0, +self.r),
                wg1_end,
            ], 1),
        )

        waveguide_length = cross1_length + cross1_refpoints_rel["base"].distance(cross1_refpoints_rel["port_bottom"])
        _, cross1_refpoints_abs = self.insert_cell(
            cross1,
            pya.DTrans(1, False, wg1_end - pya.DTrans(1, False, 0, 0) * cross1_refpoints_rel["port_right"])
        )

        meander2_end = cross1_refpoints_abs["port_bottom"] + pya.DVector(630, 0)
        self.insert_cell(Meander,
            start=cross1_refpoints_abs["port_bottom"],
            end=meander2_end,
            length=segment_length_target_rr[1] - waveguide_length,
            meanders=2,
        )

        cross2_refpoints_rel = self.get_refpoints(cross1, pya.DTrans(0, False, 0, 0))
        port_rel_cross2_wg2 = cross2_refpoints_rel["port_left"]
        _, port_abs_cross2 = self.insert_cell(cross1,
                                                        pya.DTrans(0, False, meander2_end - port_rel_cross2_wg2))

        # Last bit of the readout resonator
        waveguide_length = cross1_refpoints_rel["base"].distance(cross1_refpoints_rel["port_bottom"])
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                port_abs_cross2["port_bottom"],
                port_abs_cross2["port_bottom"] + pya.DVector(0, -(segment_length_target_rr[2] - waveguide_length))
            ], 1),
        )

        # Capacitor J
        capj = self.add_element(**cap_params(caps_fingers[0], caps_length[0], caps_type[0]))
        port_rel_capj = self.get_refpoints(capj)
        self.insert_cell(capj, pya.DTrans(port_abs_cross2["port_right"] - port_rel_capj["port_a"]))

        _, port_abs_cross3 = self.insert_cell(cross1,
                                       pya.DTrans(0, False,
                                                  port_abs_cross2["port_right"] - port_rel_capj["port_a"] +
                                                  port_rel_capj["port_b"] - port_rel_cross2_wg2))
        waveguide_length = cross1_length

        meander3_end = port_abs_cross3["port_right"] + pya.DVector(900, 0)
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                meander3_end,
                meander3_end + pya.DVector(self.r, 0),
                meander3_end + pya.DVector(self.r, -400),
                meander3_end + pya.DVector(self.r, -400 - self.r),
            ], 1),
        )

        waveguide_length += waveguide2.length()

        self.insert_cell(Meander,
                         start=port_abs_cross3["port_right"],
                         end=meander3_end,
                         length=segment_length_target_pr[0] - waveguide_length,
                         meanders=3,
                         )

        # Last bit of the Purcell filter of shaping resonator
        waveguide_length = cross1_refpoints_rel["base"].distance(cross1_refpoints_rel["port_bottom"])
        wg6_end = port_abs_cross3["port_bottom"] + pya.DVector(0, -(segment_length_target_pr[1] - waveguide_length))
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                port_abs_cross3["port_bottom"],
                wg6_end
            ], 1),
            term2=(40 if self.tunable else 0)
        )

        # Purcell resonator SQUID
        if self.tunable:
            # SQUID refpoint at the ground plane edge
            transf = pya.DTrans(0, False, wg6_end + pya.DVector(0, -40))
            self.insert_cell(Squid, transf)

            self.insert_cell(WaveguideCoplanar,
                path=pya.DPath([
                    wg6_end + pya.DVector(-20, -40 - 15),
                    wg6_end + pya.DVector(+20 + self.r, -40 - 15),
                    pya.DPoint((wg6_end + pya.DVector(+20 + self.r, -40 - 15)).x, (launchers["SE"][0]).y + self.r),
                    launchers["SE"][0] + pya.DVector(0, self.r),
                    launchers["SE"][0] + pya.DVector(0, 0),
                ], 1),
            )

        # Capacitor Kappa
        capk = self.add_element(**cap_params(caps_fingers[1], caps_length[1], caps_type[1]))
        port_rel_capk = self.get_refpoints(capk, pya.DTrans(3, False, 0, 0))
        _, port_abs_capk = self.insert_cell(capk, pya.DTrans(3, False,
                                                                     meander3_end + pya.DVector(self.r, -400 - self.r) -
                                                                     port_rel_capk["port_a"]))

        # Output port of the purcell resonator
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                port_abs_capk["port_b"],
                port_abs_capk["port_b"] + pya.DVector(0, -self.r),
                pya.DPoint((port_abs_capk["port_b"] + pya.DVector(0, -self.r)).x, (launchers["ES"][0]).y),
                launchers["ES"][0] + pya.DVector(-self.r, 0),
                launchers["ES"][0] + pya.DVector(0, 0),
            ], 1),
        )

        # Capacitor for the driveline
        capi = self.add_element(**cap_params(caps_fingers[2], caps_length[2], caps_type[2]))
        port_rel_capi = self.get_refpoints(capi, pya.DTrans(3, False, 0, 0))
        _, port_abs_capi = self.insert_cell(
            capi, pya.DTrans(3, False, cross1_refpoints_abs["port_left"] - port_rel_capi["port_a"]))

        # Driveline of the shaping resonator
        self.insert_cell(WaveguideCoplanar,
            path=pya.DPath([
                port_abs_capi["port_b"],
                port_abs_capi["port_b"] + pya.DVector(0, -self.r),
                pya.DPoint(launchers["SW"][0].x, (port_abs_capi["port_b"] + pya.DVector(0, -self.r)).y),
                launchers["SW"][0] + pya.DVector(0, self.r),
                launchers["SW"][0] + pya.DVector(0, 0),
            ], 1),
        )
