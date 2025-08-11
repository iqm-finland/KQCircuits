# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
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
from kqcircuits.simulations.epr.util import EPRTarget, create_bulk_and_mer_partition_regions
from kqcircuits.simulations.partition_region import PartitionRegion

# Partition region and correction cuts definitions for double_pads qubit

metal_edge_dimension = 3.0
vertical_dimension = 3.0
metal_edge_dimensions = [
    metal_edge_dimension,  # gap
    metal_edge_dimension,  # metal
]
junction_lead_width = 8.0  # for now, this is 8 um in Doublepad


def partition_regions(simulation: EPRTarget, prefix: str = "") -> list[PartitionRegion]:
    squid_height_ = simulation.refpoints["junction1"] - simulation.refpoints["base"]
    squid_height = squid_height_.y
    island1_bottom = simulation.squid_offset + squid_height / 2
    base = simulation.refpoints["base"]
    taper_height = (simulation.island_island_gap - squid_height) / 2

    island1_extent_0 = float(simulation.island1_extent[0])
    island1_extent_1 = float(simulation.island1_extent[1])

    island1_polygon = pya.DPolygon(
        [
            pya.DPoint(
                -island1_extent_0 / 2 - metal_edge_dimension,
                island1_bottom + taper_height + island1_extent_1 + metal_edge_dimension,
            ),
            pya.DPoint(
                island1_extent_0 / 2 + metal_edge_dimension,
                island1_bottom + taper_height + island1_extent_1 + metal_edge_dimension,
            ),
            pya.DPoint(
                island1_extent_0 / 2 + metal_edge_dimension, island1_bottom + taper_height - metal_edge_dimension
            ),
            pya.DPoint(
                -island1_extent_0 / 2 - metal_edge_dimension, island1_bottom + taper_height - metal_edge_dimension
            ),
        ]
    )

    island1_region = pya.Region(
        island1_polygon.transformed(pya.DCplxTrans(1, 0, False, base.x, base.y)).to_itype(simulation.layout.dbu)
    )

    island1_region.round_corners(
        simulation.island1_r / simulation.layout.dbu, simulation.island1_r / simulation.layout.dbu, simulation.n
    )

    island1_taper = pya.Region(
        pya.DPolygon(
            [
                pya.DPoint(
                    simulation.island1_taper_width / 2 + metal_edge_dimension - 0.624,
                    island1_bottom + taper_height - metal_edge_dimension,
                ),
                pya.DPoint(
                    simulation.island1_taper_junction_width / 2 + metal_edge_dimension + 0.08,
                    island1_bottom + 2.75 * metal_edge_dimension,
                ),
                pya.DPoint(
                    -simulation.island1_taper_junction_width / 2 - metal_edge_dimension - 0.08,
                    island1_bottom + 2.75 * metal_edge_dimension,
                ),
                pya.DPoint(
                    -simulation.island1_taper_width / 2 - metal_edge_dimension + 0.624,
                    island1_bottom + taper_height - metal_edge_dimension,
                ),
            ]
        )
        .transformed(pya.DCplxTrans(1, 0, False, base.x, base.y))
        .to_itype(simulation.layout.dbu)
    )

    island1_region = island1_region + island1_taper

    island2_top = simulation.squid_offset - squid_height / 2
    island2_polygon = pya.DPolygon(
        [
            pya.DPoint(
                -island1_extent_0 / 2 - metal_edge_dimension,
                island2_top - taper_height - island1_extent_1 - metal_edge_dimension,
            ),
            pya.DPoint(
                island1_extent_0 / 2 + metal_edge_dimension,
                island2_top - taper_height - island1_extent_1 - metal_edge_dimension,
            ),
            pya.DPoint(island1_extent_0 / 2 + metal_edge_dimension, island2_top - taper_height + metal_edge_dimension),
            pya.DPoint(-island1_extent_0 / 2 - metal_edge_dimension, island2_top - taper_height + metal_edge_dimension),
        ]
    )

    island2_region = pya.Region(
        island2_polygon.transformed(pya.DCplxTrans(1, 0, False, base.x, base.y)).to_itype(simulation.layout.dbu)
    )
    island2_region.round_corners(
        simulation.island2_r / simulation.layout.dbu, simulation.island2_r / simulation.layout.dbu, simulation.n
    )

    island2_taper = pya.Region(
        pya.DPolygon(
            [
                pya.DPoint(
                    simulation.island2_taper_width / 2 + metal_edge_dimension - 0.624,
                    island2_top - taper_height + metal_edge_dimension,
                ),
                pya.DPoint(
                    simulation.island2_taper_junction_width / 2 + metal_edge_dimension - 0.6201,
                    island2_top - 1.75 * metal_edge_dimension,
                ),
                pya.DPoint(
                    -simulation.island2_taper_junction_width / 2 - metal_edge_dimension + 0.6201,
                    island2_top - 1.75 * metal_edge_dimension,
                ),
                pya.DPoint(
                    -simulation.island2_taper_width / 2 - metal_edge_dimension + 0.624,
                    island2_top - taper_height + metal_edge_dimension,
                ),
            ]
        )
        .transformed(pya.DCplxTrans(1, 0, False, base.x, base.y))
        .to_itype(simulation.layout.dbu)
    )

    island2_region = island2_region + island2_taper

    sector_region = island1_region + island2_region

    # Lead region
    leads_p1 = simulation.refpoints["junction1"] - pya.DPoint(2.5 * metal_edge_dimension, 0)
    leads_p2 = simulation.refpoints["junction2"] + pya.DPoint(2.5 * metal_edge_dimension, metal_edge_dimension)
    # 2.5 factor is there to cover the electric field in the lead reagion properly.

    # coupler region
    first_island_top_edge = (simulation.squid_offset + squid_height / 2) + taper_height + island1_extent_1
    coupler_top_edge = first_island_top_edge + simulation.coupler_offset + float(simulation.coupler_extent[1])

    coupler_path_polygon = pya.DPolygon(
        [
            pya.DPoint(
                -simulation.coupler_a / 2 - 2 * metal_edge_dimension, (float(simulation.ground_gap[1]) / 2 + 100)
            ),
            pya.DPoint(
                simulation.coupler_a / 2 + 2 * metal_edge_dimension, (float(simulation.ground_gap[1]) / 2 + 100)
            ),
            pya.DPoint(
                simulation.coupler_a / 2 + 2 * metal_edge_dimension, coupler_top_edge + 2 * metal_edge_dimension
            ),
            pya.DPoint(
                -simulation.coupler_a / 2 - 2 * metal_edge_dimension, coupler_top_edge + 2 * metal_edge_dimension
            ),
        ]
    )

    coupler1_region = pya.Region(
        coupler_path_polygon.transformed(pya.DCplxTrans(1, 0, False, base.x, base.y)).to_itype(simulation.layout.dbu)
    )

    coupler2_polygon = pya.DPolygon(
        [
            pya.DPoint(
                -float(simulation.coupler_extent[0]) / 2 - 2 * metal_edge_dimension,
                coupler_top_edge + 2 * metal_edge_dimension,
            ),
            pya.DPoint(
                -float(simulation.coupler_extent[0]) / 2 - 2 * metal_edge_dimension,
                first_island_top_edge + simulation.coupler_offset - 2 * metal_edge_dimension,
            ),
            pya.DPoint(
                float(simulation.coupler_extent[0]) / 2 + 2 * metal_edge_dimension,
                first_island_top_edge + simulation.coupler_offset - 2 * metal_edge_dimension,
            ),
            pya.DPoint(
                float(simulation.coupler_extent[0]) / 2 + 2 * metal_edge_dimension,
                coupler_top_edge + 2 * metal_edge_dimension,
            ),
        ]
    )

    coupler2_region = pya.Region(
        coupler2_polygon.transformed(pya.DCplxTrans(1, 0, False, base.x, base.y)).to_itype(simulation.layout.dbu)
    )
    coupler2_region.round_corners(
        simulation.coupler_r / simulation.layout.dbu, simulation.coupler_r / simulation.layout.dbu, simulation.n
    )

    result = create_bulk_and_mer_partition_regions(
        name=f"{prefix}coupler1",
        face=simulation.face_ids[0],
        region=coupler1_region,
        vertical_dimensions=vertical_dimension,
        metal_edge_dimensions=metal_edge_dimension,
        bulk=False,
        visualise=True,
    )
    result += create_bulk_and_mer_partition_regions(
        name=f"{prefix}coupler2",
        face=simulation.face_ids[0],
        region=coupler2_region,
        vertical_dimensions=vertical_dimension,
        metal_edge_dimensions=metal_edge_dimension,
        bulk=False,
        visualise=True,
    )
    result += create_bulk_and_mer_partition_regions(
        name=f"{prefix}island",
        face=simulation.face_ids[0],
        region=sector_region,
        vertical_dimensions=vertical_dimension,
        metal_edge_dimensions=[6.0, metal_edge_dimensions[1]],
        visualise=True,
    )
    result += create_bulk_and_mer_partition_regions(
        name=f"{prefix}leads",
        face=simulation.face_ids[0],
        metal_edge_dimensions=metal_edge_dimensions,
        region=pya.DBox(leads_p1, leads_p2),
        vertical_dimensions=vertical_dimension,
        visualise=True,
    )
    result += create_bulk_and_mer_partition_regions(
        name=f"{prefix}tcomplement",
        face=simulation.face_ids[0],
        metal_edge_dimensions=metal_edge_dimensions,
        region=None,
        vertical_dimensions=vertical_dimension,
        visualise=True,
    )
    result += create_bulk_and_mer_partition_regions(
        name=f"{prefix}bcomplement",
        face=simulation.face_ids[1],
        metal_edge_dimensions=metal_edge_dimensions,
        region=None,
        vertical_dimensions=vertical_dimension,
        visualise=True,
    )
    return result


