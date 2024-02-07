# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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

import os
from pathlib import Path


def find_ansys_executable(default):
    """Finds latest Ansys Electronics executable from default installation locations. Returns 'default' if not found.
    """
    paths = [(Path(os.environ.get("ProgramFiles", r"C:\Program Files")).joinpath("AnsysEM"), r"Win64\ansysedt.exe"),
             (Path("/opt/AnsysEM"), "Linux64/ansysedt")]
    for root, exe in paths:
        if os.path.isdir(root):
            versions = sorted([f for f in os.listdir(root) if f.startswith("v")], reverse=True)
            for version in versions:
                executable = root.joinpath(version).joinpath(exe)
                if os.path.isfile(executable):
                    return executable
    return default
