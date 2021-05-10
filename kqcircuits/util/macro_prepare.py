# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

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
