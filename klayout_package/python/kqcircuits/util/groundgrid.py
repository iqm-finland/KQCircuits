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


from kqcircuits.pya_resolver import pya


def insert_ground_grid(
    target_cell: pya.Cell,
    target_layer: pya.LayerInfo,
    grid_area: pya.Box,
    protection: pya.Region | pya.RecursiveShapeIterator,
    grid_step: int,
    grid_size: int,
):
    """Generates ground grid as shapes in a target cell, without cell hierarchy.
    This function uses integer database units for all inputs.

    Args:
        target_cell: Cell to place the grid into
        target_layer: Layer to place the grid into
        grid_area: Area to fill with grid
        protection: Region to avoid when filling grid
        grid_step: distance between grid rectangles
        grid_size: size of grid rectangles
    """
    _, grid_cell = _make_ground_grid_cell(target_layer, grid_area, protection, grid_step, grid_size)

    # Copy shapes from temporary layout to the target cell. This flattens the instances of ``grid_element_cell``.
    cm = pya.CellMapping()
    cm.for_single_cell(target_cell, grid_cell)
    target_cell.copy_tree_shapes(grid_cell, cm)


def make_ground_grid_region(
    grid_area: pya.Box, protection: pya.Region | pya.RecursiveShapeIterator, grid_step: int, grid_size: int
) -> pya.Region:
    """Returns ground grid as a ``Region``. This function uses integer database units for all inputs.

    Note: ``insert_ground_grid`` is more efficient if the grid will be inserted into a cell.

    Args:
        target_layer: Layer definition to place the grid into
        grid_area: Area to fill with grid
        protection: Region to avoid when filling grid
        grid_step: distance between grid rectangles
        grid_size: size of grid rectangles

    Returns: a Region containing the ground grid
    """
    dummy_layer = pya.LayerInfo(1, 0)
    layout, grid_cell = _make_ground_grid_cell(dummy_layer, grid_area, protection, grid_step, grid_size)
    grid_region = pya.Region(grid_cell.begin_shapes_rec(layout.layer(dummy_layer)))
    grid_region.merge()  # Ensure the RecursiveShapeIterator is fully iterated over before we discard ``layout``
    return grid_region


def _make_ground_grid_cell(
    target_layer: pya.LayerInfo,
    grid_area: pya.Box,
    protection: pya.Region | pya.RecursiveShapeIterator,
    grid_step: int,
    grid_size: int,
) -> tuple[pya.Layout, pya.Cell]:
    """Generates ground grid as cell instances in a new cell in a new layout. The returned ``cell`` contains a child
    cell instance for each grid cell element, and should generally be flattened to avoid having too many cell instances.

    A reference to ``layout`` must be kept as long as ``cell`` is used.

    This function uses integer database units for all inputs.

    Args:
        target_layer: Layer definition to place the grid into
        grid_area: Area to fill with grid
        protection: Region to avoid when filling grid
        grid_step: distance between grid rectangles
        grid_size: size of grid rectangles

    Returns: tuple ``(layout, cell)`` containing a new ``Layout`` and ``Cell``.
    """
    region_with_ground_grid = pya.Region(grid_area) - protection

    # Create temporary layout for ground grid operations
    layout = pya.Layout()
    layout.insert_layer(target_layer)

    # Create a cell with a single ground grid square
    grid_element_cell = layout.create_cell("grid_element")
    grid_element_cell.shapes(layout.layer(target_layer)).insert(pya.Box(0, 0, grid_size, grid_size))

    # Generate the full ground grid as instances of ``grid_element_cell`` in a new cell
    grid_cell = layout.create_cell("grid")
    grid_cell.fill_region(
        region_with_ground_grid,
        grid_element_cell.cell_index(),
        pya.Box(0, 0, grid_size, grid_size),
        pya.Vector(grid_step, 0),
        pya.Vector(0, grid_step),
        pya.Point(0, 0),
    )

    return layout, grid_cell
