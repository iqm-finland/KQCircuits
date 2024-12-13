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

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.partition_region import PartitionRegion
from kqcircuits.simulations.epr.utils import in_gui, EPRTarget
from kqcircuits.elements.smooth_capacitor import SmoothCapacitor
from kqcircuits.elements.finger_capacitor_square import eval_a2, eval_b2


# Partition region and correction cuts definitions for Swissmon qubit
vertical_dimension = 1.0
metal_edge_dimension = 2.0


def partition_regions(simulation: EPRTarget, prefix: str = "") -> list[PartitionRegion]:

    port_a_rf = simulation.refpoints["port_a"]
    port_b_rf = simulation.refpoints["port_b"]

    a2, b2 = eval_a2(simulation), eval_b2(simulation)

    # Make a stub SmoothCapacitor instance, copy some attributes
    # then use some region generating functions to create a partition region shape overlapping finger edges
    s = SmoothCapacitor()
    s.n = simulation.n
    s.finger_width = simulation.finger_width
    s.finger_gap = simulation.finger_gap
    s.finger_control = simulation.finger_control
    s.ground_gap = simulation.ground_gap
    s.layout = simulation.layout

    right_fingers, left_fingers = s.get_finger_regions()
    region_ground = right_fingers + left_fingers
    region_ground += s.middle_gap_fill().sized(-simulation.ground_gap / simulation.layout.dbu, 5)
    fingers = (
        s.super_smoothen_region(region_ground, simulation.finger_gap + simulation.ground_gap)
        .sized(-(simulation.finger_width / 2.0) / simulation.layout.dbu, 5)
        .transformed(pya.DTrans(0, False, simulation.refpoints["base"]).to_itype(simulation.layout.dbu))
    )

    result = []
    if not in_gui(simulation):
        port_a_len = 11 + simulation.waveguide_length + metal_edge_dimension  # 11 is the hardcoded port dimension
        port_a_width = simulation.a + 2 * simulation.b + 2 * metal_edge_dimension
        port_a_middle = port_a_rf - pya.DPoint(port_a_len / 2.0, 0)
        port_a_dp = pya.DPoint(port_a_len / 2.0, port_a_width / 2)

        port_b_len = 11 + simulation.waveguide_length + metal_edge_dimension  # 11 is the hardcoded port dimension
        port_b_width = a2 + 2 * b2 + 2 * metal_edge_dimension
        port_b_middle = port_b_rf + pya.DPoint(port_b_len / 2.0, 0)
        port_b_dp = pya.DPoint(port_b_len / 2.0, port_b_width / 2)

        if simulation.use_internal_ports:
            port_a_region = pya.DBox(port_a_middle - port_a_dp, port_a_middle + port_a_dp)
            port_b_region = pya.DBox(port_b_middle - port_b_dp, port_b_middle + port_b_dp)
        else:
            port_a_dpx_edge = pya.DPoint(-simulation.box.width() / 2.0, 0.0)
            port_a_dpy = pya.DPoint(0.0, port_a_width / 2)
            port_a_middley = pya.DPoint(0, port_a_middle.y)
            port_a_region = pya.DBox(port_a_dpx_edge + port_a_middley - port_a_dpy, port_a_middle + port_a_dp)

            port_b_dpx_edge = pya.DPoint(simulation.box.width(), 0.0)
            port_b_dpy = pya.DPoint(0.0, port_b_width / 2)
            port_b_middley = pya.DPoint(0, port_b_middle.y)
            port_b_region = pya.DBox(port_b_middle - port_b_dp, port_b_dpx_edge + port_b_middley + port_b_dpy)

        result += [
            PartitionRegion(
                name=f"{prefix}port_bmer",
                face=simulation.face_ids[0],
                metal_edge_dimensions=metal_edge_dimension,
                region=port_b_region,
                vertical_dimensions=vertical_dimension,
                visualise=True,
            ),
            PartitionRegion(
                name=f"{prefix}port_bbulk",
                face=simulation.face_ids[0],
                metal_edge_dimensions=None,
                region=port_b_region,
                vertical_dimensions=vertical_dimension,
                visualise=True,
            ),
            PartitionRegion(
                name=f"{prefix}port_amer",
                face=simulation.face_ids[0],
                metal_edge_dimensions=metal_edge_dimension,
                region=port_a_region,
                vertical_dimensions=vertical_dimension,
                visualise=True,
            ),
            PartitionRegion(
                name=f"{prefix}port_abulk",
                face=simulation.face_ids[0],
                metal_edge_dimensions=None,
                region=port_a_region,
                vertical_dimensions=vertical_dimension,
                visualise=True,
            ),
        ]

    result += [
        PartitionRegion(
            name=f"{prefix}fingersmer",
            face=simulation.face_ids[0],
            metal_edge_dimensions=metal_edge_dimension,
            region=fingers,
            vertical_dimensions=vertical_dimension,
            visualise=True,
        ),
        PartitionRegion(
            name=f"{prefix}fingersbulk",
            face=simulation.face_ids[0],
            metal_edge_dimensions=None,
            region=fingers,
            vertical_dimensions=vertical_dimension,
            visualise=True,
        ),
        PartitionRegion(
            name=f"{prefix}bcomplementmer",
            face=simulation.face_ids[0],
            metal_edge_dimensions=metal_edge_dimension,
            region=None,
            vertical_dimensions=vertical_dimension,
            visualise=True,
        ),
        PartitionRegion(
            name=f"{prefix}bcomplementbulk",
            face=simulation.face_ids[0],
            region=None,
            vertical_dimensions=vertical_dimension,
            visualise=True,
        ),
    ]

    if in_gui(simulation):
        make_t_regions = True
    else:
        make_t_regions = len(simulation.face_stack) > 1
    if make_t_regions:
        result += [
            PartitionRegion(
                name=f"{prefix}tcomplementmer",
                face=simulation.face_ids[1],
                metal_edge_dimensions=metal_edge_dimension,
                region=None,
                vertical_dimensions=vertical_dimension,
                visualise=True,
            ),
            PartitionRegion(
                name=f"{prefix}tcomplementbulk",
                face=simulation.face_ids[1],
                region=None,
                vertical_dimensions=vertical_dimension,
                visualise=True,
            ),
        ]

    return result


