# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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
from kqcircuits.pya_resolver import pya
from kqcircuits.util.layout_to_code import convert_cells_to_code
from kqcircuits.defaults import SCRIPTS_PATH


def test_generated_code_of_waveguide_composite():
    macro = os.path.join(SCRIPTS_PATH, "macros/generate/test_waveguide_composite.lym")
    with open(macro, "r") as fp:
        xml = fp.read()
    start_ind = xml.find("<text>") + len("<text>")
    end_ind = xml.rfind("</text>")
    code1 = xml[start_ind:end_ind]
    layout1, top_cell1 = _run_macro(code1)

    code2 = convert_cells_to_code(top_cell1, output_format="create+macro")
    layout2, _ = _run_macro(code2)
    print(code2)

    diff = pya.LayoutDiff()
    assert diff.compare(layout1, layout2), "Generated code results in different geometry!"


def _run_macro(code):
    """Run macro code and return layout & top_cell."""
    _locals = locals()
    exec(code, globals(), _locals)  # pylint: disable=exec-used
    return _locals["layout"], _locals["top_cell"]
