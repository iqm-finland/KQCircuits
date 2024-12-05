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


from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt


class WaveguideCoplanarStraight(Element):
    """The PCell declaration of a straight segment of a coplanar waveguide.

    .. MARKERS_FOR_PNG 15,8 15,0
    """

    l = Param(pdt.TypeDouble, "Length", 30)
    add_metal = Param(pdt.TypeBoolean, "Add trace in base metal addition too", False)
    ground_grid_in_trace = Param(pdt.TypeBoolean, "Add ground grid also to the waveguide", False)

    @staticmethod
    def build_geometry(element, trans, l):
        # Refpoint in the first end
        # Left gap
        pts_1 = [
            pya.DPoint(0, element.a / 2 + 0),
            pya.DPoint(l, element.a / 2 + 0),
            pya.DPoint(l, element.a / 2 + element.b),
            pya.DPoint(0, element.a / 2 + element.b),
        ]
        shape_1 = pya.DPolygon(pts_1)
        element.cell.shapes(element.get_layer("base_metal_gap_wo_grid")).insert(trans * shape_1)

        # Right gap
        pts_2 = [
            pya.DPoint(l, -element.a / 2 + 0),
            pya.DPoint(0, -element.a / 2 + 0),
            pya.DPoint(0, -element.a / 2 - element.b),
            pya.DPoint(l, -element.a / 2 - element.b),
        ]
        shape_2 = pya.DPolygon(pts_2)
        element.cell.shapes(element.get_layer("base_metal_gap_wo_grid")).insert(trans * shape_2)

        # Protection layer
        if element.ground_grid_in_trace:
            element.add_protection(trans * shape_1.sized(1))
            element.add_protection(trans * shape_2.sized(1))
        else:
            w = element.a / 2 + element.b + element.margin
            pts = [pya.DPoint(0, -w), pya.DPoint(l, -w), pya.DPoint(l, w), pya.DPoint(0, w)]
            element.add_protection(trans * pya.DPolygon(pts))

        # Waveguide path and base_metal_addition
        path = pya.DPath([pya.DPoint(0, 0), pya.DPoint(l, 0)], 0)
        shape = pya.DPolygon(pts_1[:2] + pts_2[:2])
        WaveguideCoplanarStraight.add_waveguide_path(element, trans * path, trans * shape)

    @staticmethod
    def add_waveguide_path(element, path: pya.DPath, shape: pya.DPolygon):
        """Inserts the path and the shape to 'waveguide_path' layer. If element.add_metal is True, inserts the shape to
        'base_metal_addition' layer.

        Prefer this function to add path on a waveguide trace.

        The path is used only for computing waveguide length and the path width should be zero to not mess up the shapes
        in 'waveguide_path' layer.

        Args:
            element: An instance of a waveguide coplanar class.
            path: The path along the centerline of the waveguide with zero width.
            shape: The shape of the waveguide trace.
        """
        element.cell.shapes(element.get_layer("waveguide_path")).insert(path)
        element.cell.shapes(element.get_layer("waveguide_path")).insert(shape)
        if element.add_metal:
            element.cell.shapes(element.get_layer("base_metal_addition")).insert(shape)

    def build(self):
        WaveguideCoplanarStraight.build_geometry(self, pya.DTrans(), self.l)
