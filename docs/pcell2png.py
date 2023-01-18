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


# Helper script to create a .png image of the given pcell.
#
# Specify library, class name and destination directory for the .png file. If element file path is
# also given then rulers showing important sizes are also drawn on the .png file in the specified
# places.
#
# klayout -z -nc -r docs/pcell2png.py -rd lib_name=kqcircuits.elements.finger_capacitor_square
#         -rd cls_name=FingerCapacitorSquare -rd dest_dir=tmp [-rd cls_path=<path of element file>]


from importlib import import_module
from pathlib import Path

from kqcircuits.defaults import default_layers
from kqcircuits.klayout_view import KLayoutView
from kqcircuits.pya_resolver import pya


# Ruler places are specified as space delimited x,y coordinate pairs after a "MARKERS_FOR_PNG" tag.
# Ruler places can also be added manually using x1,y1,x2,y2 format.
def add_rulers(path, view):
    if path == "":
        return

    rulers = []
    with open(path) as f:
        for line in f:
             a = line.split("MARKERS_FOR_PNG ")[1:]
             if a:
                rulers += a[0].split(' ')

    #Check for autoruler in x,y format or manual ruler in x1,y1,x2,y2 format
    for ruler in rulers:
        markers = [float(x) for x in ruler.split(',')]
        if len(markers) == 2:
            ant = view.layout_view.create_measure_ruler(pya.DPoint(markers[0], markers[1]))
            ant.fmt = "$(sprintf('%.1f',D))"
        elif len(markers) == 4:
            ant = pya.Annotation()
            ant.p1 = pya.DPoint(markers[0],markers[1])
            ant.p2 = pya.DPoint(markers[2],markers[3])
            ant.style = pya.Annotation.StyleRuler
            ant.fmt = "$(sprintf('%.1f',D))"
            view.layout_view.insert_annotation(ant)


module = import_module(lib_name)
cls = getattr(module, cls_name)
path = Path(dest_dir)
cls_path = cls_path if "cls_path" in locals() else ""
view = KLayoutView()
layout = view.layout
cell = cls.create(layout)

#Insert the element to the layout
view.insert_cell(cell)

# save the element as static .oas file
static_cell = layout.cell(layout.convert_cell_to_static(cell.cell_index()))
save_opts = pya.SaveLayoutOptions()
save_opts.format = "OASIS"
save_opts.write_context_info = False  # to save all cells as static cells
static_cell.write(f"{path}/{cls.__module__}.oas", save_opts)

#Hides specified layers before saving png - improves readability and rulers
layers_to_remove = ['refpoints','1t1_ports','1t1_ground_grid_avoidance', '2b1_ground_grid_avoidance']
for layer in layers_to_remove: layout.delete_layer(layout.layer(default_layers[layer]))
view.focus()

# export as .png file
add_rulers(cls_path, view)
size = 1000 if lib_name.find(".chips.") != -1 else 500
view.export_pcell_png(path, view.top_cell, cls.__module__, max_size=size)
