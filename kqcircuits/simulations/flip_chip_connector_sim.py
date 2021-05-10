# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
from kqcircuits.elements.f2f_connectors.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import add_parameters_from


@add_parameters_from(FlipChipConnectorRf)
class FlipChipConnectorSim(Simulation):

    def build(self):
        fcc_cell = self.add_element(FlipChipConnectorRf, **self.get_parameters())

        transf = pya.DTrans(0, False, (self.box.left + self.box.right) / 2, (self.box.bottom + self.box.top) / 2)
        isnt, refp = self.insert_cell(fcc_cell, transf)

        self.produce_waveguide_to_port(refp["b_port"], refp["b_port_corner"], 1, 'left', face=0)
        self.produce_waveguide_to_port(refp["t_port"], refp["t_port_corner"], 2, 'right', face=1)
