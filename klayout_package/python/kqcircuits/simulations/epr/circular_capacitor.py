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

import math
from typing import Callable
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.epr.utils import extract_child_simulation, in_gui, EPRTarget
from kqcircuits.simulations.partition_region import PartitionRegion
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.geometry_helper import arc_points
from kqcircuits.elements.finger_capacitor_square import eval_a2, eval_b2

# Partition region and correction cuts definitions for CircularCapacitor element


def _has_waveguides(simulation):
    """Determines if waveguide regions and cuts are added used"""
    if in_gui(simulation):
        return False
    return simulation.fixed_length > 0 or simulation.waveguide_length > 0 or not simulation.use_internal_ports


def _is_flip_chip(simulation):
    """Determines if the geometry consists of multiple substrate layers"""
    if in_gui(simulation):
        return True
    return len(simulation.face_stack) > int(simulation.lower_box_height > 0) + 1


def _waveguide_end_dist(simulation):
    """Distance from the center to the end of the waveguide"""
    if simulation.use_internal_ports:
        x_guide = simulation.waveguide_length + simulation.a + 1
        if simulation.fixed_length > 0:
            return x_guide + simulation.fixed_length / 2
        else:
            return x_guide + simulation.r_outer + simulation.ground_gap
    else:
        return simulation.box.width() / 2


