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
from kqcircuits.pya_resolver import pya

from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.defaults import default_layers, default_faces

# maximum allowed distance between connected waveguide segments for them to be considered continuous
continuity_tolerance = 0.003

relative_length_tolerance = 0.05


def test_too_few_points(capfd):
    layout = pya.Layout()
    WaveguideCoplanar.create(layout, path=pya.DPath([pya.DPoint(0, 0)], 1))
    _, err = capfd.readouterr()
    assert err != ""


def test_straight_doesnt_fit_between_corners(capfd):
    layout = pya.Layout()
    points = [pya.DPoint(0, 0), pya.DPoint(200, 0), pya.DPoint(200, 190), pya.DPoint(400, 190)]
    WaveguideCoplanar.create(layout, path=pya.DPath(points, 1))
    _, err = capfd.readouterr()
    assert err != ""


def test_too_short_last_segment(capfd):
    layout = pya.Layout()
    points = [pya.DPoint(0, 0), pya.DPoint(200, 0), pya.DPoint(200, 90)]
    WaveguideCoplanar.create(layout, path=pya.DPath(points, 1))
    _, err = capfd.readouterr()
    assert err != ""


def test_continuity_90degree_turn():
    layout = pya.Layout()
    points = [
        pya.DPoint(0, 0),
        pya.DPoint(0, 200),
        pya.DPoint(200, 200),
    ]
    guideline = pya.DPath(points, 5)
    waveguide_cell = WaveguideCoplanar.create(layout, path=guideline)
    assert WaveguideCoplanar.is_continuous(
        waveguide_cell, layout.layer(default_layers["1t1_waveguide_path"]), continuity_tolerance
    )


def test_continuity_many_turns():
    layout = pya.Layout()
    waveguide_cell = _create_waveguide_many_turns(layout, 20, 40, 5)
    assert WaveguideCoplanar.is_continuous(
        waveguide_cell, layout.layer(default_layers["1t1_waveguide_path"]), continuity_tolerance
    )


def test_continuity_many_turns_with_zero_length_segments():
    """This tests a waveguide with some 0-length waveguide segments, which the continuity test should ignore (see issue
    #157 and discussion in PR #147)
    """
    layout = pya.Layout()
    waveguide_cell = _create_waveguide_many_turns(layout, 30, 30, 5)
    assert WaveguideCoplanar.is_continuous(
        waveguide_cell, layout.layer(default_layers["1t1_waveguide_path"]), continuity_tolerance
    )


def _create_waveguide_many_turns(layout, n, scale1, scale2):
    """Creates a waveguide with many turns.

    This waveguide has many turns with different angles and different directions, so it gives a "random sample" of
    all possible waveguides.

    Returns:
        Cell object for the waveguide.

    """
    points = [pya.DPoint(0, 0) for i in range(4 * n)]
    for x in range(n):
        points[x] = pya.DPoint(x * scale1, scale2 * n * math.sin(x / (n / 3) * math.pi))
        points[x + n] = pya.DPoint(n * scale1 - scale2 * n * math.sin(x / (n / 3) * math.pi), -x * scale1)
        points[x + 2 * n] = pya.DPoint(
            n * scale1 - x * scale1, -scale2 * n * math.sin(x / (n / 3) * math.pi) - n * scale1
        )
        points[x + 3 * n] = pya.DPoint(scale2 * n * math.sin(x / (n / 3) * math.pi), x * scale1 - n * scale1)

    guideline = pya.DPath(points, 5)

    waveguide_cell = WaveguideCoplanar.create(
        layout,
        path=guideline,
        r=50,
    )

    return waveguide_cell


def assert_perfect_waveguide_continuity(cell, layout, expected_shapes):
    # Test waveguide continuity by counting the number of non-overlapping shapes in the etch layer.
    #
    # Args:
    #   cell: cell containing the waveguide
    #   layout: layout containing the waveguide
    #   expected_shapes: number of non-overlapping shapes expected. Should be 2 for an open-ended waveguide,
    #       and 1 for a waveguide with one or more termination.
    test_region = pya.Region(
        cell.begin_shapes_rec(layout.layer(default_faces["1t1"]["base_metal_gap_wo_grid"]))
    ).merged()
    number_of_shapes = len([x for x in test_region.each()])
    assert number_of_shapes == expected_shapes


