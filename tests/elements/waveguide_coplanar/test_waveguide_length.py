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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

import pytest

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_curved import WaveguideCoplanarCurved


def test_presence_of_length():
    layout = pya.Layout()

    waveguide_cell = WaveguideCoplanar.create(layout, path=pya.DPath([pya.DPoint(0, 0), pya.DPoint(0, 99)], 0))
    assert hasattr(waveguide_cell, "length")
    assert waveguide_cell.length() == 99


@pytest.mark.parametrize("n, alpha", [(16, 3), (32, 1), (64, 2), (128, 0.5)])
def test_length_of_curve(n, alpha):
    layout = pya.Layout()
    waveguide_cell = WaveguideCoplanarCurved.create(layout, n=n, alpha=alpha, r=100)
    assert abs(waveguide_cell.length() - 100 * alpha) <= 0.001
