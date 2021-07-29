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


import logging
import sys
import pathlib
import importlib

from kqcircuits.pya_resolver import pya
from kqcircuits.util import macro_prepare
from kqcircuits.util.log_router import route_log_to_stdout

# Script to create a KQCircuits element in KLayout by specifying the path to the module file containing the element.
# This script can be used to integrate with external editors.
#
# Command line usage:
#   klayout_app -e -rx -rm path/to/create_element_from_path.py -rd element_path=kqcircuits\chips\demo.py
#
# Here, the flags specify the following:
#  -e: Run KLayout in edit mode
#  -rx: Skip running automatic startup scripts (avoids creating a second empty layout)
#  -rm: Run this script on startup
#  -rd: Inject a variable element_path into the script scope containing the path of the element module to create.
#       element_path should be relative to the kqcircuits repository, and it should be a module containing exactly
#       one KQCircuits Element or Chip.
#
# To use this as an external tool in Pycharm:
# - Under Settings -> Tools -> External Tools create a new entry as follows:
#   - Program: point to klayout_app.exe (Windows) or the klayout executable (Linux)
#   - Arguments: -e -rx -rm "$ContentRoot$\klayout_package\python\scripts\create_element_from_path.py" -rd
#                element_path="$FilePathRelativeToProjectRoot$"
# - To execute, right click the python file (in the Project browser on the editor tab) containing the element to create
#   and choose the tool under External Tools.

# Set up logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
route_log_to_stdout(lowest_visible_level="INFO")

logging.info(f"Element path: {element_path}")

# Figure out the python import path from the specified file path
path_without_extension = pathlib.Path(element_path).with_suffix('')
if path_without_extension.parts[0] == "klayout_package" and path_without_extension.parts[1] == "python":
    module_path = '.'.join(path_without_extension.parts[2:])
else:
    module_path = '.'.join(path_without_extension.parts)
module_name = path_without_extension.name

# Import module
module = importlib.import_module(module_path)

logging.info(f"Loaded module {str(module)}")

# Find classes that are in this actual module (rather than imported from somewhere else)
classes_in_module = [m for m in vars(module).values() if hasattr(m, '__module__') and m.__module__ == module_path]
element_classes = [m for m in classes_in_module if 'Element' in [s.__name__ for s in m.__mro__]]

logging.info(f"Found classes {str(element_classes)}")

if len(element_classes) == 1:
    cls = element_classes[0]
else:
    raise ValueError("Expecting exactly one class in the module to run.")

# Create an empty layout with top cell
layout, layout_view, cell_view = macro_prepare.prep_empty_layout()
top_cell = layout.create_cell("Top Cell")
cell_view.cell_name = top_cell.name  # Set our cell as top cell

cell = cls.create(layout)
top_cell.insert(pya.DCellInstArray(cell.cell_index(), pya.DTrans()))

# Show all hierarchy levels and zoom to fit window
layout_view.max_hier()
layout_view.zoom_fit()
