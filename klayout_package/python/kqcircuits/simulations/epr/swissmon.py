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


def _offset_point_away(p: pya.DPoint, sized: float, origin: pya.DPoint) -> pya.DPoint:
    """Offset a point *away* from the origin by `sized` on each axis."""
    dx = math.copysign(sized, p.x - origin.x) if p.x != 0 else 0.0
    dy = math.copysign(sized, p.y - origin.y) if p.y != 0 else 0.0
    return pya.DPoint(p.x + dx, p.y + dy)


def _offset_point_toward(p: pya.DPoint, sized: float) -> pya.DPoint:
    """Offset a point *toward* the origin by `sized` on each axis."""
    dx = math.copysign(sized, p.x) if p.x != 0 else 0.0
    dy = math.copysign(sized, p.y) if p.y != 0 else 0.0
    return pya.DPoint(p.x - dx, p.y - dy)


def partition_regions(simulation: EPRTarget, prefix: str = "") -> list[PartitionRegion]:
    metal_edge_dimension = 4.0
    metal_edge_margin = pya.DPoint(metal_edge_dimension, metal_edge_dimension)

    result = []
    base = simulation.refpoints["base"]
    sized = metal_edge_dimension + simulation.island_r

    # Each arm polygon is a pentagon: 4 offset epr_cross_* points + base (origin).

    for arm_name, indices in [
        ("crossleft",   [6, 7, 8, 9]),
        ("crosstop",    [9, 10, 11, 0]),
        ("crossright",  [0, 1, 2, 3]),
        ("crossbottom", [3, 4, 5, 6]),
    ]:
        raw = [simulation.refpoints[f"epr_cross_{i:02d}"] for i in indices]

        arm_poly = pya.DPolygon([_offset_point_away(p, sized, base) for p in raw] + [base])

        result += create_bulk_and_mer_partition_regions(
            name=f"{prefix}{arm_name}",
            face=simulation.face_ids[0],
            metal_edge_dimensions=metal_edge_dimension,
            region=arm_poly,
            vertical_dimensions=3.0,
            visualise=True,
        )

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
    # Cuts for cross partition regions
    cross_corner = simulation.refpoints["epr_cross_09"]
    cross_corner_h = (cross_corner.y - simulation.refpoints["epr_cross_06"].y) / 2

    coupler_corner = (
        simulation.refpoints["epr_cplr0_max"]
        if float(simulation.cpl_length[0]) > 0
        else simulation.refpoints["epr_cross_08"]
    )
    # x = midpoint between inner gap edge (epr_cross_09.x) and coupler inner face
    cross_xsection_center_left = pya.DPoint(
        (cross_corner.x + coupler_corner.x) / 2,
        cross_corner.y - cross_corner_h,
    )
    half_cut_length_left = 30.0 + cross_corner_h

    result = {
        f"{prefix}crossleftmer": {
            "p1": cross_xsection_center_left + pya.DPoint(0, -half_cut_length_left),
            "p2": cross_xsection_center_left + pya.DPoint(0,  half_cut_length_left),
        }
    }

    # --- crosstop (North arm) ---
    # Horizontal cut. Inner gap corners: epr_cross_09 (left), epr_cross_00 (right).
    cross_corner_top_l = simulation.refpoints["epr_cross_09"]
    cross_corner_top_r = simulation.refpoints["epr_cross_00"]
    cross_corner_top_w = (cross_corner_top_r.x - cross_corner_top_l.x) / 2

    coupler_corner_top = (
        simulation.refpoints["epr_cplr1_min"]
        if float(simulation.cpl_length[1]) > 0
        else simulation.refpoints["epr_cross_10"]
    )
    # y = midpoint between inner gap edge (epr_cross_09.y) and coupler inner face
    cross_xsection_center_top = pya.DPoint(
        cross_corner_top_l.x + cross_corner_top_w,
        (cross_corner_top_l.y + coupler_corner_top.y) / 2,
    )
    half_cut_length_top = 30.0 + cross_corner_top_w

    result[f"{prefix}crosstopmer"] = {
        "p1": cross_xsection_center_top + pya.DPoint(-half_cut_length_top, 0),
        "p2": cross_xsection_center_top + pya.DPoint( half_cut_length_top, 0),
    }

    # --- crossright (East arm) ---
    # Vertical cut. Inner gap corners: epr_cross_00 (top), epr_cross_03 (bottom).
    cross_corner_right_top = simulation.refpoints["epr_cross_00"]
    cross_corner_right_bot = simulation.refpoints["epr_cross_03"]
    cross_corner_right_h = (cross_corner_right_top.y - cross_corner_right_bot.y) / 2

    coupler_corner_right = (
        simulation.refpoints["epr_cplr2_min"]
        if float(simulation.cpl_length[2]) > 0
        else simulation.refpoints["epr_cross_01"]
    )
    # x = midpoint between inner gap edge (epr_cross_00.x) and coupler inner face
    cross_xsection_center_right = pya.DPoint(
        (cross_corner_right_top.x + coupler_corner_right.x) / 2,
        cross_corner_right_top.y - cross_corner_right_h,
    )
    half_cut_length_right = 30.0 + cross_corner_right_h

    result[f"{prefix}crossrightmer"] = {
        "p1": cross_xsection_center_right + pya.DPoint(0, -half_cut_length_right),
        "p2": cross_xsection_center_right + pya.DPoint(0,  half_cut_length_right),
    }

    # --- crossbottom (South arm) ---
    # Horizontal cut. Inner gap corners: epr_cross_03 (right), epr_cross_06 (left).
    # No coupler on south arm — use arm tip refpoint epr_cross_04.
    cross_corner_bot_r = simulation.refpoints["epr_cross_03"]
    cross_corner_bot_l = simulation.refpoints["epr_cross_06"]
    cross_corner_bot_w = (cross_corner_bot_r.x - cross_corner_bot_l.x) / 2

    # y = midpoint between inner gap edge (epr_cross_03.y) and arm tip (epr_cross_04.y)
    cross_xsection_center_bot = pya.DPoint(
        cross_corner_bot_l.x + cross_corner_bot_w,
        (cross_corner_bot_l.y + simulation.refpoints["epr_cross_04"].y) / 2,
    )
    half_cut_length_bot = 30.0 + cross_corner_bot_w

    result[f"{prefix}crossbottommer"] = {
        "p1": cross_xsection_center_bot + pya.DPoint(-half_cut_length_bot, 0),
        "p2": cross_xsection_center_bot + pya.DPoint( half_cut_length_bot, 0),
    }

    # --- coupler correction cuts ---
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
            "face_ids",
            "island_r",
            "cpl_gap",
            "cpl_width",
            "cpl_length",
        ],
    )
