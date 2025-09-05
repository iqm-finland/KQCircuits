# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
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

from math import cos, radians, sin
import pytest
from kqcircuits.klayout_view import KLayoutView
from kqcircuits.pya_resolver import pya
from kqcircuits.chips.single_xmons import SingleXmons
from kqcircuits.util.instance_hierarchy_helpers import transform_top_cell, get_cell_instance_hierarchy


@pytest.mark.parametrize(
    "transform",
    [
        pya.DTrans(),
        pya.DTrans(0, False, -1000, 0),
        pya.DTrans(0, False, 0, -1000),
        pya.DTrans(0, False, -1000, -1000),
        pya.DTrans(2, False, 1000, 2000),
        pya.DTrans(2, True, 1000, 2000),
        pya.DCplxTrans(1, 45, True, 1000, 2000),
        pya.DCplxTrans(1.5, 45, True, 1000, 2000),
        pya.DCplxTrans(0.5, 45, True, 1000, 2000),
    ],
    ids=["identity", "shift_left", "shift_down", "shift_diagonal", "rotate", "mirror", "complex", "grow", "shrink"],
)
def test_transform_top_cell_geometry_identical_to_layout_transform(transform):
    """Compare geometry of SingleXmons chip applied with ``layout.transform``
    and ``transform_top_cell`` to make sure polygons are similar enough.
    """
    view1, view2 = KLayoutView(), KLayoutView()
    view1.insert_cell(SingleXmons)
    view2.insert_cell(SingleXmons)
    view1.layout.transform(transform)
    transform_top_cell(transform, view2.layout)

    cell1 = view1.top_cell.cell_index()
    cell2 = view2.top_cell.cell_index()
    for layer in view1.layout.layer_infos():
        region1 = pya.Region(view1.layout.begin_shapes(cell1, view1.layout.find_layer(layer)))
        region2 = pya.Region(
            view2.layout.begin_shapes(
                cell2, view2.layout.find_layer([l for l in view2.layout.layer_infos() if l.name == layer.name][0])
            )
        )
        region_diff = region1 ^ region2
        # Tolerance of geometry difference is that no polygon of XOR geometry can have area of 3 µm^2 or higher
        for poly in region_diff.each():
            poly = poly.to_dtype(view1.layout.dbu)
            assert poly.area() < 3, (
                f"Applying layout.transform and transform_top_cell produced different results on SingleXmons at "
                f"layer {layer.name}. At point {poly.bbox().center()} the xor polygon has area {poly.area()}"
            )


@pytest.mark.parametrize(
    "index,expected",
    [
        (1, pya.DPoint(-1000 + 200, -2000 + 300)),
        (2, pya.DPoint(-1000 + 200 + 50, -2000 + 300 + 60)),
        (3, pya.DPoint(-1000 + 100, -2000 + 200)),
        (4, pya.DPoint(-1000 + 200 + 50 + 100, -2000 + 300 + 60 + 12)),
        (
            5,
            pya.DPoint(
                -1000 + 100 - 700.0 * cos(radians(30)) + 900.0 * sin(radians(30)),
                -2000 + 200 - 700.0 * sin(radians(30)) - 900.0 * cos(radians(30)),
            ),
        ),
    ],
)
def test_expected_transformation_displacements(layout_with_cell_hierarchy, index, expected):
    """Take a cell hierarchy construction, perform ``transform_top_cell``
    and see that child cells have expected absolute transformation displacements.
    """
    layout, cells = layout_with_cell_hierarchy
    transform_top_cell(pya.DTrans(0, False, -1000, -2000), layout)
    instances = get_cell_instance_hierarchy(layout, cells[index].cell_index())
    assert len(instances) == 1
    assert (
        instances[0].trans.disp == expected
    ), f"{cells[index].name} expected to have absolute displacement of {expected}, got {instances[0].trans.disp}"
