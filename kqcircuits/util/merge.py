from kqcircuits.pya_resolver import pya

from kqcircuits.defaults import default_layers


# merging the layers optical lit1 and grid layer. (2,0) + (5,0)
def merge_layers(layout, cell_list):
    for cell in cell_list:
        iter1 = pya.RecursiveShapeIterator(layout, cell, layout.layer(default_layers["b base metal gap wo grid"]))
        iter2 = pya.RecursiveShapeIterator(layout, cell, layout.layer(default_layers["b ground grid"]))

        reg1 = pya.Region(iter1)
        reg2 = pya.Region(iter2)

        merge_reg = reg1 + reg2

        cell.shapes(layout.layer(default_layers["b base metal gap"])).insert(merge_reg)
