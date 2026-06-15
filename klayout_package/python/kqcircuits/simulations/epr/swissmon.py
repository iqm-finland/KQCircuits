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


def partition_regions(simulation: EPRTarget, prefix: str = "") -> list[PartitionRegion]:

    def _offset_point_away(p: pya.DPoint, sized: float, origin: pya.DPoint) -> pya.DPoint:
        """Offset a point *away* from the origin by `sized` on each axis."""
        dx = math.copysign(sized, p.x - origin.x)
        dy = math.copysign(sized, p.y - origin.y)
        return pya.DPoint(p.x + dx, p.y + dy)

    def _get_coupler_wg_offset(i, s):
        wg_len = float(simulation.waveguide_length) if hasattr(simulation, "waveguide_length") else 0
        offset = wg_len + 25
        coupler_wg_offsets = [
            {"min": pya.DPoint(-offset, 0)},
            {"max": pya.DPoint(0, offset)},
            {"max": pya.DPoint(offset, 0)},
        ]
        return coupler_wg_offsets[i].get(s, pya.DPoint(0, 0))

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


def _swissmon_cross_cut(
    simulation: EPRTarget,
    corner_index_a: int,
    corner_index_b: int,
    coupler_refpoint: str,
    axis: str,
) -> dict[str, pya.DPoint]:
    """Return a correction-cut ``{"p1": ..., "p2": ...}`` dict for one Swissmon cross arm.

    The cut is placed at the midpoint between the inner gap edge and the coupler (or arm-tip)
    inner face, and extends by ``30 + half_arm_width`` on each side.

    Args:
        simulation:       EPR simulation target carrying ``refpoints``.
        corner_index_a:   First ``epr_cross_NN`` index defining one inner gap corner.
        corner_index_b:   Second ``epr_cross_NN`` index defining the opposite inner gap corner.
        coupler_refpoint: Name of the refpoint used as the coupler inner face
                          (e.g. ``"epr_cplr1_min"`` or a fallback ``"epr_cross_10"``).
        axis:             ``"x"`` for a vertical cut (left/right arms),
                          ``"y"`` for a horizontal cut (top/bottom arms).

    Returns:
        Dict with keys ``"p1"`` and ``"p2"`` as ``pya.DPoint`` values.
    """
    pa = simulation.refpoints[f"epr_cross_{corner_index_a:02d}"]
    pb = simulation.refpoints[f"epr_cross_{corner_index_b:02d}"]
    coupler_pt = simulation.refpoints[coupler_refpoint]

    if axis == "x":
        # Vertical cut: half-width measured along y, center x between gap edge and coupler
        half_width = (pa.y - pb.y) / 2
        center = pya.DPoint(
            (pa.x + coupler_pt.x) / 2,
            pb.y + half_width,
        )
        half_len = 30.0 + half_width
        return {
            "p1": center + pya.DPoint(0, -half_len),
            "p2": center + pya.DPoint(0,  half_len),
        }
    else:
        # Horizontal cut: half-width measured along x, center y between gap edge and coupler
        half_width = (pb.x - pa.x) / 2
        center = pya.DPoint(
            pa.x + half_width,
            (pa.y + coupler_pt.y) / 2,
        )
        half_len = 30.0 + half_width
        return {
            "p1": center + pya.DPoint(-half_len, 0),
            "p2": center + pya.DPoint( half_len, 0),
        }


def correction_cuts(simulation: EPRTarget, prefix: str = "") -> dict[str, dict]:
    # --- crossleft (West arm) ---
    # Vertical cut. Inner gap corners: epr_cross_06 (bottom), epr_cross_09 (top).
    coupler_left = (
        "epr_cplr0_max"
        if float(simulation.cpl_length[0]) > 0
        else "epr_cross_08"
    )
    result = {
        f"{prefix}crossleftmer": _swissmon_cross_cut(simulation, 9, 6, coupler_left, axis="x"),
    }

    # --- crosstop (North arm) ---
    # Horizontal cut. Inner gap corners: epr_cross_09 (left), epr_cross_00 (right).
    coupler_top = (
        "epr_cplr1_min"
        if float(simulation.cpl_length[1]) > 0
        else "epr_cross_10"
    )
    result[f"{prefix}crosstopmer"] = _swissmon_cross_cut(simulation, 9, 0, coupler_top, axis="y")

    # --- crossright (East arm) ---
    # Vertical cut. Inner gap corners: epr_cross_00 (top), epr_cross_03 (bottom).
    coupler_right = (
        f"epr_cplr2_min"
        if float(simulation.cpl_length[2]) > 0
        else "epr_cross_01"
    )
    result[f"{prefix}crossrightmer"] = _swissmon_cross_cut(simulation, 0, 3, coupler_right, axis="x")

    # --- crossbottom (South arm) ---
    # Horizontal cut. Inner gap corners: epr_cross_03 (right), epr_cross_06 (left).
    # No coupler on south arm — use arm tip refpoint epr_cross_04.
    result[f"{prefix}crossbottommer"] = _swissmon_cross_cut(simulation, 6, 3, "epr_cross_04", axis="y")

    # --- coupler correction cuts ---
    if float(simulation.cpl_length[0]) > 0:
        half_gap = float(simulation.cpl_b[0]) / 2
        xsection_point = float(simulation.cpl_gap[0]) / 2 + float(simulation.cpl_width[0]) / 2
        half_cut_length_left = 30.0 + (
            simulation.refpoints["epr_cross_09"].y - simulation.refpoints["epr_cross_06"].y
        ) / 2
        result[f"{prefix}0cplrmer"] = {
            "p1": simulation.refpoints["port_cplr0"]
            + pya.DPoint(-half_cut_length_left + half_gap, xsection_point),
            "p2": simulation.refpoints["port_cplr0"]
            + pya.DPoint( half_cut_length_left + half_gap, xsection_point),
        }

    if float(simulation.cpl_length[1]) > 0:
        half_gap = float(simulation.cpl_b[1]) / 2
        xsection_point = float(simulation.cpl_gap[1]) / 2 + float(simulation.cpl_width[1]) / 2
        half_cut_length_top = 30.0 + (
            simulation.refpoints["epr_cross_00"].x - simulation.refpoints["epr_cross_09"].x
        ) / 2
        result[f"{prefix}1cplrmer"] = {
            "p1": simulation.refpoints["port_cplr1"]
            + pya.DPoint( xsection_point,  half_cut_length_top - half_gap),
            "p2": simulation.refpoints["port_cplr1"]
            + pya.DPoint( xsection_point, -half_cut_length_top - half_gap),
        }

    if float(simulation.cpl_length[2]) > 0:
        half_gap = float(simulation.cpl_b[2]) / 2
        xsection_point = float(simulation.cpl_gap[2]) / 2 + float(simulation.cpl_width[2]) / 2
        half_cut_length_right = 30.0 + (
            simulation.refpoints["epr_cross_00"].y - simulation.refpoints["epr_cross_03"].y
        ) / 2
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
            "cpl_b",  # Accesses list's indices 0, 1, 2
            "gap_width",
            "face_ids",  # Accesses list's index 0
            "island_r",
            "cpl_gap",  # Accesses list's indices 0, 1, 2
            "cpl_width",  # Accesses list's indices 0, 1, 2
            "cpl_length",  # Accesses list's indices 0, 1, 2
        ],
    )
