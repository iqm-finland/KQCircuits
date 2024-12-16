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
from kqcircuits.util.geometry_helper import force_rounded_corners


def test_conserve_narrow_rectangle():
    w, h, r, n = 1000, 10000, 5000, 100
    region = pya.Region(pya.Box(-w, -h, w, h))
    assert abs(force_rounded_corners(region, r, 0, n).area() - region.area()) < 100  # inner rounding
    assert abs(force_rounded_corners(region, 0, r, n).area() - 39141292) < 100  # outer rounding


def test_half_sphere():
    w, r, n = 20000, 5000, 100
    region = pya.Region(pya.Box(-w, -w, w, w)).rounded_corners(w, w, n) - pya.Region(pya.Box(0, -w, w, w))
    assert abs(force_rounded_corners(region, r, 0, n).area() - region.area()) < 100  # inner rounding
    assert abs(force_rounded_corners(region, 0, r, n).area() - 611108787) < 100  # outer rounding


def test_half_sphere_hole():
    d, w, r, n = 30000, 20000, 5000, 100
    hole = pya.Region(pya.Box(-w, -w, w, w)).rounded_corners(w, w, n) - pya.Region(pya.Box(0, -w, w, w))
    region = pya.Region(pya.Box(-d, -d, d, d)) - hole
    assert abs(force_rounded_corners(region, r, 0, n).area() - 2988891213) < 100  # inner rounding
    assert abs(force_rounded_corners(region, 0, r, n).area() - 2950038234) < 100  # outer rounding


def test_boat_shape():
    w, d, r, n = 20000, 10000, 5000, 100
    region = pya.Region(pya.Box(-w - d, -w, w - d, w)).rounded_corners(w, w, n) & pya.Region(
        pya.Box(-w + d, -w, w + d, w)
    ).rounded_corners(w, w, n)
    assert abs(force_rounded_corners(region, r, 0, n).area() - region.area()) < 100  # inner rounding
    assert abs(force_rounded_corners(region, 0, r, n).area() - 486053824) < 100  # outer rounding
