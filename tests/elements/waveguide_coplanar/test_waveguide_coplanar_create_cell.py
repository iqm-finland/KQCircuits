import math
from kqcircuits.pya_resolver import pya

from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.defaults import default_layers


# maximum allowed distance between connected waveguide segments for them to be considered continuous
tolerance = 0.0015


def test_continuity_90degree_turn():
    layout = pya.Layout()
    points = [
        pya.DPoint(0, 0),
        pya.DPoint(0, 200),
        pya.DPoint(200, 200),
    ]
    guideline = pya.DPath(points, 5)
    waveguide_cell = WaveguideCoplanar.create_cell(layout, {
        "path": guideline
    })
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

    waveguide_cell = WaveguideCoplanar.create_cell(layout, {
        "path": guideline,
        "r": 50,
    })

    return waveguide_cell
