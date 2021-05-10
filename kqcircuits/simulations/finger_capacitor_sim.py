# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.pya_resolver import pya
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.util.parameters import add_parameters_from


@add_parameters_from(FingerCapacitorSquare)
class FingerCapacitorSim(Simulation):

    def build(self):
        capacitor_cell = self.add_element(FingerCapacitorSquare, **{**self.get_parameters()})

        cap_trans = pya.DTrans(0, False, (self.box.left + self.box.right) / 2, (self.box.bottom + self.box.top) / 2)
        cap_inst, refp = self.insert_cell(capacitor_cell, cap_trans)

        self.produce_waveguide_to_port(refp["port_a"], refp["port_a_corner"], 1, 'left')
        self.produce_waveguide_to_port(refp["port_b"], refp["port_b_corner"], 2, 'right')
