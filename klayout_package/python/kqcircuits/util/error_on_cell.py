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

from kqcircuits.pya_resolver import pya
from kqcircuits.util.instance_hierarchy_helpers import formatted_cell_instance_hierarchy, get_cell_instance_hierarchy


def all_cell_parents(layout: pya.Layout, cell: pya.Cell) -> list[int]:
    """Finds all parent cell indices of a given cell, including cell itself

    Args:
        layout: The layout
        cell: The cell to find parents of

    Returns: list of cell indices of parent cells, where the first element is always ``cell`` itself.
    """
    to_do = list(cell.each_parent_cell())
    result = [cell.cell_index()]
    while len(to_do) > 0:
        c = to_do.pop(0)
        result.append(c)
        to_do.extend(layout.cell(c).each_parent_cell())
    return result


def find_cells_with_error(
    layout: pya.Layout, parent_cell_index: int | None = None
) -> list[tuple[int, str, pya.DPoint]]:
    """Find cell indices and error messages for all cells in the layout that have called the ``raise_error_on_cell``
    method.

    Args:
        layout (pya.Layout): The layout.
        parent_cell_index: if not None, return only errors where the given cell index is a parent

    Returns: List of (cell_index, error_message, error_position) tuples.
    """
    # Cells with errors have a TEXT cell instance inside them, which has the error message set as instance property.
    if parent_cell_index is not None and not layout.is_valid_cell_index(parent_cell_index):
        raise ValueError("parent_cell_index does not exist in the layout")

    result = []
    for cell in layout.each_cell():
        for inst in cell.each_inst():
            error_message = inst.property("error_on_cell")
            if error_message is not None:
                if parent_cell_index is None or parent_cell_index in all_cell_parents(layout, cell):
                    error_position = inst.property("error_on_cell_position")
                    if error_position is not None:
                        x, y = map(float, error_position.split(","))
                    else:
                        x, y = 0.0, 0.0
                    position = pya.DPoint(x, y)
                    result.append((cell.cell_index(), error_message, position))
                    continue  # No need to search any remaining instances
    return result


def formatted_errors_on_cells(layout: pya.Layout, parent_cell_index: int | None = None) -> str:
    """Generate a formatted string describing all errors raised on cells and where in the cell hierarchy these appear.

    Args:
        layout: The layout
        parent_cell_index: if not None, include only errors where the given cell index is a parent

    Returns: Formatted multiline string
    """
    result = ""
    for cell_index, error_message, error_position in find_cells_with_error(layout, parent_cell_index):
        instance_data = get_cell_instance_hierarchy(layout, cell_index)
        result += f"{error_message}\n"
        for inst_data in instance_data:
            result += f"Error instance at {str(inst_data.trans * error_position)}:\n"
            result += formatted_cell_instance_hierarchy(inst_data) + "\n"
    return result