def correction_cuts(simulation: EPRTarget, prefix: str = "") -> dict[str, dict]:
    base_rf = simulation.refpoints["base"]
    port_a_rf = simulation.refpoints["port_a"]
    port_b_rf = simulation.refpoints["port_b"]

    a2, b2 = eval_a2(simulation), eval_b2(simulation)

    gaps = pya.Region(simulation.cell.begin_shapes_rec(simulation.get_layer("base_metal_gap_wo_grid")))
    finger_top = None
    finger_center = None
    for polygon in gaps.each():
        for edge in polygon.to_dtype(simulation.layout.dbu).each_edge():
            # Hole edges are oriented counterclockwise while hull edges are oriented clockwise.
            # Rely on this orientation to get top point of fingers.
            if edge.d().x < 0.0 and (finger_top is None or edge.p1.y > finger_top.y):
                finger_top = edge.p1

            k = edge.d().sprod(base_rf - edge.p1) / edge.d().sq_abs()
            nearest = (edge.p1 if k <= 0.0 else (edge.p2 if k >= 1.0 else edge.p1 + k * edge.d())) - base_rf
            if finger_center is None or nearest.abs() < finger_center.abs():
                if simulation.finger_control > 1.0 or abs(nearest.y) < abs(nearest.x):
                    finger_center = nearest

    z_me = 0
    if not in_gui(simulation):
        port_a_len = 11 + simulation.waveguide_length + metal_edge_dimension  # 11 is the hardcoded port dimension
        port_a_middle = port_a_rf - pya.DPoint(port_a_len / 2.0, 0)
        port_a_width = simulation.a + 2 * simulation.b + 2 * metal_edge_dimension

        port_b_len = 11 + simulation.waveguide_length + metal_edge_dimension  # 11 is the hardcoded port dimension
        port_b_middle = port_b_rf + pya.DPoint(port_b_len / 2.0, 0)
        port_b_width = a2 + 2 * b2 + 2 * metal_edge_dimension

        if len(simulation.face_stack) > 1:
            z_me = -simulation.substrate_height[1] - simulation.chip_distance - 2 * simulation.metal_height

    fingersmer_end = finger_center * (1.0 + simulation.finger_width * 0.9 / finger_center.abs())
    half_cut_len = 25.0
    result = {
        f"{prefix}fingersmer": {
            "p1": base_rf + fingersmer_end,
            "p2": base_rf - fingersmer_end,
            "metal_edges": [
                {"x": simulation.finger_width * 0.9, "z": z_me},
                {"x": 2 * fingersmer_end.abs() - simulation.finger_width * 0.9, "z": z_me},
            ],
        },
        f"{prefix}bcomplementmer": {
            "p1": finger_top + pya.DVector(0, simulation.ground_gap + half_cut_len),
            "p2": finger_top - pya.DVector(0, simulation.finger_width * 0.9),
            "metal_edges": [
                {"x": half_cut_len, "z": z_me},
                {"x": half_cut_len + simulation.ground_gap, "z": z_me},
            ],
        },
    }
    if not in_gui(simulation):
        result[f"{prefix}port_amer"] = {
            "p1": port_a_middle - pya.DPoint(0, port_a_width),
            "p2": port_a_middle + pya.DPoint(0, port_a_width),
            "metal_edges": [
                {
                    "x": port_a_width - simulation.a / 2.0 - simulation.b,
                    "z": z_me,
                },
                {
                    "x": port_a_width - simulation.a / 2.0,
                    "z": z_me,
                },
                {
                    "x": port_a_width + simulation.a / 2.0,
                    "z": z_me,
                },
                {
                    "x": port_a_width + simulation.a / 2.0 + simulation.b,
                    "z": z_me,
                },
            ],
        }
        result[f"{prefix}port_bmer"] = {
            "p1": port_b_middle - pya.DPoint(0, port_b_width),
            "p2": port_b_middle + pya.DPoint(0, port_b_width),
            "metal_edges": [
                {"x": port_b_width - a2 / 2 - b2, "z": z_me},
                {"x": port_b_width - a2 / 2, "z": z_me},
                {"x": port_b_width + a2 / 2, "z": z_me},
                {"x": port_b_width + a2 / 2 + b2, "z": z_me},
            ],
        }
    return result
