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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).
import os

import pytest

from kqcircuits.pya_resolver import pya, lay
from kqcircuits.util.layout_to_code import convert_cells_to_code
from kqcircuits.defaults import SCRIPTS_PATH


def test_generated_code_of_waveguide_composite():
    if not hasattr(lay, "LayoutView"):
        pytest.xfail("Stand-alone mask not supported on klayout < 0.28")

    macro = os.path.join(SCRIPTS_PATH, "macros/generate/test_waveguide_composite.lym")
    with open(macro, "r") as fp:
        xml = fp.read()
    start_ind = xml.find("<text>") + len("<text>")
    end_ind = xml.rfind("#END-TEST-HERE")
    code1 = xml[start_ind:end_ind]
    view1 = _run_macro(code1)

    code2 = convert_cells_to_code(view1.top_cell, add_instance_names=False, output_format="macro")
    view2 = _run_macro(code2)
    print(code2)

    diff = pya.LayoutDiff()
    assert diff.compare(view1.layout, view2.layout), "Generated code results in different geometry!"


def _run_macro(code):
    """Run macro code.

    **Usage note**: the caller **must** keep a reference to ``layout_view``, otherwise ``layout`` will be deleted by the
    garbage collector.

    Args:
        code: Code string to execute, including a call to ``view = KLayoutView()``

    Returns: tuple (layout, top_cell, layout_view) corresponding to the returns of ``prep_emtpy_layout``
    """
    _locals = locals()
    exec(code, globals(), _locals)  # pylint: disable=exec-used
    return _locals["view"]
