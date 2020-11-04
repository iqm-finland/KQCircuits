# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import math
from kqcircuits.pya_resolver import pya

from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.defaults import default_layers, default_faces

# maximum allowed distance between connected waveguide segments for them to be considered continuous
tolerance = 0.003


def test_continuity_90degree_turn():
    layout = pya.Layout()
    points = [
        pya.DPoint(0, 0),
        pya.DPoint(0, 200),
        pya.DPoint(200, 200),
    ]
    guideline = pya.DPath(points, 5)
    waveguide_cell = WaveguideCoplanar.create(layout,
        path=guideline
    )
    assert WaveguideCoplanar.is_continuous(waveguide_cell, layout.layer(default_layers["annotations"]), tolerance)


def test_continuity_many_turns():
    layout = pya.Layout()
    waveguide_cell = _create_waveguide_many_turns(layout, 20, 40, 5)
    assert WaveguideCoplanar.is_continuous(waveguide_cell, layout.layer(default_layers["annotations"]), tolerance)


def test_continuity_many_turns_with_zero_length_segments():
    """This tests a waveguide with some 0-length waveguide segments, which the continuity test should ignore (see issue
    #157 and discussion in PR #147)
    """
    layout = pya.Layout()
    waveguide_cell = _create_waveguide_many_turns(layout, 30, 30, 5)
    assert WaveguideCoplanar.is_continuous(waveguide_cell, layout.layer(default_layers["annotations"]), tolerance)


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
        points[x + 2 * n] = pya.DPoint(n * scale1 - x * scale1,
                                       -scale2 * n * math.sin(x / (n / 3) * math.pi) - n * scale1)
        points[x + 3 * n] = pya.DPoint(scale2 * n * math.sin(x / (n / 3) * math.pi), x * scale1 - n * scale1)

    guideline = pya.DPath(points, 5)

    waveguide_cell = WaveguideCoplanar.create(layout,
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
    test_region = pya.Region(cell.begin_shapes_rec(
            layout.layer(default_faces['b']["base metal gap wo grid"])
        )).merged()
    number_of_shapes = len([x for x in test_region.each()])
    assert(number_of_shapes == expected_shapes)


def test_perfect_continuity_of_carefully_chosen_corner():
    layout = pya.Layout()

    waveguide_cell = WaveguideCoplanar.create(layout,
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

        waveguide_cell = WaveguideCoplanar.create(layout,
            path=path,
            term1=10,
            term2=10,
        )

        assert_perfect_waveguide_continuity(waveguide_cell, layout, expected_shapes=1)
