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

from kqcircuits.klayout_view import resolve_default_layer_info
from kqcircuits.pya_resolver import pya, lay


def get_layer_color(layout_view, layer_name):
    """Find the fill color of a given layer in the current layout view.

    Args:
        layout_view: Reference to the LayoutView
        layer_name: Name of the layer, will be looked up in default layers

    Returns: Fill color (int)
    """
    layer_info = resolve_default_layer_info(layer_name)
    layer_properties = [
        l
        for l in layout_view.each_layer()
        if l.source_layer == layer_info.layer and l.source_datatype == layer_info.datatype
    ][0]

    return layer_properties.fill_color


def test_get_pixels_outside_chip_area_is_white(klayout_view_with_chip):
    """Sample an area _outside_ the chip area, so we know there is no geometry. We expect the background color."""
    if not hasattr(lay, "LayoutView"):
        pytest.xfail("get_pixels is not supported on klayout < 0.28")

    image = klayout_view_with_chip.get_pixels(box=pya.DBox(-100, -100, 0, 0), width=100, height=100)
    assert image.pixel(50, 50) == 0xFFFFFFFF


def test_get_pixels_single_layer_matches_layer_color(klayout_view_with_chip):
    """Sample an area in the chip border.
    This area contains the chip frame, so we expect the color of base_metal_gap_wo_grid."""
    if not hasattr(lay, "LayoutView"):
        pytest.xfail("get_pixels is not supported on klayout < 0.28")

    image = klayout_view_with_chip.get_pixels(
        box=pya.DBox(0, 0, 100, 100), width=100, height=100, layers_set=["1t1_base_metal_gap_wo_grid"]
    )
    assert image.pixel(50, 50) == get_layer_color(klayout_view_with_chip.layout_view, "1t1_base_metal_gap_wo_grid")


def test_get_pixels_no_layers_is_white(klayout_view_with_chip):
    """Sample an area in the chip border, which contains geometry as proven by the preceding tests.
    We set the layer list to empty, so we expect nothing is drawn and we get the background color."""
    if not hasattr(lay, "LayoutView"):
        pytest.xfail("get_pixels is not supported on klayout < 0.28")

    image = klayout_view_with_chip.get_pixels(box=pya.DBox(0, 0, 100, 100), width=100, height=100, layers_set=[])
    assert image.pixel(50, 50) == 0xFFFFFFFF


def test_get_pixels_restores_visibility_state(klayout_view_with_chip):
    if not hasattr(lay, "LayoutView"):
        pytest.xfail("get_pixels is not supported on klayout < 0.28")

    view = klayout_view_with_chip

    # Set up some unusual view state
    view.layout_view.min_hier_levels = 1
    view.layout_view.max_hier_levels = 2
    view.active_cell = view.layout.cell(3)

    # Check initial view state for remaining properties
    initial_layer_visibility = [_layer.visible for _layer in view.layout_view.each_layer()]
    initial_zoom = view.layout_view.box()

    # Grab image of the top cell, changing the box and layers
    view.get_pixels(
        cell=view.top_cell,
        box=pya.DBox(0, 0, 100, 100),
        width=100,
        height=100,
        layers_set=["1t1_base_metal_gap_wo_grid"],
    )

    # Retrieve state after get_pixels
    final_layer_visibility = [_layer.visible for _layer in view.layout_view.each_layer()]
    final_zoom = view.layout_view.box()

    # Verify that the state was restored
    assert view.layout_view.min_hier_levels == 1
    assert view.layout_view.max_hier_levels == 2
    assert view.active_cell is view.layout.cell(3)
    assert all([a == b for a, b in zip(initial_layer_visibility, final_layer_visibility)])
    assert str(initial_zoom) == str(final_zoom)


def test_get_pixels_is_equal_to_export_bitmap(klayout_view_with_chip, tmp_path):
    if not hasattr(lay, "LayoutView"):
        pytest.xfail("get_pixels is not supported on klayout < 0.28")

    view = klayout_view_with_chip

    w = 100
    h = 100

    # Export PNG and load as PixelBuffer
    view._export_bitmap(tmp_path, view.top_cell, "test", pngsize=[w, h], layers_set="all")
    pb1 = lay.PixelBuffer.read_png(str(tmp_path.joinpath("test.png")))

    # Grab a PixelBuffer directly
    pb2 = view.get_pixels(view.top_cell, width=w, height=h)

    assert all([all([pb1.pixel(x, y) == pb2.pixel(x, y) for y in range(h)]) for x in range(w)])
