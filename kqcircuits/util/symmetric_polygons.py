# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya


def polygon_with_hsym(points):
    """Polygon with horizontal symmetry.

    Attributes:
        points: List of points to copied to the other side of the symmetry axis. Points at the symmetry axis will
            be doubled.

    Returns:
        DPolygon
    """
    return polygon_with_sym(points, pya.DTrans.M0)


def polygon_with_vsym(points):
    """Polygon with vertical symmetry.

    Attributes:
        points: List of points to copied to the other side of the symmetry axis. Points at the symmetry axis will
            be doubled.

    Returns:
        DPolygon
    """
    return polygon_with_sym(points, pya.DTrans.M90)


def polygon_with_sym(points, mirror_trans):
    """Polygon with symmetry with respect to an axis.

    Attributes:
        points: List of points to copied to the other side of the symmetry axis. Points at the symmetry axis will
            be doubled.
        mirror_trans: pya.DTrans that mirrors the points with respect to an axis

    Returns:
        DPolygon
    """
    # mirror the points and return polygon
    antipoints = [mirror_trans * p for p in reversed(points)]

    return pya.DPolygon([*points, *antipoints])