def correction_cuts(simulation: EPRTarget, prefix: str = "") -> dict[str, dict]:
    half_cut_length = 30.0

    leads_center = simulation.refpoints["junction1"]

    island2_extent0 = float(simulation.island2_extent[0])
    island2_extent1 = float(simulation.island2_extent[1])
    coupler_extent0 = float(simulation.coupler_extent[0])
    coupler_extent1 = float(simulation.coupler_extent[1])
    ground_gap = simulation.refpoints["base"] + pya.DPoint(float(simulation.ground_gap[0]) / 2, 0)
    island1_edge = simulation.refpoints["base"] + pya.DPoint(island2_extent0 / 4.0, simulation.island_island_gap / 2.0)
    coupler2_center = simulation.refpoints["probe_island_1"] + pya.DPoint(
        0, island2_extent1 / 2 + simulation.coupler_offset + coupler_extent1 / 2
    )
    coupler1_center = simulation.refpoints["probe_island_1"] + pya.DPoint(
        0, island2_extent1 / 2 + simulation.coupler_offset + 4 * coupler_extent1
    )

    result = {
        f"{prefix}islandmer": {
            "p1": island1_edge + pya.DPoint(0, -half_cut_length),
            "p2": island1_edge + pya.DPoint(0, half_cut_length),
            "boundary_conditions": {"xmin": {"potential": 0}, "ymax": {"potential": 0}},
        },
        f"{prefix}leadsmer": {
            "p1": leads_center + pya.DPoint(-half_cut_length, -2 * metal_edge_dimension),
            "p2": leads_center + pya.DPoint(half_cut_length, -2 * metal_edge_dimension),
            "boundary_conditions": {"xmax": {"potential": 0}, "xmin": {"potential": 0}},
        },
        f"{prefix}coupler2mer": {
            "p1": coupler2_center + pya.DPoint(coupler_extent0 / 4.0, -half_cut_length),
            "p2": coupler2_center + pya.DPoint(coupler_extent0 / 4.0, half_cut_length),
            "boundary_conditions": {"xmax": {"potential": 0}, "xmin": {"potential": 0}},
        },
        f"{prefix}coupler1mer": {
            "p1": coupler1_center + pya.DPoint(-half_cut_length, 0),
            "p2": coupler1_center + pya.DPoint(half_cut_length, 0),
            "boundary_conditions": {"xmax": {"potential": 0}, "xmin": {"potential": 0}},
        },
        f"{prefix}tcomplementmer": {
            "p1": ground_gap + pya.DPoint(-half_cut_length, 0),
            "p2": ground_gap + pya.DPoint(half_cut_length, 0),
            "boundary_conditions": {"xmin": {"potential": 1}, "ymax": {"potential": 0}},
        },
        f"{prefix}bcomplementmer": {
            "p1": ground_gap + pya.DPoint(-half_cut_length, 0),
            "p2": ground_gap + pya.DPoint(half_cut_length, 0),
            "boundary_conditions": {"xmin": {"potential": 1}, "ymax": {"potential": 0}},
        },
    }
    return result
