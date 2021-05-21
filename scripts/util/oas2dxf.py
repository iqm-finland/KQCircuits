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


# Convert .oas to .dxf or the other way around
# usage: oas2dxf.py <some.oas>
#    or: oas2dxf.py <some.dxf>

from sys import argv
from os import path
from kqcircuits.pya_resolver import pya

file_in = argv[1]

if file_in.endswith(".dxf"):
    file_out = file_in[0:-4] + ".oas"
else:
    file_out = file_in[0:-4] + ".dxf"

layout = pya.Layout()
layout.read(file_in)

slo = pya.SaveLayoutOptions()
slo.set_format_from_filename(file_out)
slo.write_context_info = False

if file_out.endswith(".oas"):
    slo.oasis_substitution_char = "*"
    if file_in.endswith(".dxf"):    # DXF does not record TOP cell, let's use the file name
        layout.top_cell().name = path.split(file_out)[1][:-4]

layout.write(file_out, slo)