def test_perfect_continuity_of_carefully_chosen_corner():
    layout = pya.Layout()

    waveguide_cell = WaveguideCoplanar.create(
        layout,
        path=pya.DPath([pya.DPoint(135, 240), pya.DPoint(1000, 1000), pya.DPoint(2000, 1500)], 0),
        # corner_safety_overlap=0
    )

    assert_perfect_waveguide_continuity(waveguide_cell, layout, expected_shapes=2)


def test_perfect_continuity_many_turns():
    layout = pya.Layout()
    waveguide_cell = _create_waveguide_many_turns(layout, 20, 40, 5)

    assert_perfect_waveguide_continuity(waveguide_cell, layout, expected_shapes=2)


def test_perfect_continuity_straight_segment_with_terminations():
    layout = pya.Layout()

    # Selected paths that have two or more gaps
    paths = [
        pya.DPath([pya.DPoint(1.72361230024, 3.79488885597), pya.DPoint(16.4134694657, 90.2562139227)], 0),
        pya.DPath([pya.DPoint(9.15544123457, 9.4465905822), pya.DPoint(92.4307007268, 16.2896687391)], 0),
        pya.DPath([pya.DPoint(8.29389541953, 0.850110987246), pya.DPoint(86.3376785858, 33.7693474405)], 0),
        pya.DPath([pya.DPoint(6.82375493747, 3.58929890974), pya.DPoint(30.0097566092, 36.153727762)], 0),
    ]

    for path in paths:
        layout.clear()

        waveguide_cell = WaveguideCoplanar.create(
            layout,
            path=path,
            term1=10,
            term2=10,
        )

        assert_perfect_waveguide_continuity(waveguide_cell, layout, expected_shapes=1)


def test_number_of_child_instances_with_missing_curves_1():
    layout = pya.Layout()

    points = [
        pya.DPoint(0, 0),
        pya.DPoint(100, 100),
        pya.DPoint(200, 200),  # same direction as last point, so no curve at previous point
    ]

    waveguide_cell = WaveguideCoplanar.create(layout, path=pya.DPath(points, 1))

    assert waveguide_cell.child_instances() == 2


def test_number_of_child_instances_with_missing_curves_2():
    layout = pya.Layout()

    points = [
        pya.DPoint(0, 0),
        pya.DPoint(100, 200),
        pya.DPoint(200, 400),  # same direction as last point, so no curve at previous point
        pya.DPoint(200, 900),
        pya.DPoint(500, 700),
        pya.DPoint(800, 500),  # same direction as last point, so no curve at previous point
    ]

    waveguide_cell = WaveguideCoplanar.create(layout, path=pya.DPath(points, 1))

    assert waveguide_cell.child_instances() == 7


def test_length_with_missing_curves_1():

    points = [
        pya.DPoint(0, 0),
        pya.DPoint(100, 0),
        pya.DPoint(200, 0),  # same direction as last point, so no curve at previous point
    ]

    _assert_correct_length(points, target_length=200)


def test_length_with_missing_curves_2():

    points = [
        pya.DPoint(0, 0),
        pya.DPoint(0, 200),
        pya.DPoint(0, 400),  # same direction as last point, so no curve at previous point
        pya.DPoint(200, 400),
        pya.DPoint(500, 400),
        pya.DPoint(800, 400),  # same direction as last point, so no curve at previous point
    ]

    _assert_correct_length(points, target_length=1200)


def _assert_correct_length(points, target_length):
    """Asserts that the length of a waveguide created from `points` has length close enough to `target_length`."""
    layout = pya.Layout()
    waveguide_cell = WaveguideCoplanar.create(layout, path=pya.DPath(points, 1))
    true_length = waveguide_cell.length()
    relative_error = abs(true_length - target_length) / target_length
    assert relative_error < relative_length_tolerance
