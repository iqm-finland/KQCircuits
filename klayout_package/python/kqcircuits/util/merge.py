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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).
from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import region_with_merged_polygons


def merge_layers(layout, cell_list, layer_1, layer_2, layer_merged):
    """Inserts shapes in layer_1 and layer_2 to layer_merged.

    Args:
        layout: Layout of the cells
        cell_list: list of Cells whose shapes are merged (recursively)
        layer_1: LayerInfo of the layer to be merged with layer_2
        layer_2: LayerInfo of the layer to be merged with layer_1
        layer_merged: LayerInfo of the layer where the merged shapes are inserted

    """
    for cell in cell_list:
        iter1 = pya.RecursiveShapeIterator(layout, cell, layout.layer(layer_1))
        iter2 = pya.RecursiveShapeIterator(layout, cell, layout.layer(layer_2))

        reg1 = pya.Region(iter1)
        reg2 = pya.Region(iter2)

        merge_reg = reg1 + reg2

        cell.shapes(layout.layer(layer_merged)).insert(merge_reg)


def merge_layout_layers_on_face(layout, cell, face, tolerance=0.004):
    """Creates "base_metal_gap" layer on given face.

    The layer shape is combination of three layers using subtract (-) and insert (+) operations:

        "base_metal_gap" = "base_metal_gap_wo_grid" - "base_metal_addition" + "ground_grid"

    Args:
        layout: Layout containing the cell
        cell: Cell to merge
        face: face dictionary containing layer names as keys and layer info objects as values
        tolerance: gap length to be ignored while merging (µm)
    """
    gaps = pya.Region(cell.begin_shapes_rec(layout.layer(face["base_metal_gap_wo_grid"])))
    metal = pya.Region(cell.begin_shapes_rec(layout.layer(face["base_metal_addition"])))
    grid = cell.begin_shapes_rec(layout.layer(face["ground_grid"]))
    res = cell.shapes(layout.layer(face["base_metal_gap"]))
    res.insert(region_with_merged_polygons(gaps - metal, tolerance / layout.dbu))
    res.insert(grid)


def convert_child_instances_to_static(layout: pya.Layout, cell: pya.Cell, only_elements: bool = True,
                                      prune: bool = True):
    """Convert child instances of a cell to static.

    This function avoids duplicating cells: in case there are multiple instances pointing to the same PCell, only
    one static cell is created and all instances are pointed to that cell. This is in contrast to calling
    ``Instance.convert_to_static()`` on each instance separately.

    Args:
        layout: the Layout that contains the cell
        cell: static cell that may contain PCell instances to be converted
        only_elements: if True (default), only PCells which are descendants of Element are made static
        prune: if True, the PCells are deleted if they are no longer used anywhere in the layout.
    """

    # Build a dictionary {pcell: list of instances} for all instances that need to be converted
    cells_to_convert = {}
    for inst in cell.each_inst():
        if inst.is_pcell() and (not only_elements or isinstance(inst.pcell_declaration(), Element)):
            pcell = layout.cell(inst.cell_index)
            cells_to_convert[pcell] = cells_to_convert.get(pcell, []) + [inst]

    # Convert the cells and point the instances to the new static cell
    for pcell, instances in cells_to_convert.items():
        static_cell_index = layout.convert_cell_to_static(pcell.cell_index())
        for inst in instances:
            inst.cell_index = static_cell_index

    # Prune: deletes the old PCells unless they are still used elsewhere.
    if prune:
        for pcell in cells_to_convert:
            layout.prune_cell(pcell.cell_index(), -1)
