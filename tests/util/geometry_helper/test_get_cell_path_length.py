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


import math

from kqcircuits.defaults import default_layers
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import get_cell_path_length

relative_length_tolerance = 2e-4


def test_get_length_simple_path():
    layout = pya.Layout()
    path_layer = layout.layer(default_layers["1t1_waveguide_path"])
    cell = layout.create_cell("test")
    shape = pya.DPath(
        [
            pya.DPoint(0, 0),
            pya.DPoint(300, 0),
            pya.DPoint(300, 100),
        ],
        0,
    )
    cell.shapes(path_layer).insert(shape)
    length = 300 + 100
    assert abs(get_cell_path_length(cell) - length) / length < relative_length_tolerance


def test_get_length_simple_waveguide():
    layout = pya.Layout()
    r = 50
    cell = WaveguideCoplanar.create(
        layout,
        path=pya.DPath(
            [
                pya.DPoint(0, 0),
                pya.DPoint(0, 250),
                pya.DPoint(200, 250),
            ],
            0,
        ),
        r=r,
    )
    length = 250 + 200 - 2 * r + math.pi * r / 2
    assert abs(get_cell_path_length(cell) - length) / length < relative_length_tolerance
