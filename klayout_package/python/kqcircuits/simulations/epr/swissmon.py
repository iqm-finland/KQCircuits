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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

import math
from typing import Callable

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.epr.util import (
    extract_child_simulation,
    EPRTarget,
    create_bulk_and_mer_partition_regions,
)
from kqcircuits.simulations.partition_region import PartitionRegion


# Partition region and correction cuts definitions for Swissmon qubit


def _offset_point_away(p: pya.DPoint, sized: float) -> pya.DPoint:
    """Offset a point *away* from the origin by `sized` on each axis,
    using the sign of the coordinate to determine direction.
    For coordinates that are exactly zero, no offset is applied on that axis."""
    dx = math.copysign(sized, p.x) if p.x != 0 else 0.0
    dy = math.copysign(sized, p.y) if p.y != 0 else 0.0
    return pya.DPoint(p.x + dx, p.y + dy)


def _offset_point_toward(p: pya.DPoint, sized: float) -> pya.DPoint:
    """Offset a point *toward* the origin by `sized` on each axis,
    using the opposite sign of the coordinate to determine direction.
    For coordinates that are exactly zero, no offset is applied on that axis."""
    dx = math.copysign(sized, p.x) if p.x != 0 else 0.0
    dy = math.copysign(sized, p.y) if p.y != 0 else 0.0
    return pya.DPoint(p.x - dx, p.y - dy)


def partition_regions(simulation: EPRTarget, prefix: str = "") -> list[PartitionRegion]:
    metal_edge_dimension = 4.0
    metal_edge_margin = pya.DPoint(metal_edge_dimension, metal_edge_dimension)

    result = []
    base = simulation.refpoints["base"]
    sized = metal_edge_dimension + simulation.island_r

    # Each arm polygon is built from 4 epr_cross_* refpoints + base (origin).
    #
    # Full index layout (viewed from above, origin at center):
    #
    #              10  11 / 09  00
    #               |  |     |  |
    #   07--08--+--+-----+--+--00/09
    #   |                            |
    #   06--05--+--+-----+--+--03/00   (west and east inner corners)
    #               |  |     |  |
    #              06  07 / 03  04
    #
    # Per-arm index roles  [inner_A, outer_1, outer_2, inner_B]:
    #   crossleft   [6, 7, 8, 9]  — outer: 7, 8   inner: 6, 9
    #   crosstop    [9,10,11, 0]  — outer:10,11   inner: 9, 0
    #   crossright  [0, 1, 2, 3]  — outer: 1, 2   inner: 0, 3
    #   crossbottom [3, 4, 5, 6]  — outer: 4, 5   inner: 3, 6
    #
    # Point offsetting rules (applied before building the polygon):
    #   Outer points (arm tip and sides — the middle two in each list):
    #     Offset *away* from origin by `sized` on both axes, using the sign
    #     of each coordinate to determine direction. This expands the arm region
    #     outward to cover the metal edges at the arm tip and sides.
    #   Inner corner points (shared with the adjacent arms — the first and last):
    #     Offset *toward* origin by `sized` on both axes. This shrinks the inner
    #     corners inward so that the four arm polygons meet cleanly at `base`
    #     without gaps or overlaps at the center junction.
    #   base (origin): appended unchanged to close the polygon.

    for arm_name, indices in [
        ("crossleft",   [6, 7, 8, 9]),
        ("crosstop",    [9, 10, 11, 0]),
        ("crossright",  [0, 1, 2, 3]),
        ("crossbottom", [3, 4, 5, 6]),
    ]:
        raw = [simulation.refpoints[f"epr_cross_{i:02d}"] for i in indices]

        # raw[0] and raw[3] are the inner corner points → offset toward origin.
        # raw[1] and raw[2] are the outer (arm tip/side) points → offset away from origin.
        pts = [
            _offset_point_toward(raw[0], sized),
            _offset_point_away(raw[1], sized),
            _offset_point_away(raw[2], sized),
            _offset_point_toward(raw[3], sized),
        ]
        arm_poly = pya.DPolygon(pts + [base])

        result += create_bulk_and_mer_partition_regions(
            name=f"{prefix}{arm_name}",
            face=simulation.face_ids[0],
            metal_edge_dimensions=metal_edge_dimension,
            region=arm_poly,
            vertical_dimensions=3.0,
            visualise=True,
        )

    # These are added to include the waveguides attached to couplers in the coupler region
    def _get_coupler_wg_offset(i, s):
        wg_len = float(simulation.waveguide_length) if hasattr(simulation, "waveguide_length") else 0
        offset = wg_len + 25

        coupler_wg_offsets = [
            {"min": pya.DPoint(-offset, 0)},
            {"max": pya.DPoint(0, offset)},
            {"max": pya.DPoint(offset, 0)},
        ]

        return coupler_wg_offsets[i].get(s, pya.DPoint(0, 0))

    for idx in range(3):
        # Need to check if coupler is present
        if float(simulation.cpl_length[idx]) > 0:
            cplr_region = pya.DBox(
                simulation.refpoints[f"epr_cplr{idx}_min"]
                - metal_edge_margin
                + _get_coupler_wg_offset(idx, "min"),
                simulation.refpoints[f"epr_cplr{idx}_max"]
                + metal_edge_margin
                + _get_coupler_wg_offset(idx, "max"),
            )

            result += create_bulk_and_mer_partition_regions(
                name=f"{prefix}{idx}cplr",
                face=simulation.face_ids[0],
                metal_edge_dimensions=metal_edge_dimension,
                region=cplr_region,
                vertical_dimensions=3.0,
                visualise=True,
            )

    return result


