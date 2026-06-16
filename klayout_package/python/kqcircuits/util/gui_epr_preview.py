# This code is part of KQCircuits
# Copyright (C) 2026 IQM Finland Oy
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

"""Utility functions for EPR preview markers in the KLayout GUI."""

import importlib
import importlib.util

from kqcircuits.pya_resolver import pya


def _get_epr_instance_trans(layout_view):
    """Returns DCplxTrans of the single currently selected instance in the LayoutView.

    Returns None (without raising) if:
      - no instance is selected
      - more than one instance is selected

    Args:
        layout_view: the active pya.LayoutView
    """
    selected = list(layout_view.each_object_selected())
    if len(selected) != 1:
        return None
    return selected[0].inst().dcplx_trans


def _load_epr_module(element):
    """Dynamically imports and reloads the EPR module that corresponds to this element.

    Returns the module, or None if no EPR module exists for this element.

    Args:
        element: the Element instance whose EPR module should be loaded
    """
    library_name = element.__module__.split(".", maxsplit=1)[0]
    element_name = element.__module__.rsplit(".", maxsplit=1)[-1]
    epr_module_path = f"{library_name}.simulations.epr.{element_name}"
    if not importlib.util.find_spec(epr_module_path):
        return None
    epr_module = importlib.import_module(epr_module_path)
    importlib.reload(epr_module)
    return epr_module


def _draw_epr_markers(element, layout_view):
    """Draw EPR markers (cross-section cuts and partition regions) into the active LayoutView."""
    trans = _get_epr_instance_trans(layout_view)
    if trans is None:
        return

    epr_module = _load_epr_module(element)
    if epr_module is None:
        return

    if element._epr_cross_section_cut:
        _draw_epr_cross_section_cuts(element, layout_view, trans, epr_module)

    _draw_epr_partition_regions(element, layout_view, trans, epr_module)


def _draw_epr_cross_section_cuts(element, layout_view, trans, epr_module):
    """Draw EPR correction cuts as persistent KLayout Markers.

    A line marker is drawn for each cut, plus text markers at both endpoints.

    Args:
        element: the Element instance
        layout_view: the active pya.LayoutView
        trans: DCplxTrans of the selected element instance
        epr_module: the loaded EPR module for this element
    """
    assert hasattr(epr_module, "correction_cuts"), \
        f"No 'correction_cuts' function defined in EPR module for {type(element).__name__}"

    cuts = epr_module.correction_cuts(element)
    for cut_name, cut in cuts.items():
        p1 = trans.trans(cut["p1"])
        p2 = trans.trans(cut["p2"])

        line_marker = pya.Marker()
        line_marker.set_path(pya.DPath([p1, p2], 0))
        line_marker.line_width = 2
        line_marker.color = 0xFF4500  # orange-red
        layout_view.add_marker(line_marker)

        for label, pt in [(f"{cut_name}_p1", p1), (f"{cut_name}_p2", p2)]:
            text_marker = pya.Marker()
            text_marker.set_text(pya.DText(label, pt.x, pt.y))
            text_marker.color = 0xFF4500
            layout_view.add_marker(text_marker)


def _draw_epr_partition_regions(element, layout_view, trans, epr_module):
    """Draw EPR partition regions as persistent KLayout Markers.

    A filled polygon marker and a centred text marker are drawn for each enabled
    partition region.

    Args:
        element: the Element instance
        layout_view: the active pya.LayoutView
        trans: DCplxTrans of the selected element instance
        epr_module: the loaded EPR module for this element
    """
    assert hasattr(epr_module, "partition_regions"), \
        f"No 'partition_regions' function defined in EPR module for {type(element).__name__}"

    partition_regions = epr_module.partition_regions(element)

    for pr in partition_regions:
        if not hasattr(element, f"_epr_part_reg_{pr.name}"):
            continue
        if not getattr(element, f"_epr_part_reg_{pr.name}"):
            continue

        region = pya.Region()
        if isinstance(pr.region, list):
            for r in pr.region:
                region += pya.Region(r.to_itype(element.layout.dbu))
        elif isinstance(pr.region, pya.Region):
            region = pr.region
        else:
            region = pya.Region(pr.region.to_itype(element.layout.dbu))

        for polygon in region.each():
            dpoly = polygon.to_dtype(element.layout.dbu).transformed(trans)
            poly_marker = pya.Marker()
            poly_marker.set_polygon(dpoly)
            poly_marker.dither_pattern = 2   # crosshatch fill — makes region extent clearly visible
            poly_marker.line_width = 2
            poly_marker.color = 0x1E90FF      # dodger blue
            poly_marker.vertex_size = 4
            layout_view.add_marker(poly_marker)

        center = region.bbox().to_dtype(element.layout.dbu).center()
        center_transformed = trans.trans(center)
        text_marker = pya.Marker()
        text_marker.set_text(pya.DText(pr.name, center_transformed.x, center_transformed.y))
        text_marker.color = 0x1E90FF
        layout_view.add_marker(text_marker)
