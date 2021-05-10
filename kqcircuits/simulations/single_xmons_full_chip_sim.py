# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
from kqcircuits.chips.single_xmons import SingleXmons
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.port import EdgePort, InternalPort
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.defaults import default_junction_test_pads_type


class SingleXmonsFullChipSim(Simulation):
    n: int
    launchers: bool
    use_test_resonators: bool

    launchers = Param(pdt.TypeBoolean, "True to include launchers in simulation", False)
    use_test_resonators = Param(pdt.TypeBoolean, "True to include XS1-type test resonators. False produces XS2", False)

    def build(self):
        mask_parameters_for_chip = {
            "name_mask": self.name,
            "name_copy": None,
            "with_grid": False,
        }

        chip = self.add_element(SingleXmons, **{
            **mask_parameters_for_chip,
            "name_chip": 'XS1' if self.use_test_resonators else 'XS2',
            "readout_res_lengths": [4490.35, 4578.13, 4668.99, 4763.09, 4860.61, 4961.75],
            "use_test_resonators": self.use_test_resonators,
            "test_res_lengths": [4884.33, 4804.94, 4728.06, 4653.58],
            "n_fingers": 4 * [4],
            "l_fingers": [23.65, 24.204, 24.7634, 25.325],
            "type_coupler": 4 * ["plate"],
            "squid_type": "SIM1",
            "n": self.n,
        })

        # Remove unneeded elements
        chip.layout().cell('Chip Frame').delete()
        chip.layout().cell(default_junction_test_pads_type).delete()
        chip.layout().cell(f'{default_junction_test_pads_type}$1').delete()

        # Insert chip and get refpoints
        cell_inst, refpoints = self.insert_cell(chip, rec_levels=None)

        if not self.launchers:
            # Remove launchers
            chip.layout().cell('Launcher').delete()

            maximum_box = pya.DBox(pya.DPoint(800, 800), pya.DPoint(9200, 9200))
            port_shift = 0
        else:
            maximum_box = pya.DBox(pya.DPoint(200, 200), pya.DPoint(9800, 9800))
            port_shift = 600

        # Limit the size of the box to fit the ports
        self.box &= maximum_box

        # Define edge ports, shifted inward by port_shift w.r.t. launcher refpoints
        for i, (launcher, shift) in enumerate(zip(
                ['NW', 'WN', 'WS', 'SW', 'SE', 'ES', 'EN', 'NE'],
                [[0, port_shift], [-port_shift, 0], [-port_shift,0], [0, -port_shift],
                 [0, -port_shift], [port_shift, 0], [port_shift, 0], [0, port_shift]])):
            self.ports.append(EdgePort(i + 1, refpoints['{}_port'.format(launcher)] + pya.DVector(*shift)))

        # Add squid internal ports
        for j in range(6):
            self.ports.append(InternalPort(j+9, *self.etched_line(refpoints['qb_{}_port_squid_a'.format(j)],
                                                                  refpoints['qb_{}_port_squid_b'.format(j)])))
