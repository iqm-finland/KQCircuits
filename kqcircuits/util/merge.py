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


from kqcircuits.pya_resolver import pya


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
