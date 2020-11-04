# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.spiral_resonator import SpiralResonator
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.defaults import default_layers


relative_length_tolerance = 1e-3
continuity_tolerance = 0.0015


def test_length_short_resonator():
    relative_error = _get_length_error(1000, 500, 400, 1000)
    assert relative_error < relative_length_tolerance


def test_length_medium_resonator():
    relative_error = _get_length_error(5000, 500, 400, 1000)
    assert relative_error < relative_length_tolerance


def test_length_long_resonator():
    relative_error = _get_length_error(10000, 500, 400, 1000)
    assert relative_error < relative_length_tolerance


def test_length_with_crossing_airbridges():
    relative_error = _get_length_error(7200, 500, 400, 800, bridges_top=True)
    assert relative_error < relative_length_tolerance


def test_length_with_different_spacing():
    layout = pya.Layout()
    length = 4310
    spiral_resonator_cell = SpiralResonator.create(layout,
        length=length,
        above_space=0,
        below_space=425,
        right_space=500,
        use_manual_spacing=True,
        manual_x_spacing=38,
        manual_y_spacing=40,
    )
    true_length = WaveguideCoplanar.get_length(spiral_resonator_cell, layout.layer(default_layers["annotations"]))
    relative_error = abs(true_length - length) / length
    assert relative_error < relative_length_tolerance


def test_continuity_medium_resonator():
    layout = pya.Layout()
    cell = SpiralResonator.create(layout,
        length=5000,
        above_space=200,
        below_space=600,
        right_space=1100,
    )
    assert WaveguideCoplanar.is_continuous(cell, layout.layer(default_layers["annotations"]),
                                           continuity_tolerance)


def test_continuity_long_resonator():
    layout = pya.Layout()
    cell = SpiralResonator.create(layout,
        length=10000,
        above_space=200,
        below_space=600,
        right_space=1100,
    )
    assert WaveguideCoplanar.is_continuous(cell, layout.layer(default_layers["annotations"]),
                                           continuity_tolerance)


def _get_length_error(length, above_space, below_space, right_space, bridges_top=False):
    """Returns the relative error of the spiral resonator length with the given parameters."""
    layout = pya.Layout()
    spiral_resonator_cell = SpiralResonator.create(layout,
        length=length,
        above_space=above_space,
        below_space=below_space,
        right_space=right_space,
        bridges_top=bridges_top,
    )
    true_length = WaveguideCoplanar.get_length(spiral_resonator_cell, layout.layer(default_layers["annotations"]))
    relative_error = abs(true_length - length) / length
    return relative_error
