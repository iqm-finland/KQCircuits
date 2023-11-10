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

import logging

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.chips.chip import Chip
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node


class SampleHolderTest(Chip):
    """
    The PCell declaration for a SampleHolderTest chip.

    SampleHolderTest has parametrized launcher configuration (launcher dimensions and number of launchers).
    The launchers are connected pairwise by coplanar waveguides.
    """
    n_launchers = Param(pdt.TypeInt, "Number of launchers", 40, unit="")
    launcher_pitch = Param(pdt.TypeDouble, "Launcher pitch", 635, unit="μm")
    launcher_width = Param(pdt.TypeDouble, "Launcher width", 160, unit="μm")
    launcher_gap = Param(pdt.TypeDouble, "Launcher gap", 96, unit="μm")
    launcher_indent = Param(pdt.TypeDouble, "Launcher indent from edge", 520, unit="μm")

    def build(self):
        nr_pads_per_side = int(self.n_launchers / 4.)

        # North edge
        launcher_assigments = {i: f"PL-{i}-IN" for i in range(1, nr_pads_per_side + 1)}
        # East edge
        launcher_assigments.update({pin: f"PL-{pl+1}-OUT" for pl, pin in
                                    enumerate(range(2 * nr_pads_per_side, nr_pads_per_side, -1))})
        # South edge
        launcher_assigments.update({pin: f"PL-{pl + nr_pads_per_side + 1}-OUT" for pl, pin in
                                    enumerate(range(2 * nr_pads_per_side + 1, 3 * nr_pads_per_side + 1))})
        # West edge
        launcher_assigments.update({pin: f"PL-{pl + nr_pads_per_side + 1}-IN" for pl, pin in
                                    enumerate(range(4 * nr_pads_per_side, 3 * nr_pads_per_side, -1))})

        self.produce_n_launchers(self.n_launchers, "RF", self.launcher_width, self.launcher_gap, self.launcher_indent,
                                 self.launcher_pitch, launcher_assignments=launcher_assigments)

        def _produce_waveguide(i, straight_distance, first_port, second_port):
            cell = self.add_element(WaveguideComposite, nodes=[
                Node(self.refpoints[f'PL-{i}-{first_port}_port']),
                Node(self.refpoints[f'PL-{i}-{first_port}_port_corner'] + pya.DVector(0, straight_distance)),
                Node(self.refpoints[f'PL-{i}-{second_port}_port_corner'] + pya.DVector(straight_distance, 0)),
                Node(self.refpoints[f'PL-{i}-{second_port}_port']),
            ])
            self.insert_cell(cell)

            logging.info(f"{self.name_chip}: Waveguide PL-{i} length: {cell.length()}")

        for i in range(1, nr_pads_per_side + 1):
            _produce_waveguide(i, -1200, first_port="IN", second_port="OUT")

        for i in range(nr_pads_per_side + 1, nr_pads_per_side * 2 + 1):
            _produce_waveguide(i, 1200, first_port="OUT", second_port="IN")
