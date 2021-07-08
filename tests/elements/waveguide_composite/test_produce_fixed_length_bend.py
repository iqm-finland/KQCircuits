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


from kqcircuits.chips.chip import Chip
from kqcircuits.defaults import default_layers
from kqcircuits.elements.waveguide_composite import produce_fixed_length_bend
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import get_cell_path_length

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
    actual_length = get_cell_path_length(inst.cell, layout.layer(default_layers["waveguide_length"]))
    return abs(actual_length - target_len) / target_len
