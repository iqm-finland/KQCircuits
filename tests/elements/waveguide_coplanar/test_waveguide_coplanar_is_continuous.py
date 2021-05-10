# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.defaults import default_layers


# maximum allowed distance between connected waveguide segments for them to be considered continuous
tolerance = 0.0015


def test_straight_continuous():

    layout = pya.Layout()
    cell = layout.create_cell("top")
    points1 = [pya.DPoint(0, 0), pya.DPoint(100, 0)]
    points2 = [pya.DPoint(100, 0), pya.DPoint(200, 0)]
    shape1 = pya.DPath(points1, 1)
    shape2 = pya.DPath(points2, 1)
    annotation_layer = layout.layer(default_layers["waveguide_length"])
    cell.shapes(annotation_layer).insert(shape1)
    cell.shapes(annotation_layer).insert(shape2)

    assert WaveguideCoplanar.is_continuous(cell, annotation_layer, tolerance)


def test_straight_not_continuous():

    layout = pya.Layout()
    cell = layout.create_cell("top")
    points1 = [pya.DPoint(0, 0), pya.DPoint(100, 0)]
    points2 = [pya.DPoint(100 + 2*tolerance, 0), pya.DPoint(200, 0)]
    shape1 = pya.DPath(points1, 1)
    shape2 = pya.DPath(points2, 1)
    annotation_layer = layout.layer(default_layers["waveguide_length"])
    cell.shapes(annotation_layer).insert(shape1)
    cell.shapes(annotation_layer).insert(shape2)

    assert not WaveguideCoplanar.is_continuous(cell, annotation_layer, tolerance)


def test_corner_continuous():

    layout = pya.Layout()
    cell = layout.create_cell("top")
    points1 = [pya.DPoint(0, 0), pya.DPoint(50, 0)]
    points2 = [pya.DPoint(50, 0), pya.DPoint(50, 50)]
    shape1 = pya.DPath(points1, 1)
    shape2 = pya.DPath(points2, 1)
    annotation_layer = layout.layer(default_layers["waveguide_length"])
    cell.shapes(annotation_layer).insert(shape1)
    cell.shapes(annotation_layer).insert(shape2)

    assert WaveguideCoplanar.is_continuous(cell, annotation_layer, tolerance)


def test_corner_not_continuous():

    layout = pya.Layout()
    cell = layout.create_cell("top")
    points1 = [pya.DPoint(0, 0), pya.DPoint(0, 50)]
    points2 = [pya.DPoint(0, 50 + 2*tolerance), pya.DPoint(50, 50)]
    shape1 = pya.DPath(points1, 1)
    shape2 = pya.DPath(points2, 1)
    annotation_layer = layout.layer(default_layers["waveguide_length"])
    cell.shapes(annotation_layer).insert(shape1)
    cell.shapes(annotation_layer).insert(shape2)

    assert not WaveguideCoplanar.is_continuous(cell, annotation_layer, tolerance)
