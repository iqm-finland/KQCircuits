# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.chips.chip import Chip
from kqcircuits.defaults import default_layers
from kqcircuits.elements.waveguide_coplanar_bridged import WaveguideCoplanarBridged, produce_fixed_length_bend
from kqcircuits.pya_resolver import pya

DPoint = pya.DPoint

relative_length_tolerance = 1e-4


def test_short_bend_without_bridge():
    relative_error = _relative_length_error(320, pya.DPoint(0, 0), pya.DPoint(0, 100), pya.DPoint(250, 120),
                                            pya.DPoint(150, 120), "no")
    assert relative_error < relative_length_tolerance


def test_short_bend_with_bridge():
    relative_error = _relative_length_error(320, pya.DPoint(0, 0), pya.DPoint(0, 100), pya.DPoint(250, 120),
                                            pya.DPoint(150, 120), "middle")
    assert relative_error < relative_length_tolerance


def test_long_bend_without_bridge():
    relative_error = _relative_length_error(1200, pya.DPoint(0, 0), pya.DPoint(100, 0), pya.DPoint(400, 1000),
                                            pya.DPoint(400, 900), "no")
    assert relative_error < relative_length_tolerance


def test_long_bend_with_bridge():
    relative_error = _relative_length_error(1500, pya.DPoint(0, 0), pya.DPoint(100, 0), pya.DPoint(400, 1000),
                                            pya.DPoint(400, 900), "middle")
    assert relative_error < relative_length_tolerance


def _relative_length_error(target_len, point_a, point_a_corner, point_b, point_b_corner, bridges):

    layout = pya.Layout()
    chip_cell = layout.create_cell("chip")
    chip = Chip()
    chip.layout = layout
    chip.cell = chip_cell
    chip.r = 100

    inst = produce_fixed_length_bend(chip, target_len, point_a, point_a_corner, point_b,
                                                              point_b_corner, bridges)
    actual_length = WaveguideCoplanarBridged.get_length(inst.cell, layout.layer(default_layers["annotations"]))
    return abs(actual_length - target_len) / target_len