def partition_regions(simulation: EPRTarget, prefix: str = "") -> list[PartitionRegion]:

    mer_x_dim = 3.0
    mer_y_dim = 2.0
    # Let's make the mer margin just a bit larger to prevent any artefacts
    region_safety_margin = 1.5  # um
    metal_edge_margin = mer_x_dim + region_safety_margin

    center = simulation.refpoints["base"]

    def _init_part_reg(name, region, mer=True, face=0, override_y_dim=mer_y_dim):
        if in_gui(simulation):
            face_id = simulation.face_ids[face]
        else:
            face_id = simulation.face_stack[face]
        return PartitionRegion(
            name=f"{prefix}{name}" + ("mer" if mer else "bulk"),
            face=face_id,
            metal_edge_dimensions=mer_x_dim if mer else None,
            region=region,
            vertical_dimensions=override_y_dim,
            visualise=True,
        )

    def _symmetric_sector(angle, r_out, angle_in=None, r_in=0, center=center, mirror=False):
        if angle_in is None:
            angle_in = angle

        def _arc(r, angle, mirror):
            half_angle = angle / 2
            start = -half_angle + (math.pi if mirror else 0)
            stop = half_angle + (math.pi if mirror else 0)
            return arc_points(r, start=start, stop=stop, n=simulation.n, origin=center)

        outer_arc = _arc(r_out, angle, mirror)

        if r_in > 0:
            inner_arc = _arc(r_in, angle_in, mirror)
        else:
            inner_arc = [center]

        return pya.DPolygon(inner_arc + list(reversed(outer_arc)))

    def _angle_from_x(p, origin=center):
        return math.atan2(p.y - origin.y, p.x - origin.x)

    r_coupler_out = simulation.r_outer
    r_coupler_in = r_coupler_out - simulation.outer_island_width
    r_tot = r_coupler_out + simulation.ground_gap

    # Find the angles for the inner and outer arc forming the coupler from refpoints
    coupler_p_in = simulation.refpoints["epr_cplr_in"]
    coupler_p_out = simulation.refpoints["epr_cplr_out"]
    angle_in = 2 * _angle_from_x(coupler_p_in)
    angle_out = 2 * _angle_from_x(coupler_p_out)

    inner_gap_region = _symmetric_sector(
        angle_in, r_coupler_in + simulation.outer_island_width / 2 + region_safety_margin
    )
    outer_gap_region = _symmetric_sector(
        angle_out, r_tot + 1.5 * metal_edge_margin, r_in=r_coupler_out - simulation.outer_island_width / 2
    )

    # if coupler angle is closer than 45 deg from the x axis, make the region cover the central trace.
    # Otherwise the central trace will be in port_a region
    gap_type = (
        simulation.swept_angle / 2 > 135 and abs(((coupler_p_in + coupler_p_out) / 2).x - center.x) > simulation.r_inner
    )

    # how much the angle needs to be larger to include the MER area within the coupler
    coupler_angle_offset_in = 2 * math.atan(1.5 * metal_edge_margin / (r_coupler_in - metal_edge_margin))
    coupler_angle_offset_out = 2 * math.atan(1.5 * metal_edge_margin / (r_coupler_out + metal_edge_margin))
    if gap_type:
        coupler_gap_region = _symmetric_sector(
            2 * math.pi - angle_out + coupler_angle_offset_out,
            r_coupler_out + metal_edge_margin,
            angle_in=2 * math.pi - angle_in + coupler_angle_offset_in,
            r_in=r_coupler_in - metal_edge_margin,
            mirror=True,
        )
    else:
        coupler_up = pya.DPolygon(
            arc_points(
                r_coupler_out + metal_edge_margin,
                start=angle_out / 2 - coupler_angle_offset_out,
                stop=angle_out / 2 + coupler_angle_offset_out,
                n=2,
                origin=center,
            )
            + arc_points(
                r_coupler_in - metal_edge_margin,
                start=angle_in / 2 + coupler_angle_offset_in,
                stop=angle_in / 2 - coupler_angle_offset_in,
                n=2,
                origin=center,
            )
        )
        # mirror the coupler region to the other side
        coupler_down = (
            coupler_up.dup()
            .transform(pya.DTrans(pya.DVector(-center)))
            .transform(pya.DTrans(0, True, pya.DVector(center)))
        )
        coupler_gap_region = [coupler_up, coupler_down]

    lead_region = pya.DBox(
        center + pya.DPoint(-r_tot - metal_edge_margin, -simulation.a / 2 - metal_edge_margin),
        center + pya.DPoint(-simulation.r_inner + metal_edge_margin, simulation.a / 2 + metal_edge_margin),
    )
    a2, b2 = eval_a2(simulation), eval_b2(simulation)
    lead2_region = pya.DBox(
        center + pya.DPoint(r_coupler_out - metal_edge_margin, -a2 / 2 - metal_edge_margin),
        center + pya.DPoint(r_tot + metal_edge_margin, a2 / 2 + metal_edge_margin),
    )
    # Some of the regions overlap so the order of definition is important
    result = [
        _init_part_reg("cplr", coupler_gap_region),
        _init_part_reg("cplr", coupler_gap_region, mer=False),
        _init_part_reg("1lead", lead_region),
        _init_part_reg("1lead", lead_region, mer=False),
        _init_part_reg("2lead", lead2_region),
        _init_part_reg("2lead", lead2_region, mer=False),
    ]

    if _has_waveguides(simulation):
        x_guide = _waveguide_end_dist(simulation)
        # include large bulk area such that all of the waveguide energy can be removed in post-processing
        wg_y_margin = 100
        y1 = simulation.a / 2 + simulation.b + wg_y_margin
        y2 = a2 / 2 + b2 + wg_y_margin

        wg1_region = pya.DBox(
            center + pya.DPoint(-x_guide - metal_edge_margin, -y1),
            center + pya.DPoint(-r_tot - metal_edge_margin / 2, y1),
        )
        wg2_region = pya.DBox(
            center + pya.DPoint(r_tot + metal_edge_margin / 2, -y2),
            center + pya.DPoint(x_guide + metal_edge_margin, y2),
        )
        result += [
            _init_part_reg("port_a", wg1_region),
            _init_part_reg("port_b", wg2_region),
            # Making the wg bulk regions very large to contain all wg energy
            _init_part_reg("port_a", wg1_region, mer=False, override_y_dim=100),
            _init_part_reg("port_b", wg2_region, mer=False, override_y_dim=100),
        ]

    result += [
        _init_part_reg("1gap", inner_gap_region),
        _init_part_reg("2gap", outer_gap_region),
        _init_part_reg("1gap", inner_gap_region, mer=False),
        _init_part_reg("2gap", outer_gap_region, mer=False),
        _init_part_reg("bcomplement", None),
        _init_part_reg("bcomplement", None, mer=False),
    ]

    if _is_flip_chip(simulation):
        if simulation.etch_opposite_face:
            result.append(_init_part_reg("tcomplement", None, face=1))
        result.append(_init_part_reg("tcomplement", None, mer=False, face=1))

    return result


