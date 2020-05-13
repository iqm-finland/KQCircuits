from typing import List
from kqcircuits.pya_resolver import pya
from kqcircuits.defaults import default_output_format, output_formats_dict, gzip


def export_layers(filename, layout, cells=None, layers=None, output_format=default_output_format):

    svopt = pya.SaveLayoutOptions()
    svopt.format = output_format
    svopt.write_context_info = False
    if layers is not None:
        svopt.deselect_all_layers()
        for layer in layers:
            svopt.add_layer(layout.layer(layer), layer)
    if cells is not None:
        svopt.clear_cells()
        for cell in cells:
            svopt.add_cell(cell.cell_index())

    layout.write(filename, svopt)


def find_edge_from_point(cell: pya.Cell, layer: int, point: pya.DPoint, dbu, tolerance=0.01):
    # Find closest edge to point
    edges = [edge.to_dtype(dbu)
             for polygon in cell.shapes(layer).each(pya.Shapes.SPolygons)
             for edge in polygon.each_edge()
             ]
    nearest = sorted([(edge.distance_abs(point), edge) for edge in edges])[0]
    if nearest[0] < tolerance:
        return nearest[1]
    else:
        raise ValueError("No edge found at point")


def get_enclosing_polygon(points: List[List[float]]):
    """
    Order points in such a way that they form a polygon without intersecting
    lines. The ordering is clockwise starting from the left-most point.

    Arguments:
        points: List of points [x,y]

    Returns:
        points: ordered list of points [x,y]
    """

    # Find y-coordinate of linear interpolation between p0 = [x0,y0] and
    # p1 = [x1,y1] corresponding to x
    def linearinterpy(p0,p1,x):
        """
        Find y-coordinate of linear interpolation between p0 = [x0,y0] and p1 = [x1,y1] corresponding to x

        Arguments:
            p0, p1: Points [x,y]
            x: x-coordinate to interpolate at

        Returns:
            y = y0 + (x-x0)*(dy/dx)
        """
        return p0[1] + (x-p0[0])*((p1[1]-p0[1])/(p1[0]-p0[0]))

    # Sort by x and then y, to ensure we go from lowest left-most point to
    # highest right-most point.
    points.sort()

    # Leftmost and rightmost point
    pleft = points[0]
    pright = points[-1]

    # Split remaining points into groups above and below
    # the line pleft - pright
    pabove = []
    pbelow = []
    for p in points[1:-1]:
        if p[1] > linearinterpy(pleft,pright,p[0]):
            pabove.append(p)
        else:
            pbelow.append(p)

    # Construct polygon starting from pleft and going clockwise
    # Note: we rely on the fact that pabove and pbelow are still sorted by x
    # Note: the polygon is not closed.
    pbelow.reverse()
    return [pleft] + pabove + [pright] + pbelow
