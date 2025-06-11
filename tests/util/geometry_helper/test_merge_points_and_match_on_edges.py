# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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
from kqcircuits.util.geometry_helper import merge_points_and_match_on_edges


def test_narrow_polygon():
    region = pya.Region(pya.Polygon([pya.Point(-1000, 0), pya.Point(0, 0), pya.Point(1000, 1)]))
    assert region.count() == 1
    merge_points_and_match_on_edges([region])
    assert region.count() == 0


def test_narrow_hole():
    region = (
        pya.Region(pya.Box(-2000, -2000, 2000, 2000))
        - pya.Region(pya.Polygon([pya.Point(-1000, 0), pya.Point(0, 0), pya.Point(1000, 1)]))
    ).merged()
    assert region.edges().count() == 7
    merge_points_and_match_on_edges([region])
    assert region.count() == 1
    assert region.edges().count() == 4


def test_polygon_with_spike():
    region = pya.Region(
        pya.Polygon([pya.Point(-1000, 0), pya.Point(0, -1000), pya.Point(0, 0), pya.Point(1000, 0), pya.Point(2000, 1)])
    )
    assert region.edges().count() == 5
    merge_points_and_match_on_edges([region])
    assert region.count() == 1
    assert region.edges().count() == 3


def test_hole_with_spike():
    region = pya.Region(pya.Box(-2000, -2000, 3000, 2000)) - pya.Region(
        pya.Polygon([pya.Point(-1000, 0), pya.Point(0, -1000), pya.Point(0, 0), pya.Point(1000, 0), pya.Point(2000, 1)])
    )
    assert region.edges().count() == 9
    merge_points_and_match_on_edges([region])
    assert region.count() == 1
    assert region.edges().count() == 7


def test_touching_polygons():
    region = (pya.Region(pya.Box(-1000, -1000, 0, 0)) + pya.Region(pya.Box(0, 0, 1000, 1000))).merged()
    assert region.count() == 1
    merge_points_and_match_on_edges([region])
    assert region.count() == 2


def test_touching_holes():
    region = (
        pya.Region(pya.Box(-2000, -3000, 2000, 3000))
        - pya.Region(pya.Polygon([pya.Point(0, 1), pya.Point(-1000, 2000), pya.Point(1000, 2000)]))
        - pya.Region(pya.Polygon([pya.Point(0, 0), pya.Point(1000, -2000), pya.Point(-1000, -2000)]))
    )
    assert region.area() == 20001000
    merge_points_and_match_on_edges([region])
    assert region.count() == 1
    assert region.area() == 20000000


def test_close_polygons():
    region = (pya.Region(pya.Box(-1000, -1000, 0, 1000)) + pya.Region(pya.Box(1, -1000, 1000, 1000))).merged()
    assert region.count() == 2
    merge_points_and_match_on_edges([region])
    assert region.count() == 1
    assert region.area() == 4000000


def test_close_holes():
    region = (
        pya.Region(pya.Box(-2000, -2000, 2000, 2000))
        - pya.Region(pya.Box(-1000, -1000, 0, 1000))
        - pya.Region(pya.Box(1, -1000, 1000, 1000))
    )
    assert region.edges().count() == 12
    merge_points_and_match_on_edges([region])
    assert region.count() == 1
    assert region.edges().count() == 8
    assert region.area() == 12000000


def test_polygon_close_hole_edge():
    region = (
        pya.Region(pya.Box(-2000, -2000, 2000, 2000))
        - pya.Region(pya.Box(-1000, -1000, 1000, 1000))
        + pya.Region(pya.Box(-500, -0, 500, 999))
    )
    assert region.count() == 2
    merge_points_and_match_on_edges([region])
    assert region.count() == 1
    assert region.edges().count() == 12


def test_thin_hole_wall():
    region = pya.Region(pya.Box(-1000, -1000, 1000, 1000)) - pya.Region(pya.Box(0, 0, 999, 999))
    assert region.edges().count() == 8
    merge_points_and_match_on_edges([region])
    assert region.count() == 1
    assert region.edges().count() == 6


def test_close_polygon_grid():
    region = pya.Region()
    for x in range(3):
        for y in range(3):
            region += pya.Region(pya.Box(1000 * x, 1000 * y, 1000 * x + 999, 1000 * y + 999))
    assert region.count() == 9
    merge_points_and_match_on_edges([region])
    assert region.count() == 1
    assert region.edges().count() == 4
    assert region.area() == 8994001


def test_close_hole_grid():
    region = pya.Region(pya.Box(-1000, -1000, 4000, 4000))
    for x in range(3):
        for y in range(3):
            region -= pya.Region(pya.Box(1000 * x, 1000 * y, 1000 * x + 999, 1000 * y + 999))
    assert region.edges().count() == 40
    merge_points_and_match_on_edges([region])
    assert region.count() == 1
    assert region.edges().count() == 8
    assert region.area() == 16005999


def test_hole_detection():
    region = pya.Region(pya.Box(0, 0, 2000, 1000))
    region -= pya.Region(pya.Box(100, 0, 500, 500))
    region -= pya.Region(pya.Box(1000, 100, 1500, 500))
    assert region.area() == 1600000
    merge_points_and_match_on_edges([region])
    assert region.area() == 1600000
