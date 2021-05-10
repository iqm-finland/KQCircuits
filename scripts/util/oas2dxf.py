# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

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
