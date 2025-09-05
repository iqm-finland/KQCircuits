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

import pytest

from kqcircuits.elements.element import insert_cell_into
from kqcircuits.pya_resolver import pya


@pytest.fixture
def layout_with_cell_hierarchy():
    """Generates a KLayoutView with a hierarchy of three static cell instances with transformations::

              top_cell
              /      \
          cell_1    cell_3
             |         |
          cell_2    cell_5
             |
          cell_4

    Here, ``cell_1`` and ``cell_2`` have simple transformations (translation only), and ``cell_3`` has a complex
    transformation (transformation and rotation by 30 degrees).

    Returns: ``view, [top_cell, cell_1, cell_2, cell_3, cell_4, cell_5]``, where the latter are ``pya.Cell`` objects.
    """
    layout = pya.Layout()
    top_cell = layout.create_cell("Top Cell")
    cell_1 = layout.create_cell("cell_1")
    cell_2 = layout.create_cell("cell_2")
    cell_3 = layout.create_cell("cell_3")
    cell_4 = layout.create_cell("cell_4")
    cell_5 = layout.create_cell("cell_5")

    # Simply translated cell
    insert_cell_into(top_cell, cell_1, trans=pya.DTrans(200.0, 300.0), inst_name="cell_1_instance")

    # Nested cells
    insert_cell_into(cell_1, cell_2, trans=pya.DTrans(50.0, 60.0), inst_name="cell_2_instance")
    insert_cell_into(cell_2, cell_4, trans=pya.DTrans(100.0, 12.0), inst_name="cell_4_instance")

    # Complex translated cell
    insert_cell_into(top_cell, cell_3, trans=pya.DCplxTrans(1, 30, False, 100.0, 200.0), inst_name="cell_3_instance")
    insert_cell_into(cell_3, cell_5, trans=pya.DTrans(0, False, -700.0, -900.0), inst_name="cell_5_instance")

    return layout, [top_cell, cell_1, cell_2, cell_3, cell_4, cell_5]
