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

from kqcircuits.elements.element import insert_cell_into
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_dc import FlipChipConnectorDc
from kqcircuits.pya_resolver import pya
from kqcircuits.util.instance_hierarchy_helpers import get_cell_instance_hierarchy


@pytest.fixture
def layout_with_cell_hierarchy():
    """Generates a KLayoutView with a hierarchy of three static cell instances with transformations::

              top_cell
              /      \
          cell_1    cell_3
             |
          cell_2

    Here, ``cell_1`` and ``cell_2`` have simple transformations (translation only), and ``cell_3`` has a complex
    transformation (transformation and rotation by 30 degrees).

    Returns: ``view, [top_cell, cell_1, cell_2, cell_3]``, where the latter are ``pya.Cell`` objects.
    """
    layout = pya.Layout()
    top_cell = layout.create_cell("Top Cell")
    cell_1 = layout.create_cell("cell_1")
    cell_2 = layout.create_cell("cell_2")
    cell_3 = layout.create_cell("cell_3")
    cell_4 = layout.create_cell("cell_4")

    # Simply translated cell
    insert_cell_into(top_cell, cell_1, trans=pya.DTrans(200.0, 300.0), inst_name="cell_1_instance")

    # Nested cells
    insert_cell_into(cell_1, cell_2, trans=pya.DTrans(50.0, 60.0), inst_name="cell_2_instance")
    insert_cell_into(cell_2, cell_4, trans=pya.DTrans(100.0, 12.0), inst_name="cell_4_instance")

    # Complex translated cell
    insert_cell_into(top_cell, cell_3, trans=pya.DCplxTrans(1, 30, False, 100.0, 200.0), inst_name="cell_3_instance")

    return layout, [top_cell, cell_1, cell_2, cell_3, cell_4]


@pytest.mark.parametrize(
    "into_cell,transform,expected",
    [
        (0, pya.DTrans(400.0, 800.0), (400, 800)),
        (1, pya.DTrans(20.0, 30.0), (200 + 20, 300 + 30)),
        (2, pya.DTrans(1.0, 2.0), (200 + 50 + 1, 300 + 60 + 2)),
        (3, pya.DTrans(25.0, 0.0), (100.0 + 25.0 * cos(radians(30)), 200.0 + 25.0 * sin(radians(30)))),
    ],
)
def test_absolute_instance_transforms(layout_with_cell_hierarchy, into_cell, transform, expected):
    layout, cells = layout_with_cell_hierarchy

    # Create a target element and place in the cell hierarchy as given in the parametrization
    target_cell = FlipChipConnectorDc.create(layout)
    insert_cell_into(cells[into_cell], target_cell, trans=transform)

    # Get instance location
    result = get_cell_instance_hierarchy(layout, target_cell.cell_index())

    assert len(result) == 1
    result_trans = result[0].trans

    expected_x, expected_y = expected
    assert abs(result_trans.disp.x - expected_x) < 0.001
    assert abs(result_trans.disp.y - expected_y) < 0.001


@pytest.mark.parametrize(
    "index,expected_instance_name,expected_parent_instance_names,expected_top_cell_name",
    [
        (1, "cell_1_instance", [], "Top Cell"),
        (2, "cell_2_instance", ["cell_1_instance"], "Top Cell"),
        (3, "cell_3_instance", [], "Top Cell"),
        (4, "cell_4_instance", ["cell_2_instance", "cell_1_instance"], "Top Cell"),
    ],
)
def test_cell_instance_hierarchy(
    layout_with_cell_hierarchy, index, expected_instance_name, expected_parent_instance_names, expected_top_cell_name
):
    layout, cells = layout_with_cell_hierarchy

    instances = get_cell_instance_hierarchy(layout, cells[index].cell_index())

    assert len(instances) == 1
    result = instances[0]
    assert result.instance.property("id") == expected_instance_name
    assert [inst.property("id") for inst in result.parent_instances] == expected_parent_instance_names
    assert result.top_cell.name == expected_top_cell_name
