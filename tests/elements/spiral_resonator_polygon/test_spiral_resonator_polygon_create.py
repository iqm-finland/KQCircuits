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

from kqcircuits.elements.spiral_resonator_polygon import SpiralResonatorPolygon
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.defaults import default_layers


relative_length_tolerance = 1e-3
continuity_tolerance = 0.0015


def test_length_straight_last_segment():
    relative_error = _get_length_error(
        length=6000,
        input_path=pya.DPath([pya.DPoint(-200, 0), pya.DPoint(0, 0)], 0),
        poly_path=pya.DPath([pya.DPoint(0, 1000), pya.DPoint(2000, 0), pya.DPoint(0, -1000)], 0),
        auto_spacing=False,
        manual_spacing=300,
    )
    assert relative_error < relative_length_tolerance


def test_length_curved_last_segment():
    relative_error = _get_length_error(
        length=5000,
        input_path=pya.DPath([pya.DPoint(-200, 0), pya.DPoint(0, 0)], 0),
        poly_path=pya.DPath([pya.DPoint(0, 1000), pya.DPoint(2000, 0), pya.DPoint(0, -1000)], 0),
        auto_spacing=False,
        manual_spacing=300,
    )
    assert relative_error < relative_length_tolerance


def test_length_empty_input_path():
    relative_error = _get_length_error(
        length=4026,
        input_path=pya.DPath([], 0),
        poly_path=pya.DPath([pya.DPoint(0, 0), pya.DPoint(1800, 0), pya.DPoint(1800, -500), pya.DPoint(0, -500)], 0),
    )
    assert relative_error < relative_length_tolerance


def test_length_quadrilateral():
    relative_error = _get_length_error(
        length=5700,
        poly_path=pya.DPath([pya.DPoint(0, 800), pya.DPoint(1000, 0), pya.DPoint(1000, -800), pya.DPoint(0, -800)], 0),
    )
    assert relative_error < relative_length_tolerance


def test_length_pentagon():
    relative_error = _get_length_error(
        length=6200,
        poly_path=pya.DPath(
            [pya.DPoint(0, 400), pya.DPoint(700, 700), pya.DPoint(1200, 0), pya.DPoint(700, -700), pya.DPoint(0, -400)],
            0,
        ),
    )
    assert relative_error < relative_length_tolerance


def test_length_manual_spacing():
    relative_error = _get_length_error(length=4200, auto_spacing=False, manual_spacing=150)
    assert relative_error < relative_length_tolerance


def test_length_automatic_spacing():
    relative_error = _get_length_error(length=4200, auto_spacing=True)
    assert relative_error < relative_length_tolerance


def test_length_with_bridges():
    relative_error = _get_length_error(length=5300, bridge_spacing=300)
    assert relative_error < relative_length_tolerance


def test_length_without_bridges():
    relative_error = _get_length_error(length=5300, bridge_spacing=0)
    assert relative_error < relative_length_tolerance


def test_length_only_input_path():
    relative_error = _get_length_error(
        length=6000,
        input_path=pya.DPath(
            [
                pya.DPoint(0, 0),
                pya.DPoint(0, 1000),
                pya.DPoint(1000, 1000),
                pya.DPoint(1000, -1000),
                pya.DPoint(200, -1000),
                pya.DPoint(200, 800),
                pya.DPoint(800, 800),
                pya.DPoint(800, -800),
                pya.DPoint(400, -800),
                pya.DPoint(400, 600),
            ],
            0,
        ),
        poly_path=pya.DPath([], 0),
        auto_spacing=False,
        manual_spacing=300,
    )
    assert relative_error < relative_length_tolerance


def test_length_very_short_resonator():
    relative_error = _get_length_error(
        length=100,
        auto_spacing=False,
        manual_spacing=150,
        input_path=pya.DPath([pya.DPoint(0, 0)], 10),
        poly_path=pya.DPath([pya.DPoint(1000, 0), pya.DPoint(800, 350), pya.DPoint(-200, 350), pya.DPoint(0, 0)], 10),
    )
    assert relative_error < relative_length_tolerance


def test_length_resonator_with_consecutive_curves():
    relative_error = _get_length_error(
        length=3000,
        auto_spacing=False,
        manual_spacing=150,
        input_path=pya.DPath([pya.DPoint(0, 0)], 10),
        poly_path=pya.DPath([pya.DPoint(1000, 0), pya.DPoint(800, 350), pya.DPoint(-200, 350), pya.DPoint(0, 0)], 10),
    )
    assert relative_error < relative_length_tolerance


def test_length_too_long_resonator(capfd):
    relative_error = _get_length_error(
        length=3200,
        auto_spacing=False,
        manual_spacing=150,
        input_path=pya.DPath([pya.DPoint(0, 0)], 10),
        poly_path=pya.DPath([pya.DPoint(1000, 0), pya.DPoint(800, 351), pya.DPoint(-200, 351), pya.DPoint(0, 0)], 10),
    )
    # the resonator should either have small relative error or fail
    _, err = capfd.readouterr()
    assert relative_error < relative_length_tolerance or err != ""


def test_continuity_straight_last_segment():
    layout = pya.Layout()
    cell = SpiralResonatorPolygon.create(
        layout,
        length=4000,
        input_path=pya.DPath([pya.DPoint(-200, 0), pya.DPoint(0, 0)], 0),
        poly_path=pya.DPath([pya.DPoint(0, -800), pya.DPoint(1400, 0), pya.DPoint(0, 400)], 0),
        auto_spacing=False,
        manual_spacing=300,
    )
    assert WaveguideCoplanar.is_continuous(
        cell, layout.layer(default_layers["1t1_waveguide_path"]), continuity_tolerance
    )


def test_continuity_curved_last_segment():
    layout = pya.Layout()
    cell = SpiralResonatorPolygon.create(
        layout,
        length=3870,
        input_path=pya.DPath([pya.DPoint(-200, 0), pya.DPoint(0, 0)], 0),
        poly_path=pya.DPath([pya.DPoint(0, -800), pya.DPoint(1400, 0), pya.DPoint(0, 400)], 0),
        auto_spacing=False,
        manual_spacing=300,
    )
    assert WaveguideCoplanar.is_continuous(
        cell, layout.layer(default_layers["1t1_waveguide_path"]), continuity_tolerance
    )


def test_can_create_resonator_with_short_segment(capfd):
    layout = pya.Layout()
    SpiralResonatorPolygon.create(
        layout,
        length=5000,
        input_path=pya.DPath([pya.DPoint(-200, 0), pya.DPoint(0, 0)], 0),
        poly_path=pya.DPath([pya.DPoint(0, 800), pya.DPoint(1000, 0), pya.DPoint(1000, -250), pya.DPoint(0, -800)], 0),
        auto_spacing=False,
        manual_spacing=100,
    )
    _, err = capfd.readouterr()
    assert err == "", err


def _get_length_error(length, **parameters):
    """Returns the relative error of the spiral resonator length with the given parameters."""
    layout = pya.Layout()
    spiral_resonator_cell = SpiralResonatorPolygon.create(layout, length=length, **parameters)
    true_length = get_cell_path_length(spiral_resonator_cell)
    relative_error = abs(true_length - length) / length
    return relative_error
