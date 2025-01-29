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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

import pytest
from kqcircuits.klayout_view import KLayoutView
from kqcircuits.pya_resolver import pya, lay
from kqcircuits.util.geometry_helper import round_dpath_width


def test_already_rounded_path_has_no_effect():
    dpath = pya.DPath([pya.DPoint(0, 0), pya.DPoint(0, 100), pya.DPoint(100, 100), pya.DPoint(100, 500)], 10)
    assert dpath == round_dpath_width(dpath, 0.001), "Rounding already rounded DPath should produce same DPath"


def test_unrounded_path_gets_rounded():
    dpath = pya.DPath(
        [pya.DPoint(0, 0), pya.DPoint(0, 100), pya.DPoint(100, 100), pya.DPoint(100, 500)], 7.502857003982128
    )
    dbu = 0.001
    rounded_dpath = round_dpath_width(dpath, dbu)
    assert dpath.points == rounded_dpath.points, "Points list should be same before and after rounding"
    assert dpath.width != rounded_dpath.width, "Unrounded DPath width shouldn't be identical to rounded DPath width"
    assert (
        dpath.to_itype(dbu).width - rounded_dpath.to_itype(dbu).width == 1
    ), "Width of rounded DPath should differ in databse units by 1 from the unrounded DPath"


def test_rounded_path_can_be_saved(tmp_path):
    if not hasattr(lay, "LayoutView"):
        pytest.xfail("KLayoutView not supported on klayout < 0.28")

    layout_view = KLayoutView()
    dpath = pya.DPath(
        [pya.DPoint(0, 0), pya.DPoint(0, 100), pya.DPoint(100, 100), pya.DPoint(100, 500)], 7.502857003982128
    )
    rounded_dpath = round_dpath_width(dpath, layout_view.layout.dbu)
    layout_view.top_cell.shapes(layout_view.layout.layer("waveguide_path")).insert(rounded_dpath)
    # Uncommenting below would cause RuntimeError: Paths with odd width cannot be written to OASIS files
    # layout_view.top_cell.shapes(layout_view.layout.layer("waveguide_path")).insert(dpath)
    layout_view.save_layout(str(tmp_path) + "/rounded_path.oas")
