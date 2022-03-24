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


def polygon_with_hsym(points):
    """Polygon with horizontal symmetry.

    Arguments:
        points: List of points to copied to the other side of the symmetry axis. Points at the symmetry axis will
            be doubled.

    Returns:
        DPolygon
    """
    return polygon_with_sym(points, pya.DTrans.M0)


def polygon_with_vsym(points):
    """Polygon with vertical symmetry.

    Arguments:
        points: List of points to copied to the other side of the symmetry axis. Points at the symmetry axis will
            be doubled.

    Returns:
        DPolygon
    """
    return polygon_with_sym(points, pya.DTrans.M90)


def polygon_with_sym(points, mirror_trans):
    """Polygon with symmetry with respect to an axis.

    Arguments:
        points: List of points to copied to the other side of the symmetry axis. Points at the symmetry axis will
            be doubled.
        mirror_trans: pya.DTrans that mirrors the points with respect to an axis

    Returns:
        DPolygon
    """
    # mirror the points and return polygon
    antipoints = [mirror_trans * p for p in reversed(points)]

    return pya.DPolygon([*points, *antipoints])
