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
from kqcircuits.simulations.epr.utils import extract_child_simulation
from kqcircuits.simulations.partition_region import PartitionRegion
from kqcircuits.simulations.simulation import Simulation


# Partition region and correction cuts definitions for Swissmon qubit


def partition_regions(simulation: Simulation, prefix: str = "") -> list[PartitionRegion]:
    metal_edge_dimension = 4.0
    metal_edge_margin = pya.DPoint(metal_edge_dimension, metal_edge_dimension)
    cross_poly = pya.DPolygon([simulation.refpoints[f"epr_cross_{idx:02d}"] for idx in range(12)]).sized(
        metal_edge_dimension + simulation.island_r
    )

    result = [
        PartitionRegion(
            name=f"{prefix}crossmer",
            face=simulation.face_ids[0],
            metal_edge_dimensions=metal_edge_dimension,
            region=cross_poly,
            vertical_dimensions=3.0,
            visualise=True,
        ),
        PartitionRegion(
            name=f"{prefix}crossbulk",
            face=simulation.face_ids[0],
            metal_edge_dimensions=None,
            region=cross_poly,
            vertical_dimensions=3.0,
            visualise=True,
        ),
    ]

    # These are added to include the waveguides attached to couplers in the coupler region
    def _get_coupler_wg_offset(i, s):
        coupler_wg_offsets = [{"min": pya.DPoint(-150, 0)}, {"max": pya.DPoint(0, 150)}, {"max": pya.DPoint(150, 0)}]
        return coupler_wg_offsets[i].get(s, pya.DPoint(0, 0))

    for idx in range(3):
        # Need to check if coupler is present
        if simulation.cpl_length[idx] > 0:
            cplr_region = pya.DBox(
                simulation.refpoints[f"epr_cplr{idx}_min"] - metal_edge_margin + _get_coupler_wg_offset(idx, "min"),
                simulation.refpoints[f"epr_cplr{idx}_max"] + metal_edge_margin + _get_coupler_wg_offset(idx, "max"),
            )
            result += [
                PartitionRegion(
                    name=f"{prefix}{idx}cplrmer",
                    face=simulation.face_ids[0],
                    metal_edge_dimensions=metal_edge_dimension,
                    region=cplr_region,
                    vertical_dimensions=3.0,
                    visualise=True,
                ),
                PartitionRegion(
                    name=f"{prefix}{idx}cplrbulk",
                    face=simulation.face_ids[0],
                    metal_edge_dimensions=None,
                    region=cplr_region,
                    vertical_dimensions=3.0,
                    visualise=True,
                ),
            ]
    return result


def correction_cuts(simulation: Simulation, prefix: str = "") -> dict[str, dict]:
    cross_corner = simulation.refpoints["epr_cross_09"]
    coupler_corner = (
        simulation.refpoints["epr_cplr0_max"] if simulation.cpl_length[0] > 0 else simulation.refpoints["epr_cross_08"]
    )

    half_gap = simulation.gap_width[1] / 2
    if len(set(simulation.gap_width)) > 1:
        logging.warning("Partition regions for Swissmon with varying gaps are not implemented")
        logging.warning(
            "Using correction with %s gap for all arms with gap widths %s", str(2 * half_gap), str(simulation.gap_width)
        )

    cross_xsection_center = pya.DPoint((cross_corner.x + coupler_corner.x) / 2, cross_corner.y - half_gap)
    half_cut_length = 30.0
    result = {
        f"{prefix}crossmer": {
            "p1": cross_xsection_center + pya.DPoint(0, -half_cut_length),
            "p2": cross_xsection_center + pya.DPoint(0, half_cut_length),
            "metal_edges": [{"x": half_cut_length - half_gap}, {"x": half_cut_length + half_gap, "x_reversed": True}],
        }
    }

    half_gap = simulation.b / 2
    if simulation.cpl_length[0] > 0:
        xsection_point = simulation.cpl_gap[0] / 2 + simulation.cpl_width[0] / 2
        result[f"{prefix}0cplrmer"] = {
            "p1": simulation.refpoints["port_cplr0"] + pya.DPoint(-half_cut_length + half_gap, xsection_point),
            "p2": simulation.refpoints["port_cplr0"] + pya.DPoint(half_cut_length + half_gap, xsection_point),
            "metal_edges": [{"x": half_cut_length - half_gap}, {"x": half_cut_length + half_gap, "x_reversed": True}],
        }
    if simulation.cpl_length[1] > 0:
        xsection_point = simulation.cpl_gap[1] / 2 + simulation.cpl_width[1] / 2
        result[f"{prefix}1cplrmer"] = {
            "p1": simulation.refpoints["port_cplr1"] + pya.DPoint(xsection_point, half_cut_length - half_gap),
            "p2": simulation.refpoints["port_cplr1"] + pya.DPoint(xsection_point, -half_cut_length - half_gap),
            "metal_edges": [{"x": half_cut_length - half_gap}, {"x": half_cut_length + half_gap, "x_reversed": True}],
        }
    if simulation.cpl_length[2] > 0:
        xsection_point = simulation.cpl_gap[2] / 2 + simulation.cpl_width[2] / 2
        result[f"{prefix}2cplrmer"] = {
            "p1": simulation.refpoints["port_cplr2"] + pya.DPoint(-half_cut_length - half_gap, xsection_point),
            "p2": simulation.refpoints["port_cplr2"] + pya.DPoint(half_cut_length - half_gap, xsection_point),
            "metal_edges": [{"x": half_cut_length - half_gap}, {"x": half_cut_length + half_gap, "x_reversed": True}],
        }
    return result


def extract_swissmon_from(
    simulation: Simulation, refpoint_prefix: str, parameter_remap_function: Callable[[Simulation, str], any]
):
    return extract_child_simulation(
        simulation,
        refpoint_prefix,
        parameter_remap_function,
        [
            "b",
            "gap_width",
            "face_ids",  # Accesses list's index 0
            "island_r",
            "cpl_gap",  # Accesses list's indices 0, 1, 2
            "cpl_width",  # Accesses list's indices 0, 1, 2
            "cpl_length",  # Accesses list's indices 0, 1, 2
        ],
    )
