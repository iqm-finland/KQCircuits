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
from kqcircuits.elements.meander import Meander
from kqcircuits.elements.qubits.swissmon import Swissmon
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar

reload(sys.modules[Chip.__module__])

version = 1


class Demo(Chip):
    """Demonstration chip with a qubit, few waveguides and finger capacitors.
    """

    PARAMETERS_SCHEMA = {
        "freqQ1": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Frequency QB1 (GHz)",
            "default": 100
        },
        "freqRR1": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Frequency RR1 (GHz)",
            "default": 100
        }
    }

    def __init__(self):
        super().__init__()

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return ("TestChip".format())

    def produce_impl(self):
        super().produce_impl()

        launchers = self.produce_launchers_ARD24()

        # Meander demo
        meander = Meander.create_cell(self.layout, {
            "start": launchers["11"][0],
            "end": launchers["18"][0],
            "length": 8000 * 2,
            "meanders": 10
        })
        self.insert_cell(meander)

        # Swissmon
        swissmon = Swissmon.create_cell(self.layout, {
            "cpl_length": [0, 160, 0]
        })

        swissmon_refpoints_rel = self.get_refpoints(swissmon)

        swissmon_pos_v = pya.DVector(2500 - swissmon_refpoints_rel["port_drive"].y, 7500)
        swissmon_instance, swissmon_refpoints_abs = self.insert_cell(
            swissmon, pya.DCplxTrans(1, -90, False, swissmon_pos_v))

        port_qubit_dr = swissmon_refpoints_abs["port_drive"]
        port_qubit_fl = swissmon_refpoints_abs["port_flux"]
        port_qubit_ro = swissmon_refpoints_abs["port_cplr1"]

        # Driveline
        driveline = WaveguideCoplanar.create_cell(self.layout, {
            "term2": self.b,
            "path": pya.DPath([
                launchers["0"][0],
                launchers["0"][0] + pya.DVector(0, -self.r),
                port_qubit_dr + pya.DVector(0, self.r),
                port_qubit_dr
            ], 1)
        })
        self.insert_cell(driveline)

        # Fluxline
        fluxline = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                launchers["23"][0],
                launchers["23"][0] + pya.DVector(self.r, 0),
                port_qubit_fl + pya.DVector(-self.r, 0),
                port_qubit_fl
            ], 1)
        })
        self.insert_cell(fluxline)

        # Capacitor J
        capj = FingerCapacitorSquare.create_cell(self.layout, {
            "finger_number": 2
        })
        capj_inst, capj_refpoints_abs = self.insert_cell(capj, pya.DTrans(pya.DVector(5400, 7500)))

        # Capacitor kappa
        capk = FingerCapacitorSquare.create_cell(self.layout, {
            "finger_number": 8
        })
        capk_inst, capk_refpoints_abs = self.insert_cell(capk, pya.DTrans(pya.DVector(7800, 7500)))

        # Readout resonator
        readout = Meander.create_cell(self.layout, {
            "start": port_qubit_ro,
            "end": capj_refpoints_abs["port_a"],
            "length": 6000,
            "meanders": 6
        })
        self.insert_cell(readout)

        # Purcell filter
        purcell = Meander.create_cell(self.layout, {
            "start": capj_refpoints_abs["port_b"],
            "end": capk_refpoints_abs["port_a"],
            "length": 5500,
            "meanders": 6
        })
        self.insert_cell(purcell)

        # Output line
        output_line = WaveguideCoplanar.create_cell(self.layout, {
            "path": pya.DPath([
                capk_refpoints_abs["port_b"],
                capk_refpoints_abs["port_b"] + pya.DVector(self.r, 0),
                launchers["6"][0] + pya.DVector(-self.r, 0),
                launchers["6"][0] + pya.DVector(0, 0)
            ], 1)
        })
        self.insert_cell(output_line)
