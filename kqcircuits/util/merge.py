# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

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
