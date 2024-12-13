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
from kqcircuits.simulations.epr.utils import in_gui, EPRTarget
from kqcircuits.simulations.partition_region import PartitionRegion
from kqcircuits.elements.finger_capacitor_square import eval_a2, eval_b2

vertical_dimension = 1.0
metal_edge_dimension = 1.0
waveguide_margin = 10.0
waveguide_length_scale = 5


def partition_regions(simulation: EPRTarget, prefix: str = "") -> list[PartitionRegion]:
    """
    Returns partition regions. Doesn't work in general with non-symmetric spiral capacitors.
    """
    rr = simulation.finger_width / 2 + simulation.ground_gap
    rr /= simulation.layout.dbu

    # Use modified SmoothCapacitor geometry to obtain partition regions on fingers
    finger_gaps = pya.Region(simulation.cell.begin_shapes_rec(simulation.get_layer("ground_grid_avoidance"))).sized(
        (-simulation.margin - simulation.ground_gap - simulation.finger_width / 2) / simulation.layout.dbu, 5
    )

    ra = simulation.a / 2 + simulation.b + waveguide_margin
    port_a = simulation.refpoints["port_a"]
    dir_a = waveguide_length_scale * (simulation.refpoints["port_a_corner"] - port_a)
    cross_a = ra / dir_a.abs() * pya.DVector(dir_a.y, -dir_a.x)
    wg_region = pya.Region(
        pya.DPolygon(
            [
                port_a - cross_a,
                port_a - cross_a + dir_a,
                port_a + cross_a + dir_a,
                port_a + cross_a,
            ]
        ).to_itype(simulation.layout.dbu)
    )
    rb = eval_a2(simulation) / 2 + eval_b2(simulation) + waveguide_margin
    port_b = simulation.refpoints["port_b"]
    dir_b = waveguide_length_scale * (simulation.refpoints["port_b_corner"] - port_b)
    cross_b = rb / dir_b.abs() * pya.DVector(dir_b.y, -dir_b.x)
    wg_region += pya.Region(
        pya.DPolygon(
            [
                port_b - cross_b,
                port_b - cross_b + dir_b,
                port_b + cross_b + dir_b,
                port_b + cross_b,
            ]
        ).to_itype(simulation.layout.dbu)
    )

    result = [
        PartitionRegion(
            name=f"{prefix}fingergmer",
            face=simulation.face_ids[0],
            metal_edge_dimensions=metal_edge_dimension,
            region=finger_gaps,
            vertical_dimensions=vertical_dimension,
            visualise=True,
        ),
        PartitionRegion(
            name=f"{prefix}waveguides",
            face=simulation.face_ids[0],
            region=wg_region,
            visualise=True,
        ),
        PartitionRegion(
            name=f"{prefix}groundgmer",
            face=simulation.face_ids[0],
            metal_edge_dimensions=metal_edge_dimension,
            vertical_dimensions=vertical_dimension,
            visualise=True,
        ),
    ]

    return result


def correction_cuts(simulation: EPRTarget, prefix: str = "") -> dict[str, dict]:
    """
    Returns correction cuts. Doesn't work in general with non-symmetric spiral capacitors.
    """

    base_rf = simulation.refpoints["base"]

    z_me = 0
    if not in_gui(simulation):
        if len(simulation.face_stack) > 1:
            z_me = -simulation.substrate_height[1] - simulation.chip_distance - 2 * simulation.metal_height

    gaps = pya.Region(simulation.cell.begin_shapes_rec(simulation.get_layer("base_metal_gap_wo_grid")))
    top_most = None
    center_most = None
    for polygon in gaps.each():
        d_poly = polygon.to_dtype(simulation.layout.dbu)
        points = [(e.p1 + e.p2) / 2 for e in d_poly.each_edge()] + list(d_poly.each_point_hull())
        for p in points:
            if top_most is None or p.y > top_most.y:
                top_most = p
            if center_most is None or p.distance(base_rf) < center_most.distance(base_rf):
                center_most = p

    center_dir = 2 * (center_most - base_rf)
    center_gap_len = center_dir.abs()
    center_dir /= center_gap_len
    half_cut_len = 25.0
    result = {
        f"{prefix}fingergmer": {
            "p1": center_most + simulation.finger_width * 0.9 * center_dir,
            "p2": center_most - center_dir * (center_gap_len + simulation.finger_width * 0.9),
            "metal_edges": [
                {"x": simulation.finger_width * 0.9, "z": z_me},
                {"x": center_gap_len + simulation.finger_width * 0.9, "z": z_me},
            ],
        },
        f"{prefix}groundgmer": {
            "p1": top_most + pya.DPoint(0, half_cut_len),
            "p2": top_most - pya.DPoint(0, simulation.ground_gap + simulation.finger_width * 0.9),
            "metal_edges": [
                {"x": half_cut_len, "z": z_me},
                {"x": half_cut_len + simulation.ground_gap, "z": z_me},
            ],
        },
    }
    return result
