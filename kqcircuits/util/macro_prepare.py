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


from kqcircuits.pya_resolver import pya

from kqcircuits.klayout_view import KLayoutView


# This script has multiple sideeffects

def prep_empty_layout():
    """Creates an empty layout with default layers.

    Returns:
        A tuple ``(layout, layout_view, cell_view)``

        * ``layout``:  the created layout
        * ``layout_view``: layout view for the layout
        * ``cell_view``: cell view for the layout
    """

    view = KLayoutView(current=False, initialize=True)
    layout = KLayoutView.get_active_layout()
    layout_view = view.layout_view
    cell_view = view.get_active_cell_view()

    return layout, layout_view, cell_view


def get_layout_top_cell():
    cell_view = pya.CellView.active()
    layout = cell_view.layout()
    return layout.top_cell()
