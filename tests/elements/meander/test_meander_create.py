# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.meander import Meander
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.defaults import default_layers


relative_length_tolerance = 1e-3
continuity_tolerance = 0.0015


def test_length_short_meander_r50():
    relative_error = _get_meander_length_error(1200, 4, 500, 50)
    assert relative_error < relative_length_tolerance


def test_length_long_meander_r50():
    relative_error = _get_meander_length_error(10000, 16, 2000, 50)
    assert relative_error < relative_length_tolerance


def test_length_long_meander_r25():
    relative_error = _get_meander_length_error(10000, 32, 2000, 25)
    assert relative_error < relative_length_tolerance


def test_length_long_meander_r100():
    relative_error = _get_meander_length_error(10000, 8, 2000, 100)
    assert relative_error < relative_length_tolerance


def test_length_min_num_meanders_r25():
    relative_error = _get_meander_length_error(1000, 2, 500, 25)
    assert relative_error < relative_length_tolerance


def test_length_min_num_meanders_r100():
    relative_error = _get_meander_length_error(1400, 2, 700, 100)
    assert relative_error < relative_length_tolerance


def test_continuity_short_meander():
    layout = pya.Layout()
    meander_cell = Meander.create(layout,
        start=pya.DPoint(0, 0),
        end=pya.DPoint(800, 0),
        length=1600,
        meanders=4,
        r=50
    )
    assert WaveguideCoplanar.is_continuous(meander_cell, layout.layer(default_layers["annotations"]),
                                           continuity_tolerance)


def test_continuity_long_meander():
    layout = pya.Layout()
    meander_cell = Meander.create(layout,
        start=pya.DPoint(0, 0),
        end=pya.DPoint(2500, 0),
        length=9000,
        meanders=15,
        r=50
    )
    assert WaveguideCoplanar.is_continuous(meander_cell, layout.layer(default_layers["annotations"]),
                                           continuity_tolerance)


def _get_meander_length_error(meander_length, num_meanders, end, r):
    """Returns the relative error of the meander length for a meander with the given parameters."""
    layout = pya.Layout()
    meander_cell = Meander.create(layout,
        start=pya.DPoint(0, 0),
        end=pya.DPoint(end, 0),
        length=meander_length,
        meanders=num_meanders,
        r=r
    )
    true_length = WaveguideCoplanar.get_length(meander_cell, layout.layer(default_layers["annotations"]))
    relative_error = abs(true_length - meander_length) / meander_length
    return relative_error
