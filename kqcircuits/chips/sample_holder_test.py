# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
from autologging import logged

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt

from kqcircuits.chips.chip import Chip
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
version = 1


@logged
class SampleHolderTest(Chip):
    """
    The PCell declaration for a SampleHolderTest chip.

    SampleHolderTest has parametrized launcher configuration (launcher dimensions and number of launchers).
    The launchers are connected pairwise by coplanar waveguides.
    """
    n_launchers = Param(pdt.TypeInt, "Number of launchers", 40, unit="")
    launcher_pitch = Param(pdt.TypeDouble, "Launcher pitch", 635, unit="[μm]")
    launcher_width = Param(pdt.TypeDouble, "Launcher width", 160, unit="[μm]")
    launcher_indent = Param(pdt.TypeDouble, "Launcher indent from edge", 520, unit="[μm]")

    def produce_impl(self):
        launcher_assignments = {}
        launchers = self.produce_n_launchers(self.n_launchers, "RF", self.launcher_width, self.launcher_indent,
                                             launcher_assignments, self.launcher_pitch)

        nr_pads_per_side = int(self.n_launchers / 4.)

        def _produce_waveguide(i, j, straight_distance):
            cell = self.add_element(WaveguideComposite, nodes=[
                Node(self.refpoints[f'{i}_port']),
                Node(self.refpoints[f'{i}_port_corner'] + pya.DVector(0, straight_distance)),
                Node(self.refpoints[f'{j}_port_corner'] + pya.DVector(straight_distance, 0)),
                Node(self.refpoints[f'{j}_port']),
            ], a=self.a, b=self.b, r=self.r, n=self.n)
            self.insert_cell(cell)

            self.__log.info("%s: Waveguide %d-%d length: %s", self.name_chip, i, j, cell.length())

        for i, j in zip(range(1, nr_pads_per_side + 1),
                        range(2 * nr_pads_per_side, nr_pads_per_side, -1)):
            _produce_waveguide(i, j, -1200)

        for i, j in zip(range(2 * nr_pads_per_side + 1, 3 * nr_pads_per_side + 1),
                        range(4 * nr_pads_per_side, 3 * nr_pads_per_side, -1)):
            _produce_waveguide(i, j, 1200)

        super().produce_impl()
