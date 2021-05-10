# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

# Helper script to create a .png image of the given pcell.
#
# Specify library, class name and destination directory for the .png file. For example:
# klayout -z -nc -r pcell2png.py -rd lib_name=kqcircuits.elements.finger_capacitor_square -rd cls_name=FingerCapacitorSquare -rd dest_dir=tmp

from sys import argv
from os import mkdir
from pathlib import Path
from importlib import import_module
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
