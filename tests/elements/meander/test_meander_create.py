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


from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import get_cell_path_length

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
    assert WaveguideCoplanar.is_continuous(meander_cell, layout.layer(default_layers["waveguide_length"]),
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
    assert WaveguideCoplanar.is_continuous(meander_cell, layout.layer(default_layers["waveguide_length"]),
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
    true_length = get_cell_path_length(meander_cell, layout.layer(default_layers["waveguide_length"]))
    relative_error = abs(true_length - meander_length) / meander_length
    return relative_error
