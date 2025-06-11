# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

import math
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.partition_region import PartitionRegion
from kqcircuits.util.geometry_helper import arc_points


def partition_regions(simulation):
    """Returns list of PartitionRegion objects for Circular Transmon Single Island EPR simulation."""
    
    regions = []
    
    # Coupler partition regions - one for each coupler
    for i, (c_angle, c_width, c_arc_ampl) in enumerate(
        zip(simulation.couplers_angle, simulation.couplers_width, simulation.couplers_arc_amplitude)
    ):
        # Create pizza slice shape for each coupler
        c_angle_rad = math.radians(float(c_angle))
        c_arc_ampl_rad = math.radians(float(c_arc_ampl))
        
        # Inner radius (closer to qubit center, with some margin)
        inner_radius = simulation.r_island - 10
        # Outer radius (extends beyond coupler, with extra space)
        outer_radius = simulation.r_island + simulation.ground_gap + 20
        
        # Angular extent with extra margin
        half_angle = c_arc_ampl_rad / 2 + math.radians(10)  # Extra 10 degrees on each side
        
        # Create pizza slice polygon
        points = [pya.DPoint(0, 0)]  # Center point
        
        # Add arc points for outer edge
        n_points = 32
        for j in range(n_points + 1):
            angle = c_angle_rad - half_angle + (2 * half_angle * j) / n_points
            x = outer_radius * math.cos(angle)
            y = outer_radius * math.sin(angle)
            points.append(pya.DPoint(x, y))
        
        # Add arc points for inner edge (reverse direction)
        for j in range(n_points, -1, -1):
            angle = c_angle_rad - half_angle + (2 * half_angle * j) / n_points
            x = inner_radius * math.cos(angle)
            y = inner_radius * math.sin(angle)
            points.append(pya.DPoint(x, y))
        
        coupler_region = pya.DPolygon(points)
        
        regions.append(PartitionRegion(
            name=f"{i}cplrmer",
            region=coupler_region,
            metal_edge_dimensions=2.0,
            visualise=True
        ))
    
    # Junction hall partition region
    squid_angle_rad = math.radians(simulation.squid_angle)
    hall_length = simulation.ground_gap + 10  # Extra space
    hall_width = 8 + 4  # Junction hall width + extra space
    
    # Create rotated rectangle for junction hall
    hall_rect = pya.DPolygon([
        pya.DPoint(-hall_width/2, 0),
        pya.DPoint(hall_width/2, 0),
        pya.DPoint(hall_width/2, hall_length),
        pya.DPoint(-hall_width/2, hall_length)
    ])
    
    # Position at island edge and rotate
    junction_pos = pya.DPoint(
        simulation.r_island * math.cos(squid_angle_rad),
        simulation.r_island * math.sin(squid_angle_rad)
    )
    
    hall_transform = pya.DCplxTrans(1, simulation.squid_angle - 90, False, junction_pos)
    hall_region = hall_transform * hall_rect
    
    regions.append(PartitionRegion(
        name="leadsmer",
        region=hall_region,
        metal_edge_dimensions=2.0,
        visualise=True
    ))
    
    # Main island complement region (covers everything not covered by above regions)
    regions.append(PartitionRegion(
        name="bcomplementmer",
        region=None,  # Entire element extent
        metal_edge_dimensions=2.0,
        visualise=True
    ))
    
    return regions


def correction_cuts(simulation):
    """Returns dictionary of correction cuts for Circular Transmon Single Island EPR simulation."""
    
    cuts = {}
    
    # Coupler correction cuts
    for i, (c_angle, c_arc_ampl) in enumerate(
        zip(simulation.couplers_angle, simulation.couplers_arc_amplitude)
    ):
        c_angle_rad = math.radians(float(c_angle))
        
        # Cut from outside qubit through coupler to island center
        # Start outside the qubit
        outer_point = pya.DPoint(
            (simulation.r_island + simulation.ground_gap + 15) * math.cos(c_angle_rad),
            (simulation.r_island + simulation.ground_gap + 15) * math.sin(c_angle_rad)
        )
        
        # End at island edge
        inner_point = pya.DPoint(
            (simulation.r_island - 10) * math.cos(c_angle_rad),
            (simulation.r_island - 10) * math.sin(c_angle_rad)
        )
        
        cuts[f"{i}cplrmer"] = {
            "p1": outer_point,
            "p2": inner_point
        }
    
    # Junction hall correction cut
    squid_angle_rad = math.radians(simulation.squid_angle)
    
    # Cut across the width of junction hall
    hall_center = pya.DPoint(
        (simulation.r_island + simulation.ground_gap/2) * math.cos(squid_angle_rad),
        (simulation.r_island + simulation.ground_gap/2) * math.sin(squid_angle_rad)
    )
    
    # Perpendicular direction to junction hall
    perp_angle = squid_angle_rad + math.pi/2
    cut_length = 15  # Extend beyond hall width
    
    p1 = pya.DPoint(
        hall_center.x + cut_length * math.cos(perp_angle),
        hall_center.y + cut_length * math.sin(perp_angle)
    )
    p2 = pya.DPoint(
        hall_center.x - cut_length * math.cos(perp_angle),
        hall_center.y - cut_length * math.sin(perp_angle)
    )
    
    cuts["leadsmer"] = {
        "p1": p1,
        "p2": p2,
        "boundary_conditions": {'xmin': {'potential': 0}, 'xmax': {'potential': 0}}
    }
    
    # Main island complement correction cut
    # Find a direction that avoids couplers and junction
    # Use angle opposite to junction
    complement_angle = math.radians(simulation.squid_angle + 180)
    
    # Check if this angle conflicts with any coupler
    min_angular_distance = 360
    for c_angle in simulation.couplers_angle:
        angular_dist = abs(float(c_angle) - (simulation.squid_angle + 180))
        if angular_dist > 180:
            angular_dist = 360 - angular_dist
        min_angular_distance = min(min_angular_distance, angular_dist)
    
    # If too close to a coupler, adjust angle
    if min_angular_distance < 30:  # Less than 30 degrees separation
        complement_angle = math.radians(simulation.squid_angle + 150)
    
    # Cut from island to outside qubit
    inner_point = pya.DPoint(
        simulation.r_island * math.cos(complement_angle),
        simulation.r_island * math.sin(complement_angle)
    )
    outer_point = pya.DPoint(
        (simulation.r_island + simulation.ground_gap + 10) * math.cos(complement_angle),
        (simulation.r_island + simulation.ground_gap + 10) * math.sin(complement_angle)
    )
    
    cuts["bcomplementmer"] = {
        "p1": inner_point,
        "p2": outer_point
    }
    
    return cuts
