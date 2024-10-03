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
from kqcircuits.simulations.simulation import Simulation


# Partition region and correction cuts definitions for Swissmon qubit
vertical_dimension = 3.0
metal_edge_dimension = 4.0


def partition_regions(simulation: Simulation, prefix: str = "") -> list[PartitionRegion]:

    base_rf = simulation.refpoints["base"]
    port_a_rf = simulation.refpoints["port_a"]
    port_b_rf = simulation.refpoints["port_b"]

    scale = simulation.finger_width + simulation.finger_gap
    s_len = scale * (2 * simulation.finger_control - 3)  # length of straight segment
    width = scale * simulation.finger_control - simulation.finger_width / 2 - simulation.finger_gap / 2

    box_dp = pya.DPoint(s_len / 2.0 + simulation.finger_width + simulation.finger_gap, width)

    a2 = simulation.a if simulation.a2 < 0 else simulation.a2
    b2 = simulation.b if simulation.b2 < 0 else simulation.b2
    rr = b2 + a2 / 2
    rr = (rr + (simulation.finger_gap + 1.5 * simulation.finger_width)) / 2
    rr /= simulation.layout.dbu

    box = pya.DBox(base_rf - box_dp, base_rf + box_dp)
    box_rounded = pya.Region(box.to_itype(simulation.layout.dbu)).rounded_corners(rr, rr, simulation.n)

    port_a_len = 11 + simulation.waveguide_length + metal_edge_dimension  # 11 is the hardcoded port dimension
    port_a_width = simulation.a + 2 * simulation.b + 2 * metal_edge_dimension
    port_a_middle = port_a_rf - pya.DPoint(port_a_len / 2.0, 0)
    port_a_dp = pya.DPoint(port_a_len / 2.0, port_a_width / 2)
    port_a_region = pya.DBox(port_a_middle - port_a_dp, port_a_middle + port_a_dp)

    port_b_len = 11 + simulation.waveguide_length + metal_edge_dimension  # 11 is the hardcoded port dimension
    port_b_width = a2 + 2 * b2 + 2 * metal_edge_dimension
    port_b_middle = port_b_rf + pya.DPoint(port_b_len / 2.0, 0)
    port_b_dp = pya.DPoint(port_b_len / 2.0, port_b_width / 2)
    port_b_region = pya.DBox(port_b_middle - port_b_dp, port_b_middle + port_b_dp)

    result = [
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
        PartitionRegion(
            name=f"{prefix}fingersmer",
            face=simulation.face_ids[0],
            metal_edge_dimensions=metal_edge_dimension,
            region=box_rounded,
            vertical_dimensions=vertical_dimension,
            visualise=True,
        ),
        PartitionRegion(
            name=f"{prefix}fingersbulk",
            face=simulation.face_ids[0],
            metal_edge_dimensions=None,
            region=box_rounded,
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

    if len(simulation.face_stack) > 1:
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


def correction_cuts(simulation: Simulation, prefix: str = "") -> dict[str, dict]:
    base_rf = simulation.refpoints["base"]
    port_a_rf = simulation.refpoints["port_a"]
    port_b_rf = simulation.refpoints["port_b"]

    a2 = simulation.a if simulation.a2 < 0 else simulation.a2
    b2 = simulation.b if simulation.b2 < 0 else simulation.b2

    port_a_len = 11 + simulation.waveguide_length + metal_edge_dimension  # 11 is the hardcoded port dimension
    port_a_middle = port_a_rf - pya.DPoint(port_a_len / 2.0, 0)
    port_a_width = simulation.a + 2 * simulation.b + 2 * metal_edge_dimension

    port_b_len = 11 + simulation.waveguide_length + metal_edge_dimension  # 11 is the hardcoded port dimension
    port_b_middle = port_b_rf + pya.DPoint(port_b_len / 2.0, 0)
    port_b_width = a2 + 2 * b2 + 2 * metal_edge_dimension

    if len(simulation.face_stack) == 1:
        z_me = 0
    else:
        z_me = -simulation.substrate_height[1] - simulation.chip_distance - 2 * simulation.metal_height

    scale = simulation.finger_width + simulation.finger_gap
    half_cut_len = 25.0
    result = {
        f"{prefix}fingersmer": {
            "p1": base_rf + pya.DPoint(0, -scale / 2),
            "p2": base_rf + pya.DPoint(0, scale / 2),
            "metal_edges": [
                {"x": (scale - simulation.finger_gap) / 2, "z": z_me},
                {"x": (scale + simulation.finger_gap) / 2, "z": z_me},
            ],
        },
        f"{prefix}port_amer": {
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
        },
        f"{prefix}port_bmer": {
            "p1": port_b_middle - pya.DPoint(0, port_b_width),
            "p2": port_b_middle + pya.DPoint(0, port_b_width),
            "metal_edges": [
                {"x": port_b_width - a2 / 2 - b2, "z": z_me},
                {"x": port_b_width - a2 / 2, "z": z_me},
                {"x": port_b_width + a2 / 2, "z": z_me},
                {"x": port_b_width + a2 / 2 + b2, "z": z_me},
            ],
        },
        f"{prefix}bcomplementmer": {
            "p1": port_a_rf + pya.DPoint(-half_cut_len, simulation.a + simulation.b),
            "p2": port_a_rf + pya.DPoint(half_cut_len, simulation.a + simulation.b),
            "metal_edges": [
                {"x": half_cut_len, "z": z_me},
            ],
        },
    }
    return result
