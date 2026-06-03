# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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
from kqcircuits.simulations.epr.util import extract_child_simulation, EPRTarget, create_bulk_and_mer_partition_regions
from kqcircuits.simulations.partition_region import PartitionRegion


# Partition region and correction cuts definitions for Swissmon qubit


def partition_regions(simulation: EPRTarget, prefix: str = "") -> list[PartitionRegion]:
    metal_edge_dimension = 4.0
    metal_edge_margin = pya.DPoint(metal_edge_dimension, metal_edge_dimension)

    # Center of the cross — used as the shared terminating vertex for each quadrant polygon.
    base = pya.DPoint(0, 0)

    # The epr_cross_XX refpoints trace the outer gap boundary of the cross clockwise starting
    # from the NE corner of the north arm:
    #   00: NE corner north arm      (top-right of N arm gap)
    #   01: NE corner east side      (top-right end of E arm gap)
    #   02: SE corner east side      (bottom-right end of E arm gap)
    #   03: SE corner south side     (bottom-right of S arm gap)
    #   04: SW corner south side     (bottom-left of S arm gap)
    #   05: SW corner west side      (bottom-left end of W arm gap)
    #   06: NW corner west side      (top-left end of W arm gap)
    #   07: NW corner north side     (top-left of N arm gap)
    #   08: NW corner outer N arm    (outer-left of N arm tip)
    #   09: NE corner outer N arm    (outer-right of N arm tip — same y as 08)
    #  (indices wrap; the polygon is closed )
    #
    # design stores exactly 12 points (indices 00–11):
    #   00 = (+wn+sn,  +we+se)   NE inner corner of N arm
    #   01 = (+l2+se,  +we+se)   NE outer corner of E arm
    #   02 = (+l2+se,  -we-se)   SE outer corner of E arm
    #   03 = (+ws+ss,  -we-se)   SE inner corner of S arm
    #   04 = (+ws+ss,  -l3-ss)   SW outer corner of S arm  (sign differs — it is really the bottom-right)
    #   05 = (-ws-ss,  -l3-ss)   bottom-left corner of S arm
    #   06 = (-ws-ss,  -ww-sw)   NW inner corner of W arm (below axis)
    #   07 = (-l0-sw,  -ww-sw)   NW outer corner of W arm (below axis)
    #   08 = (-l0-sw,  +ww+sw)   SW outer corner of W arm (above axis)
    #   09 = (-wn-sn,  +ww+sw)   SW inner corner of W arm (above axis)
    #   10 = (-wn-sn,  +l1+sn)   NW outer corner of N arm
    #   11 = (+wn+sn,  +l1+sn)   NE outer corner of N arm

    rp = simulation.refpoints  # shorthand


    # crossleft  — west arm: refpoints 06, 07, 08, 09, base
    crossleft_poly = pya.DPolygon([
        rp["epr_cross_06"],
        rp["epr_cross_07"],
        rp["epr_cross_08"],
        rp["epr_cross_09"],
        base,
    ]).sized(metal_edge_dimension + simulation.island_r)
    result = create_bulk_and_mer_partition_regions(
        name=f"{prefix}crossleft",
        face=simulation.face_ids[0],
        metal_edge_dimensions=metal_edge_dimension,
        region=crossleft_poly,
        vertical_dimensions=3.0,
        visualise=True,
    )

    
    # crosstop  — north arm: refpoints 09, 10, 11, 00, base
    crosstop_poly = pya.DPolygon([
        rp["epr_cross_09"],
        rp["epr_cross_10"],
        rp["epr_cross_11"],
        rp["epr_cross_00"],
        base,
    ]).sized(metal_edge_dimension + simulation.island_r)
    result += create_bulk_and_mer_partition_regions(
        name=f"{prefix}crosstop",
        face=simulation.face_ids[0],
        metal_edge_dimensions=metal_edge_dimension,
        region=crosstop_poly,
        vertical_dimensions=3.0,
        visualise=True,
    )

    
    # crossright  — east arm: refpoints 00, 01, 02, 03, base
    crossright_poly = pya.DPolygon([
        rp["epr_cross_00"],
        rp["epr_cross_01"],
        rp["epr_cross_02"],
        rp["epr_cross_03"],
        base,
    ]).sized(metal_edge_dimension + simulation.island_r)
    result += create_bulk_and_mer_partition_regions(
        name=f"{prefix}crossright",
        face=simulation.face_ids[0],
        metal_edge_dimensions=metal_edge_dimension,
        region=crossright_poly,
        vertical_dimensions=3.0,
        visualise=True,
    )

    # crossbottom  — south arm: refpoints 03, 04, 05, 06, base
    crossbottom_poly = pya.DPolygon([
        rp["epr_cross_03"],
        rp["epr_cross_04"],
        rp["epr_cross_05"],
        rp["epr_cross_06"],
        base,
    ]).sized(metal_edge_dimension + simulation.island_r)
    result += create_bulk_and_mer_partition_regions(
        name=f"{prefix}crossbottom",
        face=simulation.face_ids[0],
        metal_edge_dimensions=metal_edge_dimension,
        region=crossbottom_poly,
        vertical_dimensions=3.0,
        visualise=True,
    )

    
    # Coupler partition regions — extend to include any attached waveguide
    # Coupler indices: 0 = west (R90), 1 = north (R0), 2 = east (R270)
    # For each coupler we grow the bounding box of its gap shape by
    # metal_edge_margin on all sides, then additionally extend it along the
    # direction the attached waveguide travels so that the waveguide fits
    # inside the partition region with 25 µm of clearance at the far end.
    waveguide_length = getattr(simulation, "waveguide_length", 0)
    wg_room = 25.0  # extra clearance beyond the waveguide end

    for idx in range(3):
        if float(simulation.cpl_length[idx]) <= 0:
            continue

        p_min = rp[f"epr_cplr{idx}_min"] - metal_edge_margin
        p_max = rp[f"epr_cplr{idx}_max"] + metal_edge_margin

        # Extend the region in the direction the waveguide exits the coupler.
        # Coupler 0 (west): waveguide exits to the left  → shrink x_min
        # Coupler 1 (north): waveguide exits upward       → grow  y_max
        # Coupler 2 (east): waveguide exits to the right  → grow  x_max
        extension = float(waveguide_length) + wg_room
        if idx == 0:
            p_min = pya.DPoint(p_min.x - extension, p_min.y)
        elif idx == 1:
            p_max = pya.DPoint(p_max.x, p_max.y + extension)
        elif idx == 2:
            p_max = pya.DPoint(p_max.x + extension, p_max.y)

        cplr_region = pya.DBox(p_min, p_max)
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
    rp = simulation.refpoints  # shorthand

    result = {}

    
    # crossleft correction cut  (west arm, original cross cut — kept as-is)
    # The cut is placed horizontally across the metal-edge region of the west
    # arm, centred between the arm tip (epr_cross_07/08) and the nearest
    # coupler or cross corner on the east side.
    cross_corner = rp["epr_cross_09"]        # inner top corner of west arm (above axis)
    cross_corner_h = (cross_corner.y - rp["epr_cross_06"].y) / 2  # half the arm height
    coupler_corner = (
        rp["epr_cplr0_max"]
        if float(simulation.cpl_length[0]) > 0
        else rp["epr_cross_08"]
    )
    cross_xsection_center = pya.DPoint(
        (cross_corner.x + coupler_corner.x) / 2,
        cross_corner.y - cross_corner_h,
    )
    half_cut_length = 30.0 + cross_corner_h
    result[f"{prefix}crossleftmer"] = {
        "p1": cross_xsection_center + pya.DPoint(0, -half_cut_length),
        "p2": cross_xsection_center + pya.DPoint(0, half_cut_length),
    }

    
    # crosstop correction cut  (north arm)
    # : the north arm extends upward (positive y).
    # epr_cross_10 and 11 are the outer corners of the north arm tip.
    # The cut is vertical (along x), centred between the arm tip and the
    # nearest coupler / cross corner below.
    north_outer_left = rp["epr_cross_10"]    # (-wn-sn, +l1+sn)
    north_outer_right = rp["epr_cross_11"]   # (+wn+sn, +l1+sn)
    north_arm_half_width = (north_outer_right.x - north_outer_left.x) / 2
    north_coupler_corner = (
        rp["epr_cplr1_max"]
        if float(simulation.cpl_length[1]) > 0
        else rp["epr_cross_11"]
    )
    # y-centre: midway between the inner base of the arm (at y≈0) and the
    # outer tip.  
    north_tip_y = north_outer_left.y
    # The "inner edge" of the north arm relative to the cross body is at y ≈
    # ww+sw (the shoulder). approximate via the epr_cross_09 y value.
    north_inner_y = rp["epr_cross_09"].y
    north_xsection_y = (north_tip_y + north_inner_y) / 2
    half_cut_length_top = 30.0 + north_arm_half_width
    result[f"{prefix}crosstopmer"] = {
        "p1": pya.DPoint(-half_cut_length_top, north_xsection_y),
        "p2": pya.DPoint( half_cut_length_top, north_xsection_y),
    }

    
    # crossright correction cut  (east arm)
    east_outer_top = rp["epr_cross_01"]      # (+l2+se,  +we+se)
    east_outer_bot = rp["epr_cross_02"]      # (+l2+se,  -we-se)
    east_arm_half_height = (east_outer_top.y - east_outer_bot.y) / 2
    east_inner_x = rp["epr_cross_00"].x      # inner x of east arm at top shoulder
    east_tip_x = east_outer_top.x
    east_xsection_x = (east_tip_x + east_inner_x) / 2
    half_cut_length_right = 30.0 + east_arm_half_height
    result[f"{prefix}crossrightmer"] = {
        "p1": pya.DPoint(east_xsection_x, -half_cut_length_right),
        "p2": pya.DPoint(east_xsection_x,  half_cut_length_right),
    }

    
    # crossbottom correction cut  
    south_outer_right = rp["epr_cross_04"]   # (+ws+ss, -l3-ss)
    south_outer_left  = rp["epr_cross_05"]   # (-ws-ss, -l3-ss)
    south_arm_half_width = (south_outer_right.x - south_outer_left.x) / 2
    south_tip_y  = south_outer_left.y         # most negative y
    south_inner_y = rp["epr_cross_06"].y      # inner shoulder y
    south_xsection_y = (south_tip_y + south_inner_y) / 2
    half_cut_length_bot = 30.0 + south_arm_half_width
    result[f"{prefix}crossbottommer"] = {
        "p1": pya.DPoint(-half_cut_length_bot, south_xsection_y),
        "p2": pya.DPoint( half_cut_length_bot, south_xsection_y),
    }

    # Coupler correction cuts  
    if float(simulation.cpl_length[0]) > 0:
        half_gap = float(simulation.cpl_b[0]) / 2
        xsection_point = float(simulation.cpl_gap[0]) / 2 + float(simulation.cpl_width[0]) / 2
        result[f"{prefix}0cplrmer"] = {
            "p1": rp["port_cplr0"] + pya.DPoint(-30.0 + half_gap, xsection_point),
            "p2": rp["port_cplr0"] + pya.DPoint( 30.0 + half_gap, xsection_point),
        }
    if float(simulation.cpl_length[1]) > 0:
        half_gap = float(simulation.cpl_b[1]) / 2
        xsection_point = float(simulation.cpl_gap[1]) / 2 + float(simulation.cpl_width[1]) / 2
        result[f"{prefix}1cplrmer"] = {
            "p1": rp["port_cplr1"] + pya.DPoint( xsection_point,  30.0 - half_gap),
            "p2": rp["port_cplr1"] + pya.DPoint( xsection_point, -30.0 - half_gap),
        }
    if float(simulation.cpl_length[2]) > 0:
        half_gap = float(simulation.cpl_b[2]) / 2
        xsection_point = float(simulation.cpl_gap[2]) / 2 + float(simulation.cpl_width[2]) / 2
        result[f"{prefix}2cplrmer"] = {
            "p1": rp["port_cplr2"] + pya.DPoint(-30.0 - half_gap, xsection_point),
            "p2": rp["port_cplr2"] + pya.DPoint( 30.0 - half_gap, xsection_point),
        }

    return result


def extract_swissmon_from(
    simulation: EPRTarget, refpoint_prefix: str, parameter_remap_function: Callable[[EPRTarget, str], any]
):
    return extract_child_simulation(
        simulation,
        refpoint_prefix,
        parameter_remap_function,
        [
            "b",
            "gap_width",
            "face_ids",       # Accesses list's index 0
            "island_r",
            "cpl_b",          # Accesses list's indices 0, 1, 2 (per-coupler gap-to-ground)
            "cpl_gap",        # Accesses list's indices 0, 1, 2
            "cpl_width",      # Accesses list's indices 0, 1, 2
            "cpl_length",     # Accesses list's indices 0, 1, 2
        ],
    )
