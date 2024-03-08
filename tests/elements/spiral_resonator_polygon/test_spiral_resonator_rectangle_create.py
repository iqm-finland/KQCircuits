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


from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import get_cell_path_length

from kqcircuits.elements.spiral_resonator_polygon import SpiralResonatorPolygon, rectangular_parameters
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.defaults import default_layers


relative_length_tolerance = 1e-3
continuity_tolerance = 0.0025


def test_length_short_resonator():
    relative_error = _get_length_error(1000, 500, 400, 1000)
    assert relative_error < relative_length_tolerance


def test_length_medium_resonator():
    relative_error = _get_length_error(4000, 500, 400, 1000)
    assert relative_error < relative_length_tolerance


def test_length_long_resonator():
    relative_error = _get_length_error(8000, 500, 400, 1000)
    assert relative_error < relative_length_tolerance


def test_length_short_segment_resonator():
    relative_error = _get_length_error(2500, 150, 150, 1000)
    assert relative_error < relative_length_tolerance


def test_length_with_crossing_airbridges():
    relative_error = _get_length_error(7000, 500, 400, 1000, bridges_top=True)
    assert relative_error < relative_length_tolerance


def test_length_with_different_spacing():
    layout = pya.Layout()
    length = 4310
    spiral_resonator_cell = SpiralResonatorPolygon.create(
        layout,
        **rectangular_parameters(
            length=length,
            above_space=0,
            below_space=425,
            right_space=500,
            x_spacing=38,
            y_spacing=40,
            auto_spacing=False,
        ),
    )
    true_length = get_cell_path_length(spiral_resonator_cell)
    relative_error = abs(true_length - length) / length
    assert relative_error < relative_length_tolerance


def test_continuity_medium_resonator():
    layout = pya.Layout()
    cell = SpiralResonatorPolygon.create(
        layout,
        **rectangular_parameters(length=5000, above_space=200, below_space=600, right_space=1100, auto_spacing=False),
    )
    assert WaveguideCoplanar.is_continuous(
        cell, layout.layer(default_layers["1t1_waveguide_path"]), continuity_tolerance
    )


def test_continuity_long_resonator():
    layout = pya.Layout()
    cell = SpiralResonatorPolygon.create(
        layout, **rectangular_parameters(length=10000, above_space=200, below_space=600, right_space=1100)
    )
    assert WaveguideCoplanar.is_continuous(
        cell, layout.layer(default_layers["1t1_waveguide_path"]), continuity_tolerance
    )


def test_continuity_short_segment_resonator():
    layout = pya.Layout()
    cell = SpiralResonatorPolygon.create(
        layout,
        **rectangular_parameters(length=2500, above_space=150, below_space=150, right_space=1000, auto_spacing=False),
    )
    assert WaveguideCoplanar.is_continuous(
        cell, layout.layer(default_layers["1t1_waveguide_path"]), continuity_tolerance
    )


def _get_length_error(length, above_space, below_space, right_space, bridges_top=False):
    """Returns the relative error of the spiral resonator length with the given parameters."""
    layout = pya.Layout()
    spiral_resonator_cell = SpiralResonatorPolygon.create(
        layout,
        **rectangular_parameters(
            length=length,
            above_space=above_space,
            below_space=below_space,
            right_space=right_space,
            bridges_top=bridges_top,
            auto_spacing=False,
        ),
    )
    true_length = get_cell_path_length(spiral_resonator_cell)
    relative_error = abs(true_length - length) / length
    return relative_error
