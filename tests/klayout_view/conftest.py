# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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

from kqcircuits.pya_resolver import lay
from kqcircuits.klayout_view import KLayoutView
from kqcircuits.chips.demo import Chip


@pytest.fixture
def klayout_view_with_chip():
    """A KLayoutView with well-defined rendering settings and a Chip inserted at 0,0"""
    if not hasattr(lay, "LayoutView"):
        return None

    view = KLayoutView(background_color="#ffffff")
    view.layout_view.set_config("grid-visible", "false")
    view.layout_view.set_config("guiding-shape-visible", "false")
    view.insert_cell(Chip)
    return view
