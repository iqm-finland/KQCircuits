# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import sys
from importlib import reload

from kqcircuits.pya_resolver import pya

from kqcircuits.chips.chip import Chip
from kqcircuits.elements.element import Element
from kqcircuits.elements.meander import Meander
from kqcircuits.elements.qubits.swissmon import Swissmon
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_tcross import WaveguideCoplanarTCross
from kqcircuits.util.coupler_lib import produce_library_capacitor


reload(sys.modules[Chip.__module__])

version = 1


class Shaping(Chip):
    """The PCell declaration for a Shaping chip."""

    PARAMETERS_SCHEMA = {
        "tunable": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Tunable",
            "default": False
        }
    }

    def __init__(self):
        super().__init__()
        self.r = 100

    def produce_impl(self):

        # Launcher
        launchers = self.produce_launchers_SMA8()

        # Finnmon
        finnmon = Swissmon.create_cell(self.layout, {
            "fluxline": True,
            "arm_width": [30, 23, 30, 23],
            "arm_length": [190, 96, 160, 96],
            "gap_width": 89,
            "corner_r": 2,
            "cpl_length": [235, 0, 205],
            "cpl_width": [60, 42, 60],
            "cpl_gap": [110, 112, 110],
            "cl_offset": [150, 150]
        })
        finnmon_inst, finnmon_refpoints_abs = self.insert_cell(finnmon, pya.DTrans(3, False, 4000, 5000))
        
        port_qubit_dr = finnmon_refpoints_abs["port_drive"]
        port_qubit_fl = finnmon_refpoints_abs["port_flux"]
        port_qubit_ro = finnmon_refpoints_abs["port_cplr0"]
        port_qubit_sh = finnmon_refpoints_abs["port_cplr2"]

        # Chargeline
        tl = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                launchers["WN"][0],
                launchers["WN"][0] + pya.DVector(self.r, 0),
                pya.DPoint((launchers["WN"][0] + pya.DVector(self.r, 0)).x, port_qubit_dr.y),
                port_qubit_dr - pya.DVector(self.r, 0),
                port_qubit_dr
            ], 1),
            "r": self.r,
            "term2": self.b,
        })
        self.insert_cell(tl)

        # Fluxline
        fl = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                launchers["WS"][0],
                launchers["WS"][0] + pya.DVector(self.r, 0),
                pya.DPoint((launchers["WS"][0] + pya.DVector(self.r, 0)).x, port_qubit_fl.y),
                port_qubit_fl - pya.DVector(self.r, 0),
                port_qubit_fl
            ], 1),
            "r": self.r
        })
        self.insert_cell(fl)

        ####### Readout resonator with the purcell filter

        segment_length_target_rr = [611.586, 1834.76, 611.586]  # from qubit to shorted end
        segment_length_target_pr = [3158.32, 789.581]  # from output to shorted end
        caps_fingers = [4, 4, 4]  # J, kappa, drive
        caps_length = [37.5, 67.9, 36.2]  # J, kappa, drive
        caps_type = ["plate", "square", "plate"]  # J, kappa, drive

        # Waveguide t-cross used in multiple locations
        cross1 = WaveguideCoplanarTCross.create_cell(self.layout, {
            "length_extra_side": 2 * self.a,
            "length_extra": 50,
            "r": self.r})
        cross1_refpoints_rel = self.get_refpoints(cross1, pya.DTrans(0, False, 0, 0))
        cross1_length = cross1_refpoints_rel["port_right"].distance(cross1_refpoints_rel["port_left"])

        # Readout resonator first segement
        waveguide_length = 0
        wg1_end = port_qubit_ro + pya.DVector(0, segment_length_target_rr[0] - cross1_length)
        waveguide1 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                port_qubit_ro,
                port_qubit_ro + pya.DVector(0, self.r),
                wg1_end + pya.DVector(0, -self.r),
                wg1_end,
            ], 1),
            "r": self.r
        })
        self.insert_cell(waveguide1)

        waveguide_length = cross1_length + cross1_refpoints_rel["base"].distance(cross1_refpoints_rel["port_bottom"])
        cross1_inst, cross1_refpoints_abs = self.insert_cell(
            cross1,
            pya.DTrans(1, False, wg1_end - pya.DTrans(1, False, 0, 0) * cross1_refpoints_rel["port_left"])
        )

        meander2_end = cross1_refpoints_abs["port_bottom"] + pya.DVector(630, 0)
        meander2 = Meander.create_cell(self.layout, {
            "start": cross1_refpoints_abs["port_bottom"],
            "end": meander2_end,
            "length": segment_length_target_rr[1] - waveguide_length,
            "meanders": 2,
            "r": self.r
        })
        self.insert_cell(meander2)

        cross2_refpoints_rel = self.get_refpoints(cross1, pya.DTrans(2, False, 0, 0))
        port_rel_cross2_wg2 = cross2_refpoints_rel["port_right"]
        port_rel_cross2_jcap = cross2_refpoints_rel["port_left"]
        port_rel_cross2_wg3 = cross2_refpoints_rel["port_bottom"]
        cross2_inst, port_abs_cross2 = self.insert_cell(
            cross1, pya.DTrans(2, False, meander2_end - port_rel_cross2_wg2))

        # Last bit of the readout resonator
        waveguide_length = cross1_refpoints_rel["base"].distance(cross1_refpoints_rel["port_bottom"])
        waveguide5 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                port_abs_cross2["port_bottom"],
                port_abs_cross2["port_bottom"] + pya.DVector(0, (segment_length_target_rr[2] - waveguide_length))
            ], 1),
            "r": self.r
        })
        self.insert_cell(waveguide5)

        # Capacitor J
        capj = produce_library_capacitor(self.layout, caps_fingers[0], caps_length[0], caps_type[0])

        FingerCapacitorSquare.create_cell(self.layout, {
            "finger_number": 2
        })
        port_rel_capj = self.get_refpoints(capj, pya.DTrans())
        self.insert_cell(capj, pya.DTrans(port_abs_cross2["port_left"] - port_rel_capj["port_a"]))

        cross3_inst, port_abs_cross3 = self.insert_cell(
            cross1, pya.DTrans(2, False, port_abs_cross2["port_left"] -
                               port_rel_capj["port_a"] + port_rel_capj["port_b"] - port_rel_cross2_wg2))
        waveguide_length = cross1_length

        meander3_end = port_abs_cross3["port_left"] + pya.DVector(900, 0)
        meander3 = Meander.create_cell(self.layout, {
            "start": port_abs_cross3["port_left"],
            "end": meander3_end,
            "length": 1500,
            "meanders": 3,
            "r": self.r
        })
        meander3_inst, meander3_inst_ref = self.insert_cell(meander3)

        waveguide2 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                meander3_end,
                meander3_end + pya.DVector(self.r, 0),
                meander3_end + pya.DVector(self.r, 400),
                meander3_end + pya.DVector(self.r, 400 + self.r),
            ], 1),
            "r": self.r
        })
        self.insert_cell(waveguide2)

        waveguide_length += WaveguideCoplanar.get_length(waveguide2, self.layout.layer(self.la))
        meander3_inst.change_pcell_parameter("length", segment_length_target_pr[0] - waveguide_length)

        # Last bit of the Purcell filter of RR
        waveguide_length = cross1_refpoints_rel["base"].distance(cross1_refpoints_rel["port_bottom"])
        wg6_end = port_abs_cross3["port_bottom"] + pya.DVector(0, (segment_length_target_pr[1] - waveguide_length))
        waveguide6 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                port_abs_cross3["port_bottom"],
                wg6_end
            ], 1),
            "r": self.r,
            "term2": (40 if self.tunable else 0)
        })
        self.insert_cell(waveguide6)

        # Purcell resonator SQUID
        if (self.tunable):
            # SQUID refpoint at the ground plane edge
            squid_cell = Element.create_cell_from_shape(self.layout, "QCD1")
            transf = pya.DTrans(2, False, wg6_end + pya.DVector(0, 40))
            self.insert_cell(squid_cell, transf)

            waveguide_restune = WaveguideCoplanar.create_cell(self.layout, {
                "path": pya.DPath([
                    wg6_end + pya.DVector(-20, 40 + 15),
                    wg6_end + pya.DVector(+20 + self.r, 40 + 15),
                    pya.DPoint((wg6_end + pya.DVector(+20 + self.r, 40 + 15)).x, (launchers["NE"][0]).y - self.r),
                    launchers["NE"][0] + pya.DVector(0, -self.r),
                    launchers["NE"][0] + pya.DVector(0, 0),
                ], 1),
                "r": self.r
            })
            self.insert_cell(waveguide_restune)

        # Capacitor Kappa
        capk = produce_library_capacitor(self.layout, caps_fingers[1], caps_length[1], caps_type[1])
        port_rel_capk = self.get_refpoints(capk, pya.DTrans(1, False, 0, 0))
        capk_inst, port_abs_capk = self.insert_cell(capk, pya.DTrans(1, False,
                                           meander3_end + pya.DVector(self.r, 400 + self.r) -
                                           port_rel_capk["port_a"]))

        # Output port of the purcell resonator
        waveguide3 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                port_abs_capk["port_b"],
                port_abs_capk["port_b"] + pya.DVector(0, self.r),
                pya.DPoint((port_abs_capk["port_b"] + pya.DVector(0, self.r)).x, launchers["EN"][0].y),
                launchers["EN"][0] + pya.DVector(-self.r, 0),
                launchers["EN"][0],
            ], 1),
            "r": self.r
        })
        self.insert_cell(waveguide3)
        waveguide_length = 0

        # Capacitor for the driveline
        capi = produce_library_capacitor(self.layout, caps_fingers[2], caps_length[2], caps_type[2])
        port_rel_capi = self.get_refpoints(capi, pya.DTrans(1, False, 0, 0))
        capi_inst, port_abs_capi = self.insert_cell(capi,
                                     pya.DTrans(1, False,
                                               cross1_refpoints_abs["port_right"] - port_rel_capi[
                                                   "port_a"]))

        # Driveline of the readout resonator
        waveguide4 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                port_abs_capi["port_b"],
                port_abs_capi["port_b"] + pya.DVector(0, self.r),
                pya.DPoint(launchers["NW"][0].x, (port_abs_capi["port_b"] + pya.DVector(0, self.r)).y),
                launchers["NW"][0] + pya.DVector(0, -self.r),
                launchers["NW"][0] + pya.DVector(0, 0),
            ], 1),
            "r": self.r
        })
        self.insert_cell(waveguide4)

        ####### Shaping resonator with the purcell filter

        segment_length_target_rr = [634.71, 1904.13, 634.71]  # from qubit to shorted end
        segment_length_target_pr = [3253.65, 813.413]  # from output to shorted end
        caps_fingers = [4, 4, 4]  # J, kappa, drive
        caps_length = [36.8, 71.5, 36.2]  # J, kappa, drive
        caps_type = ["plate", "square", "plate"]  # J, kappa, drive

        # Readout resonator first segement
        waveguide_length = 0
        wg1_end = port_qubit_sh + pya.DVector(0, -(segment_length_target_rr[0] - cross1_length))
        waveguide1 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                port_qubit_sh,
                port_qubit_sh + pya.DVector(0, -self.r),
                wg1_end + pya.DVector(0, +self.r),
                wg1_end,
            ], 1),
            "r": self.r
        })
        self.insert_cell(waveguide1)

        waveguide_length = cross1_length + cross1_refpoints_rel["base"].distance(cross1_refpoints_rel["port_bottom"])
        cross1_inst, cross1_refpoints_abs = self.insert_cell(
            cross1,
            pya.DTrans(1, False, wg1_end - pya.DTrans(1, False, 0, 0) * cross1_refpoints_rel["port_right"])
        )

        meander2_end = cross1_refpoints_abs["port_bottom"] + pya.DVector(630, 0)
        meander2 = Meander.create_cell(self.layout, {
            "start": cross1_refpoints_abs["port_bottom"],
            "end": meander2_end,
            "length": segment_length_target_rr[1] - waveguide_length,
            "meanders": 2,
            "r": self.r
        })
        self.insert_cell(meander2)

        cross2_refpoints_rel = self.get_refpoints(cross1, pya.DTrans(0, False, 0, 0))
        port_rel_cross2_wg2 = cross2_refpoints_rel["port_left"]
        port_rel_cross2_jcap = cross2_refpoints_rel["port_right"]
        port_rel_cross2_wg3 = cross2_refpoints_rel["port_bottom"]
        cross2_inst, port_abs_cross2 = self.insert_cell(cross1,
                                                        pya.DTrans(0, False, meander2_end - port_rel_cross2_wg2))

        # Last bit of the readout resonator
        waveguide_length = cross1_refpoints_rel["base"].distance(cross1_refpoints_rel["port_bottom"])
        waveguide5 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                port_abs_cross2["port_bottom"],
                port_abs_cross2["port_bottom"] + pya.DVector(0, -(segment_length_target_rr[2] - waveguide_length))
            ], 1),
            "r": self.r
        })
        self.insert_cell(waveguide5)

        # Capacitor J
        capj = produce_library_capacitor(self.layout, caps_fingers[0], caps_length[0], caps_type[0])
        port_rel_capj = self.get_refpoints(capj)
        self.insert_cell(capj, pya.DTrans(port_abs_cross2["port_right"] - port_rel_capj["port_a"]))

        cross3_inst, port_abs_cross3 = self.insert_cell(cross1,
                                       pya.DTrans(0, False,
                                                  port_abs_cross2["port_right"] - port_rel_capj["port_a"] +
                                                  port_rel_capj["port_b"] - port_rel_cross2_wg2))
        waveguide_length = cross1_length

        meander3_end = port_abs_cross3["port_right"] + pya.DVector(900, 0)
        meander3 = Meander.create_cell(self.layout, {
            "start": port_abs_cross3["port_right"],
            "end": meander3_end,
            "length": 1500,
            "meanders": 3,
            "r": self.r
        })
        meander3_inst, meander3_inst_ref = self.insert_cell(meander3)

        waveguide2 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                meander3_end,
                meander3_end + pya.DVector(self.r, 0),
                meander3_end + pya.DVector(self.r, -400),
                meander3_end + pya.DVector(self.r, -400 - self.r),
            ], 1),
            "r": self.r
        })
        self.insert_cell(waveguide2)

        waveguide_length += WaveguideCoplanar.get_length(waveguide2, self.layout.layer(self.la))
        meander3_inst.change_pcell_parameter("length", segment_length_target_pr[0] - waveguide_length)

        # Last bit of the Purcell filter of shaping resonator
        waveguide_length = cross1_refpoints_rel["base"].distance(cross1_refpoints_rel["port_bottom"])
        wg6_end = port_abs_cross3["port_bottom"] + pya.DVector(0, -(segment_length_target_pr[1] - waveguide_length))
        waveguide6 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                port_abs_cross3["port_bottom"],
                wg6_end
            ], 1),
            "r": self.r,
            "term2": (40 if self.tunable else 0)
        })
        self.insert_cell(waveguide6)

        # Purcell resonator SQUID
        if (self.tunable):
            # SQUID refpoint at the ground plane edge
            squid_cell = Element.create_cell_from_shape(self.layout, "QCD1")
            transf = pya.DTrans(0, False, wg6_end + pya.DVector(0, -40))
            self.insert_cell(squid_cell, transf)

            waveguide_restune = WaveguideCoplanar.create_cell(self.layout, {
                "path": pya.DPath([
                    wg6_end + pya.DVector(-20, -40 - 15),
                    wg6_end + pya.DVector(+20 + self.r, -40 - 15),
                    pya.DPoint((wg6_end + pya.DVector(+20 + self.r, -40 - 15)).x, (launchers["SE"][0]).y + self.r),
                    launchers["SE"][0] + pya.DVector(0, self.r),
                    launchers["SE"][0] + pya.DVector(0, 0),
                ], 1),
                "r": self.r
            })
            self.insert_cell(waveguide_restune)

        # Capacitor Kappa
        capk = produce_library_capacitor(self.layout, caps_fingers[1], caps_length[1], caps_type[1])
        port_rel_capk = self.get_refpoints(capk, pya.DTrans(3, False, 0, 0))
        capk_inst, port_abs_capk = self.insert_cell(capk, pya.DTrans(3, False,
                                                                     meander3_end + pya.DVector(self.r, -400 - self.r) -
                                                                     port_rel_capk["port_a"]))

        # Output port of the purcell resonator
        waveguide3 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                port_abs_capk["port_b"],
                port_abs_capk["port_b"] + pya.DVector(0, -self.r),
                pya.DPoint((port_abs_capk["port_b"] + pya.DVector(0, -self.r)).x, (launchers["ES"][0]).y),
                launchers["ES"][0] + pya.DVector(-self.r, 0),
                launchers["ES"][0] + pya.DVector(0, 0),
            ], 1),
            "r": self.r
        })
        self.insert_cell(waveguide3)
        waveguide_length = 0

        # Capacitor for the driveline
        capi = produce_library_capacitor(self.layout, caps_fingers[2], caps_length[2], caps_type[2])
        port_rel_capi = self.get_refpoints(capi, pya.DTrans(3, False, 0, 0))
        capi_inst, port_abs_capi = self.insert_cell(
            capi, pya.DTrans(3, False, cross1_refpoints_abs["port_left"] - port_rel_capi["port_a"]))

        # Driveline of the shaping resonator
        waveguide4 = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                port_abs_capi["port_b"],
                port_abs_capi["port_b"] + pya.DVector(0, -self.r),
                pya.DPoint(launchers["SW"][0].x, (port_abs_capi["port_b"] + pya.DVector(0, -self.r)).y),
                launchers["SW"][0] + pya.DVector(0, self.r),
                launchers["SW"][0] + pya.DVector(0, 0),
            ], 1),
            "r": self.r
        })
        self.insert_cell(waveguide4)

        # chip frame and possibly ground plane grid
        super().produce_impl()
