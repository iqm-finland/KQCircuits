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

import logging
from typing import Callable

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.epr.util import (
    extract_child_simulation,
    EPRTarget,
    create_bulk_and_mer_partition_regions,
)
from kqcircuits.simulations.partition_region import PartitionRegion


# Partition region and correction cuts definitions for Swissmon qubit


def partition_regions(simulation: EPRTarget, prefix: str = "") -> list[PartitionRegion]:
    metal_edge_dimension = 4.0
    metal_edge_margin = pya.DPoint(metal_edge_dimension, metal_edge_dimension)

    result = []
    base = simulation.refpoints["base"]
    sized = metal_edge_dimension + simulation.island_r

    for arm_name, indices in [
        ("crossleft", [6, 7, 8, 9]),
        ("crosstop", [9, 10, 11, 0]),
        ("crossright", [0, 1, 2, 3]),
        ("crossbottom", [3, 4, 5, 6]),
    ]:
        # Build polygon from epr_cross_* refpoints only (without base), size it,
        # then reconstruct adding base unsized so the four arm polygons meet at center
        # without overlapping each other.
        arm_points_poly = pya.DPolygon(
            [simulation.refpoints[f"epr_cross_{i:02d}"] for i in indices]
        )
        sized_poly = arm_points_poly.sized(sized)
        hull_points = [sized_poly.point_hull(i) for i in range(sized_poly.num_points_hull())]
        arm_poly = pya.DPolygon(hull_points + [base])

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
    half_gap = float(simulation.gap_width[1]) / 2

    if len(set(simulation.gap_width)) > 1:
        logging.warning("Partition regions for Swissmon with varying gaps are not implemented")
        logging.warning(
            "Using correction with %s gap for all arms with gap widths %s",
            str(2 * half_gap),
            str(simulation.gap_width),
        )

    # --- crossleft (West arm) ---
    # Vertical cut placed between the cross body and the west coupler (or arm tip if no coupler).
    # Runs from ground metal below the arm, through the arm gap+metal, back to ground above.
    # Refpoints for west arm gap: 06=(-sw-ws, -ww-sw), 07=(-l0-sw, -ww-sw),
    #                              08=(-l0-sw, +ww+sw), 09=(-wn-sn, +ww+sw)
    cross_corner = simulation.refpoints["epr_cross_09"]  # inner top corner of west arm gap
    cross_corner_h = (cross_corner.y - simulation.refpoints["epr_cross_06"].y) / 2  # half-height of arm gap

    coupler_corner = (
        simulation.refpoints["epr_cplr0_max"]
        if float(simulation.cpl_length[0]) > 0
        else simulation.refpoints["epr_cross_08"]
    )

    # x: midpoint between inner gap edge and coupler/arm-tip; y: vertical center of arm (y=0)
    cross_xsection_center = pya.DPoint(
        (cross_corner.x + coupler_corner.x) / 2,
        cross_corner.y - cross_corner_h,
    )

    half_cut_length = 30.0 + cross_corner_h

    result = {
        f"{prefix}crossleftmer": {
            "p1": cross_xsection_center + pya.DPoint(0, -half_cut_length),
            "p2": cross_xsection_center + pya.DPoint(0, half_cut_length),
        }
    }

    # --- crosstop (North arm) ---
    # Horizontal cut placed between the cross body and the north coupler (or arm tip if no coupler).
    # Runs from ground metal left of arm, through arm gap+metal, back to ground on right.
    # Refpoints for north arm gap: 09=(-wn-sn, +ww+sw), 10=(-wn-sn, +l1+sn),
    #                               11=(+wn+sn, +l1+sn), 00=(+wn+sn, +ww+sw)
    cross_corner_top_l = simulation.refpoints["epr_cross_09"]  # inner bottom-left of north arm gap
    cross_corner_top_r = simulation.refpoints["epr_cross_00"]  # inner bottom-right of north arm gap
    cross_corner_top_w = (cross_corner_top_r.x - cross_corner_top_l.x) / 2  # half-width of arm gap

    coupler_corner_top = (
        simulation.refpoints["epr_cplr1_max"]
        if float(simulation.cpl_length[1]) > 0
        else simulation.refpoints["epr_cross_10"]
    )

    # x: horizontal center of arm; y: midpoint between inner gap edge and coupler/arm-tip
    cross_xsection_center_top = pya.DPoint(
        cross_corner_top_l.x + cross_corner_top_w,
        (cross_corner_top_l.y + coupler_corner_top.y) / 2,
    )

    half_cut_length_top = 30.0 + cross_corner_top_w

    result[f"{prefix}crosstopmer"] = {
        "p1": cross_xsection_center_top + pya.DPoint(-half_cut_length_top, 0),
        "p2": cross_xsection_center_top + pya.DPoint(half_cut_length_top, 0),
    }

    # --- crossright (East arm) ---
    # Vertical cut placed between the cross body and the east coupler (or arm tip if no coupler).
    # Runs from ground metal below the arm, through arm gap+metal, back to ground above.
    # Mirror of crossleftmer on the east side.
    # Refpoints for east arm gap: 00=(+wn+sn, +we+se), 01=(+l2+se, +we+se),
    #                              02=(+l2+se, -we-se), 03=(+ws+ss, -we-se)
    cross_corner_right_top = simulation.refpoints["epr_cross_00"]  # inner top-left of east arm gap
    cross_corner_right_bot = simulation.refpoints["epr_cross_03"]  # inner bottom-left of east arm gap
    cross_corner_right_h = (cross_corner_right_top.y - cross_corner_right_bot.y) / 2  # half-height of arm gap

    coupler_corner_right = (
        simulation.refpoints["epr_cplr2_max"]
        if float(simulation.cpl_length[2]) > 0
        else simulation.refpoints["epr_cross_01"]
    )

    # x: midpoint between inner gap edge and coupler/arm-tip; y: vertical center of arm (y=0)
    cross_xsection_center_right = pya.DPoint(
        (cross_corner_right_top.x + coupler_corner_right.x) / 2,
        cross_corner_right_top.y - cross_corner_right_h,
    )

    half_cut_length_right = 30.0 + cross_corner_right_h

    result[f"{prefix}crossrightmer"] = {
        "p1": cross_xsection_center_right + pya.DPoint(0, -half_cut_length_right),
        "p2": cross_xsection_center_right + pya.DPoint(0, half_cut_length_right),
    }

    # --- crossbottom (South arm) ---
    # Horizontal cut placed between the cross body and the south arm tip (no coupler on south arm).
    # Runs from ground metal left of arm, through arm gap+metal, back to ground on right.
    # Mirror of crosstopmer on the south side.
    # Refpoints for south arm gap: 03=(+ws+ss, -we-se), 04=(+ws+ss, -l3-ss),
    #                               05=(-ws-ss, -l3-ss), 06=(-ws-ss, -ww-sw)
    cross_corner_bot_r = simulation.refpoints["epr_cross_03"]  # inner top-right of south arm gap
    cross_corner_bot_l = simulation.refpoints["epr_cross_06"]  # inner top-left of south arm gap
    cross_corner_bot_w = (cross_corner_bot_r.x - cross_corner_bot_l.x) / 2  # half-width of arm gap

    # x: horizontal center of arm; y: midpoint between inner gap edge and arm tip
    cross_xsection_center_bot = pya.DPoint(
        cross_corner_bot_l.x + cross_corner_bot_w,
        (cross_corner_bot_l.y + simulation.refpoints["epr_cross_04"].y) / 2,
    )

    half_cut_length_bot = 30.0 + cross_corner_bot_w

    result[f"{prefix}crossbottommer"] = {
        "p1": cross_xsection_center_bot + pya.DPoint(-half_cut_length_bot, 0),
        "p2": cross_xsection_center_bot + pya.DPoint(half_cut_length_bot, 0),
    }

    if float(simulation.cpl_length[0]) > 0:
        half_gap = float(simulation.cpl_b[0]) / 2
        xsection_point = float(simulation.cpl_gap[0]) / 2 + float(simulation.cpl_width[0]) / 2

        result[f"{prefix}0cplrmer"] = {
            "p1": simulation.refpoints["port_cplr0"]
            + pya.DPoint(-half_cut_length + half_gap, xsection_point),
            "p2": simulation.refpoints["port_cplr0"]
            + pya.DPoint(half_cut_length + half_gap, xsection_point),
        }

    if float(simulation.cpl_length[1]) > 0:
        half_gap = float(simulation.cpl_b[1]) / 2
        xsection_point = float(simulation.cpl_gap[1]) / 2 + float(simulation.cpl_width[1]) / 2

        result[f"{prefix}1cplrmer"] = {
            "p1": simulation.refpoints["port_cplr1"]
            + pya.DPoint(xsection_point, half_cut_length - half_gap),
            "p2": simulation.refpoints["port_cplr1"]
            + pya.DPoint(xsection_point, -half_cut_length - half_gap),
        }

    if float(simulation.cpl_length[2]) > 0:
        half_gap = float(simulation.cpl_b[2]) / 2
        xsection_point = float(simulation.cpl_gap[2]) / 2 + float(simulation.cpl_width[2]) / 2

        result[f"{prefix}2cplrmer"] = {
            "p1": simulation.refpoints["port_cplr2"]
            + pya.DPoint(-half_cut_length - half_gap, xsection_point),
            "p2": simulation.refpoints["port_cplr2"]
            + pya.DPoint(half_cut_length - half_gap, xsection_point),
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
