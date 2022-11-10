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
            "junction_type": "Sim",
            "n": self.n,
        })

        # Remove unneeded elements
        self.delete_instances(chip, 'Chip Frame')
        self.delete_instances(chip, default_junction_test_pads_type, range(2))

        # Insert chip and get refpoints
        _, refpoints = self.insert_cell(chip, rec_levels=None)

        if not self.launchers:
            # Remove launchers
            self.delete_instances(chip, 'Launcher')

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
