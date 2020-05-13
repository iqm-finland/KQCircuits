from kqcircuits.pya_resolver import pya


def polygon_with_hsym(points):
    """ Polygon with horizontal symmetry.

    Attributes:
        points: List of points to copied to the other side of the symmetry axis. Points at the symmetry axis will
            be doubled.

    Returns:
        DPolygon
    """
    # horizontal mirror the points and return polygon
    flip = pya.DTrans.M0
    antipoints = [flip * p for p in reversed(points)]

    return pya.DPolygon([*points, *antipoints])