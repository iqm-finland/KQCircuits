# This code is part of KQCircuits
# Copyright (C) 2026 IQM Finland Oy
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

import pytest

from kqcircuits.defaults import default_faces
from kqcircuits.pya_resolver import pya
from kqcircuits.util import instance_hierarchy_helpers


def test_get_instance_marker_polygons_applies_recursive_and_instance_transforms():
    """Marker polygons are returned in top-cell coordinates for recursively nested shapes."""
    assert hasattr(instance_hierarchy_helpers, "get_instance_marker_polygons")

    layout = pya.Layout()
    top_cell = layout.create_cell("top_cell")
    selected_cell = layout.create_cell("selected_cell")
    nested_cell = layout.create_cell("nested_cell")
    marker_layer = layout.layer(default_faces["1t1"]["ground_grid_avoidance"])

    nested_cell.shapes(marker_layer).insert(pya.DBox(0, 0, 10, 20))
    selected_cell.insert(pya.DCellInstArray(nested_cell.cell_index(), pya.DCplxTrans(1, 90, False, 5, 0)))
    selected_inst = top_cell.insert(
        pya.DCellInstArray(selected_cell.cell_index(), pya.DCplxTrans(1, 0, False, 100, 200))
    )

    polygons = instance_hierarchy_helpers.get_instance_marker_polygons(layout, selected_inst)

    assert len(polygons) == 1
    marker_box = polygons[0].bbox()
    assert marker_box.left == pytest.approx(85)
    assert marker_box.right == pytest.approx(105)
    assert marker_box.bottom == pytest.approx(200)
    assert marker_box.top == pytest.approx(210)