def correction_cuts(simulation: EPRTarget, prefix: str = "") -> dict[str, dict]:
    # All four cross*mer cuts follow the same two-step strategy:
    #
    #   Step 1 — ideal position: place the cut halfway between the arm's inner gap
    #     edge (the epr_cross_* corner closest to cross center) and the origin (0,0).
    #     This keeps all cuts as close to center as possible.
    #
    #   Step 2 — coupler guard (clamp): if a coupler is present on that arm, the cut
    #     must not reach into the coupler region. The coupler bounding box is defined
    #     as bbox.p1 = epr_cplr*_min, bbox.p2 = epr_cplr*_max, so the center-facing
    #     (inner) boundary of each coupler is:
    #       west  arm (cplr0): epr_cplr0_max.x  (less negative — closer to origin)
    #       north arm (cplr1): epr_cplr1_min.y  (less positive — closer to origin)
    #       east  arm (cplr2): epr_cplr2_min.x  (less positive — closer to origin)
    #     The ideal coordinate is clamped to stay on the center-side of that boundary:
    #       west arm  (negative x): cut_x = max(ideal_x, epr_cplr0_max.x)
    #       north arm (positive y): cut_y = min(ideal_y, epr_cplr1_min.y)
    #       east arm  (positive x): cut_x = min(ideal_x, epr_cplr2_min.x)
    #
    #   half_cut_length = 30 µm + half the arm gap dimension, extending 30 µm into
    #   ground metal on each side. Each arm uses its own half_cut_length so coupler
    #   cuts are correct even when arms have different gap dimensions.
    #   Cuts are allowed to overlap — not a problem.

    # --- crossleft (West arm) ---
    # Vertical cut. Inner gap corners: epr_cross_09 (top) and epr_cross_06 (bottom).
    # epr_cross_09 = (-wn-sn, +ww+sw)  — inner top corner of west arm gap
    # epr_cross_06 = (-ws-ss, -ww-sw)  — inner bottom corner of west arm gap
    cross_corner_left_top = simulation.refpoints["epr_cross_09"]
    cross_corner_left_bot = simulation.refpoints["epr_cross_06"]
    cross_corner_left_h = (cross_corner_left_top.y - cross_corner_left_bot.y) / 2  # half-height of arm gap

    # Step 1: ideal cut x = midpoint between inner edge and origin.
    # inner_x_left is negative; origin is 0 → ideal is inner_x_left / 2.
    inner_x_left = cross_corner_left_top.x
    ideal_x_left = inner_x_left / 2

    # Step 2: clamp — epr_cplr0_max.x is the right (center-facing) edge of the west
    # coupler (less negative, closer to origin). max() keeps the cut >= that boundary.
    if float(simulation.cpl_length[0]) > 0:
        cut_x_left = max(ideal_x_left, simulation.refpoints["epr_cplr0_max"].x)
    else:
        cut_x_left = ideal_x_left

    cross_xsection_center_left = pya.DPoint(
        cut_x_left,
        cross_corner_left_top.y - cross_corner_left_h,
    )
    half_cut_length_left = 30.0 + cross_corner_left_h

    result = {
        f"{prefix}crossleftmer": {
            "p1": cross_xsection_center_left + pya.DPoint(0, -half_cut_length_left),
            "p2": cross_xsection_center_left + pya.DPoint(0,  half_cut_length_left),
        }
    }

    # --- crosstop (North arm) ---
    # Horizontal cut. Inner gap corners: epr_cross_09 (left) and epr_cross_00 (right).
    # epr_cross_09 = (-wn-sn, +ww+sw)  — inner bottom-left corner of north arm gap
    # epr_cross_00 = (+wn+sn, +we+se)  — inner bottom-right corner of north arm gap
    cross_corner_top_l = simulation.refpoints["epr_cross_09"]
    cross_corner_top_r = simulation.refpoints["epr_cross_00"]
    cross_corner_top_w = (cross_corner_top_r.x - cross_corner_top_l.x) / 2  # half-width of arm gap

    # Step 1: ideal cut y = midpoint between inner edge and origin.
    # inner_y_top is positive; ideal is inner_y_top / 2.
    inner_y_top = cross_corner_top_l.y
    ideal_y_top = inner_y_top / 2

    # Step 2: clamp — epr_cplr1_min.y is the bottom (center-facing) edge of the north
    # coupler (less positive, closer to origin). min() keeps the cut <= that boundary.
    if float(simulation.cpl_length[1]) > 0:
        cut_y_top = min(ideal_y_top, simulation.refpoints["epr_cplr1_min"].y)
    else:
        cut_y_top = ideal_y_top

    cross_xsection_center_top = pya.DPoint(
        cross_corner_top_l.x + cross_corner_top_w,
        cut_y_top,
    )
    half_cut_length_top = 30.0 + cross_corner_top_w

    result[f"{prefix}crosstopmer"] = {
        "p1": cross_xsection_center_top + pya.DPoint(-half_cut_length_top, 0),
        "p2": cross_xsection_center_top + pya.DPoint( half_cut_length_top, 0),
    }

    # --- crossright (East arm) ---
    # Vertical cut — mirror of crossleftmer on the east side.
    # epr_cross_00 = (+wn+sn, +we+se)  — inner top corner of east arm gap
    # epr_cross_03 = (+ws+ss, -we-se)  — inner bottom corner of east arm gap
    cross_corner_right_top = simulation.refpoints["epr_cross_00"]
    cross_corner_right_bot = simulation.refpoints["epr_cross_03"]
    cross_corner_right_h = (cross_corner_right_top.y - cross_corner_right_bot.y) / 2  # half-height of arm gap

    # Step 1: ideal cut x = midpoint between inner edge and origin.
    # inner_x_right is positive; ideal is inner_x_right / 2.
    inner_x_right = cross_corner_right_top.x
    ideal_x_right = inner_x_right / 2

    # Step 2: clamp — epr_cplr2_min.x is the left (center-facing) edge of the east
    # coupler (less positive, closer to origin). min() keeps the cut <= that boundary.
    if float(simulation.cpl_length[2]) > 0:
        cut_x_right = min(ideal_x_right, simulation.refpoints["epr_cplr2_min"].x)
    else:
        cut_x_right = ideal_x_right

    cross_xsection_center_right = pya.DPoint(
        cut_x_right,
        cross_corner_right_top.y - cross_corner_right_h,
    )
    half_cut_length_right = 30.0 + cross_corner_right_h

    result[f"{prefix}crossrightmer"] = {
        "p1": cross_xsection_center_right + pya.DPoint(0, -half_cut_length_right),
        "p2": cross_xsection_center_right + pya.DPoint(0,  half_cut_length_right),
    }

    # --- crossbottom (South arm) ---
    # Horizontal cut — mirror of crosstopmer on the south side.
    # No coupler on south arm; cut is always the ideal midpoint (no clamp needed).
    # epr_cross_03 = (+ws+ss, -we-se)  — inner top-right corner of south arm gap
    # epr_cross_06 = (-ws-ss, -ww-sw)  — inner top-left corner of south arm gap
    cross_corner_bot_r = simulation.refpoints["epr_cross_03"]
    cross_corner_bot_l = simulation.refpoints["epr_cross_06"]
    cross_corner_bot_w = (cross_corner_bot_r.x - cross_corner_bot_l.x) / 2  # half-width of arm gap

    # Step 1: ideal cut y = midpoint between inner edge and origin.
    # inner_y_bot is negative; ideal is inner_y_bot / 2.
    inner_y_bot = cross_corner_bot_r.y
    cut_y_bot = inner_y_bot / 2  # no coupler on south arm — no clamp needed

    cross_xsection_center_bot = pya.DPoint(
        cross_corner_bot_l.x + cross_corner_bot_w,
        cut_y_bot,
    )
    half_cut_length_bot = 30.0 + cross_corner_bot_w

    result[f"{prefix}crossbottommer"] = {
        "p1": cross_xsection_center_bot + pya.DPoint(-half_cut_length_bot, 0),
        "p2": cross_xsection_center_bot + pya.DPoint( half_cut_length_bot, 0),
    }

    # --- coupler correction cuts ---
    # Each cut uses the half_cut_length of its own arm so that cuts remain correct
    # even when arms have different gap dimensions.
    if float(simulation.cpl_length[0]) > 0:
        half_gap = float(simulation.cpl_b[0]) / 2
        xsection_point = float(simulation.cpl_gap[0]) / 2 + float(simulation.cpl_width[0]) / 2

        result[f"{prefix}0cplrmer"] = {
            "p1": simulation.refpoints["port_cplr0"]
            + pya.DPoint(-half_cut_length_left + half_gap, xsection_point),
            "p2": simulation.refpoints["port_cplr0"]
            + pya.DPoint( half_cut_length_left + half_gap, xsection_point),
        }

    if float(simulation.cpl_length[1]) > 0:
        half_gap = float(simulation.cpl_b[1]) / 2
        xsection_point = float(simulation.cpl_gap[1]) / 2 + float(simulation.cpl_width[1]) / 2

        result[f"{prefix}1cplrmer"] = {
            "p1": simulation.refpoints["port_cplr1"]
            + pya.DPoint( xsection_point,  half_cut_length_top - half_gap),
            "p2": simulation.refpoints["port_cplr1"]
            + pya.DPoint( xsection_point, -half_cut_length_top - half_gap),
        }

    if float(simulation.cpl_length[2]) > 0:
        half_gap = float(simulation.cpl_b[2]) / 2
        xsection_point = float(simulation.cpl_gap[2]) / 2 + float(simulation.cpl_width[2]) / 2

        result[f"{prefix}2cplrmer"] = {
            "p1": simulation.refpoints["port_cplr2"]
            + pya.DPoint(-half_cut_length_right - half_gap, xsection_point),
            "p2": simulation.refpoints["port_cplr2"]
            + pya.DPoint( half_cut_length_right - half_gap, xsection_point),
        }

    return result


def extract_swissmon_from(
    simulation: EPRTarget,
    refpoint_prefix: str,
    parameter_remap_function: Callable[[EPRTarget, str], any],
):
    return extract_child_simulation(
        simulation,
        refpoint_prefix,
        parameter_remap_function,
        [
            "b",
            "cpl_b",
            "gap_width",
            "face_ids",  # Accesses list's index 0
            "island_r",
            "cpl_gap",  # Accesses list's indices 0, 1, 2
            "cpl_width",  # Accesses list's indices 0, 1, 2
            "cpl_length",  # Accesses list's indices 0, 1, 2
        ],
    )
