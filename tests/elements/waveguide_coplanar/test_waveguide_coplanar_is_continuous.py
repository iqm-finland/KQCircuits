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
    annotation_layer = layout.layer(default_layers["1t1_waveguide_path"])
    cell.shapes(annotation_layer).insert(shape1)
    cell.shapes(annotation_layer).insert(shape2)

    assert WaveguideCoplanar.is_continuous(cell, annotation_layer, tolerance)


def test_straight_not_continuous():

    layout = pya.Layout()
    cell = layout.create_cell("top")
    points1 = [pya.DPoint(0, 0), pya.DPoint(100, 0)]
    points2 = [pya.DPoint(100 + 2 * tolerance, 0), pya.DPoint(200, 0)]
    shape1 = pya.DPath(points1, 1)
    shape2 = pya.DPath(points2, 1)
    annotation_layer = layout.layer(default_layers["1t1_waveguide_path"])
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
    annotation_layer = layout.layer(default_layers["1t1_waveguide_path"])
    cell.shapes(annotation_layer).insert(shape1)
    cell.shapes(annotation_layer).insert(shape2)

    assert WaveguideCoplanar.is_continuous(cell, annotation_layer, tolerance)


def test_corner_not_continuous():

    layout = pya.Layout()
    cell = layout.create_cell("top")
    points1 = [pya.DPoint(0, 0), pya.DPoint(0, 50)]
    points2 = [pya.DPoint(0, 50 + 2 * tolerance), pya.DPoint(50, 50)]
    shape1 = pya.DPath(points1, 1)
    shape2 = pya.DPath(points2, 1)
    annotation_layer = layout.layer(default_layers["1t1_waveguide_path"])
    cell.shapes(annotation_layer).insert(shape1)
    cell.shapes(annotation_layer).insert(shape2)

    assert not WaveguideCoplanar.is_continuous(cell, annotation_layer, tolerance)
