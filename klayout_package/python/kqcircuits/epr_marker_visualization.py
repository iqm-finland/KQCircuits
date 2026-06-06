# epr_marker_visualization.py

from __future__ import annotations

import importlib
from typing import Optional

from kqcircuits.pya_resolver import pya, lay

from kqcircuits.simulations.epr.partition_region import (
    PartitionRegion,
)


# ============================================================
# GLOBAL MARKER STATE
# ============================================================

# Keep references alive so KLayout doesn't GC markers
_ACTIVE_MARKERS = []


# ============================================================
# MARKER MANAGEMENT
# ============================================================

def clear_epr_markers():
    """
    Remove all EPR markers from current LayoutView.
    """

    global _ACTIVE_MARKERS

    layout_view = lay.LayoutView.current()

    if layout_view is None:
        return

    try:
        layout_view.clear_markers()
    except Exception:
        pass

    _ACTIVE_MARKERS = []


def add_marker(marker):
    """
    Add marker and keep Python reference alive.
    """

    global _ACTIVE_MARKERS

    layout_view = lay.LayoutView.current()

    if layout_view is None:
        return

    layout_view.add_marker(marker)

    _ACTIVE_MARKERS.append(marker)


# ============================================================
# SELECTION HELPERS
# ============================================================

def get_single_selected_transform() -> Optional[pya.DCplxTrans]:
    """
    Return transform of selected instance.

    Only valid if exactly one object selected.
    """

    layout_view = lay.LayoutView.current()

    if layout_view is None:
        return None

    selected = list(layout_view.each_object_selected())

    if len(selected) != 1:
        return None

    try:
        return selected[0].inst().dcplx_trans
    except Exception:
        return None


# ============================================================
# TRANSFORM HELPERS
# ============================================================

def transform_dpolygon(poly, trans):

    pts = []

    for p in poly.each_point_hull():
        pts.append(trans * p)

    return pya.DPolygon(pts)


def transform_dpath(path, trans):

    pts = []

    for p in path.each_point():
        pts.append(trans * p)

    return pya.DPath(pts, path.width)


# ============================================================
# MARKER STYLE
# ============================================================

def style_partition_marker(marker):

    marker.line_width = 2
    marker.vertex_size = 0
    marker.dither_pattern = 3
    marker.halo = 1

    # ARGB
    marker.color = 0x55FF0000


def style_cut_marker(marker):

    marker.line_width = 4
    marker.vertex_size = 4
    marker.halo = 1

    marker.color = 0xFF00FFFF


def style_text_marker(marker):

    marker.line_width = 1
    marker.vertex_size = 0
    marker.halo = 1

    marker.color = 0xFFFFFFFF


# ============================================================
# DRAW PARTITION REGION
# ============================================================

def draw_partition_region(region, trans):

    poly = transform_dpolygon(region.region, trans)

    marker = pya.Marker()

    marker.set_polygon(poly)

    style_partition_marker(marker)

    add_marker(marker)

    # ----------------------------------------
    # Text marker
    # ----------------------------------------

    bbox = poly.bbox()

    center = bbox.center()

    text_marker = pya.Marker()

    text_marker.set_text(
        region.name,
        center,
    )

    style_text_marker(text_marker)

    add_marker(text_marker)


# ============================================================
# DRAW CORRECTION CUT
# ============================================================

def draw_correction_cut(name, cut, trans):

    p1 = trans * cut[0]
    p2 = trans * cut[1]

    path = pya.DPath([p1, p2], 0)

    marker = pya.Marker()

    marker.set_path(path)

    style_cut_marker(marker)

    add_marker(marker)

    # ----------------------------------------
    # Endpoint labels
    # ----------------------------------------

    m1 = pya.Marker()

    m1.set_text(
        f"{name}_A",
        p1,
    )

    style_text_marker(m1)

    add_marker(m1)

    m2 = pya.Marker()

    m2.set_text(
        f"{name}_B",
        p2,
    )

    style_text_marker(m2)

    add_marker(m2)


# ============================================================
# LOAD EPR MODULE
# ============================================================

def load_epr_module(element):

    module_name = element.__class__.__module__.split(".")[-1]

    epr_module_path = (
        f"kqcircuits.simulations.epr.{module_name}"
    )

    try:
        return importlib.import_module(epr_module_path)

    except ModuleNotFoundError:
        return None


# ============================================================
# MAIN ENTRY
# ============================================================

def update_epr_markers(element):
    """
    Main redraw function.

    Safe against:
    - no selection
    - multiple selections
    - missing modules
    """

    clear_epr_markers()

    # ----------------------------------------
    # User toggle
    # ----------------------------------------

    if not getattr(element, "_epr_show", False):
        return

    # ----------------------------------------
    # Selection handling
    # ----------------------------------------

    trans = get_single_selected_transform()

    if trans is None:
        return

    # ----------------------------------------
    # EPR module
    # ----------------------------------------

    epr_module = load_epr_module(element)

    if epr_module is None:
        return

    # ----------------------------------------
    # Partition regions
    # ----------------------------------------

    if hasattr(epr_module, "partition_regions"):

        try:
            regions = epr_module.partition_regions(element)

            for region in regions:

                param_name = (
                    f"_epr_part_reg_{region.name}"
                )

                enabled = getattr(
                    element,
                    param_name,
                    False,
                )

                if not enabled:
                    continue

                draw_partition_region(
                    region,
                    trans,
                )

        except Exception as exc:
            print(
                "Failed drawing partition regions:",
                exc,
            )

    # ----------------------------------------
    # Correction cuts
    # ----------------------------------------

    if getattr(
        element,
        "_epr_cross_section_cut",
        False,
    ):

        if hasattr(epr_module, "correction_cuts"):

            try:

                cuts = epr_module.correction_cuts(
                    element
                )

                for name, cut in cuts.items():

                    draw_correction_cut(
                        name,
                        cut,
                        trans,
                    )

            except Exception as exc:
                print(
                    "Failed drawing correction cuts:",
                    exc,
                )
```
