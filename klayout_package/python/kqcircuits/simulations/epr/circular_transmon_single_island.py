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

import math
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.epr.util import create_bulk_and_mer_partition_regions


def partition_regions(simulation):
    """Returns list of PartitionRegion objects for Circular Transmon Single Island EPR simulation."""

    regions = []

    # Coupler partition regions - one for each coupler
    for i, (c_angle, c_arc_ampl) in enumerate(zip(simulation.couplers_angle, simulation.couplers_arc_amplitude)):
        # Create pizza slice shape for each coupler
        c_angle_rad = math.radians(float(c_angle))
        c_arc_ampl_rad = math.radians(float(c_arc_ampl))

        # Inner radius (closer to qubit center, with some margin)
        inner_radius = simulation.r_island - 10
        # Outer radius (extends beyond coupler, with extra space)
        outer_radius = simulation.r_island + simulation.ground_gap + 20

        # Angular extent with extra margin
        half_angle = c_arc_ampl_rad / 2 + math.radians(10)  # Extra 10 degrees on each side

        # Create pizza slice polygon without center point to avoid zero width lines
        points = []

        # Add arc points for outer edge
        n_points = 32
        for j in range(n_points + 1):
            angle = c_angle_rad - half_angle + (2 * half_angle * j) / n_points
            x = outer_radius * math.cos(angle)
            y = outer_radius * math.sin(angle)
            points.append(pya.DPoint(x, y) + simulation.refpoints["base"])

        # Add arc points for inner edge (reverse direction)
        for j in range(n_points, -1, -1):
            angle = c_angle_rad - half_angle + (2 * half_angle * j) / n_points
            x = inner_radius * math.cos(angle)
            y = inner_radius * math.sin(angle)
            points.append(pya.DPoint(x, y) + simulation.refpoints["base"])

        coupler_region = pya.DPolygon(points)

        regions += create_bulk_and_mer_partition_regions(
            name=f"{i}cplr",
            face=simulation.face_ids[0],
            metal_edge_dimensions=2.0,
            region=coupler_region,
            vertical_dimensions=3.0,
            bulk=False,
            visualise=True,
        )

    # Junction hall partition region
    squid_angle_rad = math.radians(simulation.squid_angle)
    hall_length = simulation.ground_gap + 10  # Extra space
    hall_width = 8 + 4  # Junction hall width + extra space

    # Create rotated rectangle for junction hall
    hall_rect = pya.DPolygon(
        [
            pya.DPoint(-hall_width / 2, 0),
            pya.DPoint(hall_width / 2, 0),
            pya.DPoint(hall_width / 2, hall_length),
            pya.DPoint(-hall_width / 2, hall_length),
        ]
    )

    # Position at island edge and rotate
    junction_pos = pya.DPoint(
        simulation.r_island * math.cos(squid_angle_rad), simulation.r_island * math.sin(squid_angle_rad)
    )

    hall_transform = pya.DCplxTrans(1, simulation.squid_angle - 90, False, junction_pos + simulation.refpoints["base"])
    hall_region = hall_transform * hall_rect

    regions += create_bulk_and_mer_partition_regions(
        name="leads",
        face=simulation.face_ids[0],
        metal_edge_dimensions=2.0,
        region=hall_region,
        vertical_dimensions=3.0,
        bulk=False,
        visualise=True,
    )

    # Main island complement region
    regions += create_bulk_and_mer_partition_regions(
        name="bcomplement",
        face=simulation.face_ids[0],
        metal_edge_dimensions=2.0,
        region=None,
        vertical_dimensions=3.0,
        bulk=False,
        visualise=True,
    )

    return regions


def correction_cuts(simulation):
    """Returns dictionary of correction cuts for Circular Transmon Single Island EPR simulation."""

    cuts = {}

    # Coupler correction cuts
    for i, (c_angle, c_arc_ampl) in enumerate(zip(simulation.couplers_angle, simulation.couplers_arc_amplitude)):
        c_angle_rad = math.radians(float(c_angle))
        c_arc_ampl_rad = math.radians(float(c_arc_ampl))

        # Cut  outside the hall and cross the coupler slightly on the side
        # mid angle between current cut position and coupler arc amplitude
        half_arc = c_arc_ampl_rad / 2
        cut_angle_offset = half_arc / 2  # Halfway between center and arc edge
        cut_angle = c_angle_rad + cut_angle_offset  # Offset to the side

        # Cut from outside qubit through coupler to island center
        # Start outside the qubit
        outer_point = pya.DPoint(
            (simulation.r_island + simulation.ground_gap + 15) * math.cos(cut_angle),
            (simulation.r_island + simulation.ground_gap + 15) * math.sin(cut_angle),
        )

        # End at island edge
        inner_point = pya.DPoint(
            (simulation.r_island - 10) * math.cos(cut_angle), (simulation.r_island - 10) * math.sin(cut_angle)
        )

        cuts[f"{i}cplrmer"] = {
            "p1": outer_point + simulation.refpoints["base"],
            "p2": inner_point + simulation.refpoints["base"],
        }

    # Junction hall correction cut
    squid_angle_rad = math.radians(simulation.squid_angle)

    # Cut across the width of junction hall
    hall_center = pya.DPoint(
        (simulation.r_island + simulation.ground_gap / 2) * math.cos(squid_angle_rad),
        (simulation.r_island + simulation.ground_gap / 2) * math.sin(squid_angle_rad),
    )

    # Perpendicular direction to junction hall
    perp_angle = squid_angle_rad + math.pi / 2
    cut_length = 15

    p1 = pya.DPoint(
        hall_center.x + cut_length * math.cos(perp_angle), hall_center.y + cut_length * math.sin(perp_angle)
    )
    p2 = pya.DPoint(
        hall_center.x - cut_length * math.cos(perp_angle), hall_center.y - cut_length * math.sin(perp_angle)
    )

    cuts["leadsmer"] = {
        "p1": p1 + simulation.refpoints["base"],
        "p2": p2 + simulation.refpoints["base"],
        "boundary_conditions": {"xmin": {"potential": 0}, "xmax": {"potential": 0}},
    }

    # Main island complement correction cut
    # direction that avoids couplers and junction
    # angle opposite to junction
    complement_angle = math.radians(simulation.squid_angle + 180)

    # Check if this angle conflicts with any coupler
    min_angular_distance = 360
    for c_angle in simulation.couplers_angle:
        angular_dist = abs(float(c_angle) - (simulation.squid_angle + 180))
        if angular_dist > 180:
            angular_dist = 360 - angular_dist
        min_angular_distance = min(min_angular_distance, angular_dist)

    # Close to the coupler
    if min_angular_distance < 30:  # Less than 30 degrees separation
        complement_angle = math.radians(simulation.squid_angle + 150)

    # Cut from island to outside qubit
    # points equidistant from the gap region
    gap_distance = 10  # Same distance from gap as outer point

    inner_point = pya.DPoint(
        (simulation.r_island - gap_distance) * math.cos(complement_angle),
        (simulation.r_island - gap_distance) * math.sin(complement_angle),
    )
    outer_point = pya.DPoint(
        (simulation.r_island + simulation.ground_gap + gap_distance) * math.cos(complement_angle),
        (simulation.r_island + simulation.ground_gap + gap_distance) * math.sin(complement_angle),
    )

    cuts["bcomplementmer"] = {
        "p1": inner_point + simulation.refpoints["base"],
        "p2": outer_point + simulation.refpoints["base"],
    }

    return cuts