def correction_cuts(simulation: EPRTarget, prefix: str = "") -> dict[str, dict]:

    # def _init_cut(center, width, edges):
    result = {}

    center = simulation.refpoints["base"]
    # Make cuts this much shorter than allowed by perfect rounding to account for discretization
    cut_length_margin = 0.5

    s_to_s_gap = 0
    z_me = 0
    r_tot = simulation.r_outer + simulation.ground_gap
    is_flip_chip = _is_flip_chip(simulation)
    if not in_gui(simulation):
        s_to_s_gap = simulation.chip_distance + 2 * simulation.metal_height
        z_me = -simulation.substrate_height[1] - s_to_s_gap if is_flip_chip else 0

    a2, b2 = eval_a2(simulation), eval_b2(simulation)

    def _coupler_cut_lim(unit_vec, start_p, origin_p, rlim):
        """
        Find how long a line can be extended from `start_p` towards `unit vec` before being over
        `rlim` away from `origin_p`. Returns the solution with smallest absolute value

        Solves n from || start_p + n*unit_vec - origin_p || =  rlim.

        """
        diff = pya.DVector(start_p) - pya.DVector(origin_p)
        dotp = unit_vec.sprod(diff)
        pm = (dotp**2 - diff.sq_length() + rlim**2) ** 0.5
        return min(abs(dotp + pm), abs(dotp - pm))

    cut_center = center + pya.DPoint(-simulation.r_inner - 0.5, 0)
    cut_lim = _coupler_cut_lim(
        pya.DVector(0, 1), cut_center, center, simulation.r_outer - simulation.outer_island_width
    )
    half_cut_length = min(cut_lim - cut_length_margin, 30)
    result[f"{prefix}1leadmer"] = {
        "p1": cut_center + pya.DPoint(0, -half_cut_length),
        "p2": cut_center + pya.DPoint(0, half_cut_length),
        "metal_edges": [
            {"x": half_cut_length - simulation.a / 2, "x_reversed": True, "z": z_me},
            {"x": half_cut_length + simulation.a / 2, "z": z_me},
        ],
        "boundary_conditions": {"xmin": {"potential": 0}, "xmax": {"potential": 0}},
    }

    cut_center = center + pya.DPoint(simulation.r_outer + simulation.ground_gap / 2, 0)
    cut_lim = _coupler_cut_lim(pya.DVector(0, 1), cut_center, center, simulation.r_outer + simulation.ground_gap)
    half_cut_length = min(cut_lim - cut_length_margin, 30)
    result[f"{prefix}2leadmer"] = {
        "p1": cut_center + pya.DPoint(0, -half_cut_length),
        "p2": cut_center + pya.DPoint(0, half_cut_length),
        "metal_edges": [
            {"x": half_cut_length - a2 / 2, "x_reversed": True, "z": z_me},
            {"x": half_cut_length + a2 / 2, "z": z_me},
        ],
        "boundary_conditions": {"xmin": {"potential": 0}, "xmax": {"potential": 0}},
    }

    if _has_waveguides(simulation):
        x_guide = _waveguide_end_dist(simulation)
        wg_cut_x = (x_guide + r_tot) / 2 - 0.2

        # wg1
        cut_center = center + pya.DPoint(-wg_cut_x, 0)
        half_cut_length = simulation.a / 2 + simulation.b + 20
        result[f"{prefix}port_amer"] = {
            "p1": cut_center + pya.DPoint(0, -half_cut_length),
            "p2": cut_center + pya.DPoint(0, half_cut_length),
            "metal_edges": [
                {"x": half_cut_length - simulation.a / 2 - simulation.b, "z": z_me},
                {"x": half_cut_length - simulation.a / 2, "x_reversed": True, "z": z_me},
                {"x": half_cut_length + simulation.a / 2, "z": z_me},
                {"x": half_cut_length + simulation.a / 2 + simulation.b, "x_reversed": True, "z": z_me},
            ],
        }

        # wg2
        cut_center = center + pya.DPoint(wg_cut_x, 0)
        half_cut_length = a2 / 2 + b2 + 20
        result[f"{prefix}port_bmer"] = {
            "p1": cut_center + pya.DPoint(0, -half_cut_length),
            "p2": cut_center + pya.DPoint(0, half_cut_length),
            "metal_edges": [
                {"x": half_cut_length - a2 / 2 - b2, "z": z_me},
                {"x": half_cut_length - a2 / 2, "x_reversed": True, "z": z_me},
                {"x": half_cut_length + a2 / 2, "z": z_me},
                {"x": half_cut_length + a2 / 2 + b2, "x_reversed": True, "z": z_me},
            ],
        }

    # 1gap cut
    half_gap = (simulation.r_outer - simulation.outer_island_width - simulation.r_inner) / 2
    cut_center = center + pya.DPoint(simulation.r_inner + half_gap, 0)
    half_cut_length = half_gap + min(20, simulation.outer_island_width - cut_length_margin)
    result[f"{prefix}1gapmer"] = {
        "p1": cut_center + pya.DPoint(-half_cut_length, 0),
        "p2": cut_center + pya.DPoint(half_cut_length, 0),
        "metal_edges": [
            {"x": half_cut_length - half_gap, "z": z_me},
            {"x": half_cut_length + half_gap, "x_reversed": True, "z": z_me},
        ],
    }

    # 2gap cut
    half_gap = simulation.ground_gap / 2
    # for small swept angle and large a2 we might not be able to take a "gap-type" cross-section so a default one-sided
    # correction is used
    angle_margin = math.radians(0.5)
    wg2_angle = math.atan((b2 + a2 / 2) / (simulation.r_outer + simulation.ground_gap)) + angle_margin
    eff_coupler_angle = math.radians(simulation.swept_angle) / 2 - angle_margin

    if eff_coupler_angle > wg2_angle:
        cut_unit_vector = pya.DVector(math.cos(wg2_angle), math.sin(wg2_angle))
        cut_center = center + (simulation.r_outer + half_gap) * cut_unit_vector
        half_cut_length = half_gap + min(simulation.outer_island_width - cut_length_margin, 20)

        result[f"{prefix}2gapmer"] = {
            "p1": cut_center - half_cut_length * cut_unit_vector,
            "p2": cut_center + half_cut_length * cut_unit_vector,
            "metal_edges": [
                {"x": half_cut_length - half_gap, "z": z_me},
                {"x": half_cut_length + half_gap, "x_reversed": True, "z": z_me},
            ],
        }
    else:
        cut_unit_vector = pya.DVector(math.cos(eff_coupler_angle / 2), math.sin(eff_coupler_angle / 2))
        cut_center = center + simulation.r_outer * cut_unit_vector
        half_cut_length = min(simulation.outer_island_width - cut_length_margin, 30)

        result[f"{prefix}2gapmer"] = {
            "p1": cut_center - half_cut_length * cut_unit_vector,
            "p2": cut_center + half_cut_length * cut_unit_vector,
            "metal_edges": [
                {"x": half_cut_length - half_gap, "z": z_me},
            ],
            "boundary_conditions": {"xmax": {"potential": 0}},
        }

    # cplr cut
    cmin = simulation.refpoints["epr_cplr_in"]
    cmax = simulation.refpoints["epr_cplr_out"]

    coupler_edge_center = (cmin + cmax) / 2

    # make the cut across the central trace and both couplers if the remaining angle between coupler and
    # trace is less than 45 degrees and the cut doesn't cause overlaps with inner islands.
    # Otherwise use one-sided cross-section with the 0 potential "at infinity"

    gap_type = simulation.swept_angle / 2 > 135 and abs(coupler_edge_center.x - center.x) > simulation.r_inner
    if gap_type:
        cut_center = pya.DPoint(coupler_edge_center.x, center.y)
        # vertical unit vector
        cut_unit_vector = pya.DVector(0, -1)
        cplr_gap_width = coupler_edge_center.y - center.y - simulation.a / 2

        half_cut_lim_coupler = _coupler_cut_lim(cut_unit_vector, coupler_edge_center, center, simulation.r_outer)

        half_cut_length = cplr_gap_width + simulation.a / 2 + min(half_cut_lim_coupler - cut_length_margin, 20)
        result[f"{prefix}cplrmer"] = {
            "p1": cut_center - half_cut_length * cut_unit_vector,
            "p2": cut_center + half_cut_length * cut_unit_vector,
            "metal_edges": [
                {"x": half_cut_length - simulation.a / 2 - cplr_gap_width, "z": z_me},
                {"x": half_cut_length - simulation.a / 2, "x_reversed": True, "z": z_me},
                {"x": half_cut_length + simulation.a / 2, "z": z_me},
                {"x": half_cut_length + simulation.a / 2 + cplr_gap_width, "x_reversed": True, "z": z_me},
            ],
        }
    else:
        cut_center = coupler_edge_center
        # unit vector perpendicaular to the coupler island
        cut_unit_vector = pya.DVector(-(cmax - cmin).y, (cmax - cmin).x)
        cut_unit_vector = (1 / cut_unit_vector.length()) * cut_unit_vector
        # restrict the cut to stay in the coupler island
        half_cut_lim_coupler = _coupler_cut_lim(cut_unit_vector, coupler_edge_center, center, simulation.r_outer)
        # restrict not to cut over the central trace
        half_cut_trace_lim = (
            math.inf
            if cut_unit_vector.y == 0
            else abs((cut_center.y - center.y - simulation.a / 2) / cut_unit_vector.y)
        )
        half_cut_length = min(half_cut_lim_coupler, half_cut_trace_lim)
        # default to max 40
        half_cut_length = min(40, half_cut_length - cut_length_margin)

        result[f"{prefix}cplrmer"] = {
            "p1": cut_center - half_cut_length * cut_unit_vector,
            "p2": cut_center + half_cut_length * cut_unit_vector,
            "metal_edges": [
                {"x": half_cut_length, "z": z_me},
            ],
            "boundary_conditions": {"xmax": {"potential": 0}},
        }

    # bcomplement cut
    # This might contain one or 2 metal edges with maybe non-optimal placement with some parameters
    # However, in the edge cases the bcomplement region is almost empty so it doesnt have much effect
    wg1_angle = (
        math.atan(
            (simulation.b + simulation.a / 2 + simulation.etch_opposite_face_margin)
            / (simulation.r_outer + simulation.ground_gap)
        )
        + angle_margin
    )
    cut_unit_vector = pya.DVector(math.cos(math.pi - wg1_angle), math.sin(math.pi - wg1_angle))
    cut_center = center + (simulation.r_outer + simulation.ground_gap) * cut_unit_vector
    half_cut_length = 30
    result[f"{prefix}bcomplementmer"] = {
        "p1": cut_center + half_cut_length * cut_unit_vector,
        "p2": cut_center - half_cut_length * cut_unit_vector,
        "metal_edges": [
            {"x": half_cut_length, "z": z_me},
        ],
        "boundary_conditions": {"xmax": {"potential": 1}},
    }

    # tcomplement cut
    # almost same as bcomplement cut but different mer box
    if is_flip_chip and simulation.etch_opposite_face:
        cut_center = (
            center
            + (simulation.r_outer + simulation.ground_gap + simulation.etch_opposite_face_margin) * cut_unit_vector
        )
        half_cut_length = 30
        result[f"{prefix}tcomplementmer"] = {
            "p1": cut_center + half_cut_length * cut_unit_vector,
            "p2": cut_center - half_cut_length * cut_unit_vector,
            "metal_edges": [
                {"x": half_cut_length, "z": z_me + s_to_s_gap},
            ],
            "boundary_conditions": {"xmax": {"potential": 1}},
        }

    return result


def extract_circular_capacitor_from(
    simulation: EPRTarget, refpoint_prefix: str, parameter_remap_function: Callable[[EPRTarget, str], any]
) -> Simulation:
    # fmt: off
    return extract_child_simulation(
        simulation,
        refpoint_prefix,
        parameter_remap_function,
        [
            "n", "a", "a2", "b", "b2", "face_stack", "waveguide_length",
            "fixed_length", "r_inner", "r_outer", "swept_angle", "outer_island_width", "ground_gap",
            "etch_opposite_face", "etch_opposite_face_margin", "use_internal_ports", "box",
        ],
    )
    # fmt: on
