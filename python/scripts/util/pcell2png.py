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
# Specify library, class name and destination directory for the .png file. For example:
# klayout -z -nc -r pcell2png.py -rd lib_name=kqcircuits.elements.finger_capacitor_square -rd
# cls_name=FingerCapacitorSquare -rd dest_dir=tmp

from importlib import import_module
from pathlib import Path

from kqcircuits.klayout_view import KLayoutView
from kqcircuits.pya_resolver import pya

module = import_module(lib_name)
cls = getattr(module, cls_name)
path = Path(dest_dir)

layout = KLayoutView.get_active_layout()
top = layout.create_cell("top")
cell = cls.create(layout)
top.insert(pya.DCellInstArray(cell.cell_index(), pya.DTrans()))
view = KLayoutView(current=True)
view.focus(top)
size = 1000 if lib_name.startswith("kqcircuits.chips") else 500
view.export_pcell_png(path, top, cls.__module__, max_size=size)
