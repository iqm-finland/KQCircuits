# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
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

from itertools import permutations

import pytest

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.util import get_enclosing_polygon
from kqcircuits.simulations.port import InternalPort
from kqcircuits.simulations.simulation import Simulation


def _signed_area(points):
    """Return the signed area; clockwise polygons have negative area."""
    x, y = points[0][:2]
    relative = [(point[0] - x, point[1] - y) for point in points]
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(relative, relative[1:] + relative[:1])) / 2


@pytest.mark.parametrize(
    "points,area",
    [
        ([[0, 0], [10, 0], [10, 10], [20, 20]], 100),
        ([[0, 0], [0, 10], [10, 0], [20, 0]], 100),
        ([[0, 0], [0, 10], [10, 10], [10, 0]], 100),
        ([[0, 0], [10, 0], [5, 2], [5, 10]], 30),
        ([[0.0, 0.0], [0.001, 0.0], [0.001, 0.003], [0.003, 0.009]], 4.5e-6),
        ([[5000.0, 5000.0], [5000.001, 5000.0], [5000.001, 5000.003], [5000.003, 5000.009]], 4.5e-6),
    ],
)
def test_enclosing_polygon_preserves_area_and_clockwise_winding(points, area):
    """Collinear boundary points must not cause a polygon to backtrack."""
    for permutation in permutations(points):
        ordered = get_enclosing_polygon(list(permutation))
        assert ordered[0] == min(points)
        assert sorted(ordered) == sorted(points)
        assert _signed_area(ordered) == pytest.approx(-area, rel=1e-8, abs=0)


class AngledPortSimulation(Simulation):
    """A signal island facing a diagonal ground edge."""

    def build(self):
        """Insert two metal regions separated by an internal port."""
        dbu = self.layout.dbu
        signal = pya.Region(pya.DPolygon([pya.DPoint(0, 0), pya.DPoint(10, 0), pya.DPoint(5, -5)]).to_itype(dbu))
        ground = pya.Region(
            pya.DPolygon(
                [
                    pya.DPoint(10, 10),
                    pya.DPoint(20, 20),
                    pya.DPoint(30, 20),
                    pya.DPoint(30, -10),
                    pya.DPoint(20, -10),
                ]
            ).to_itype(dbu)
        )
        gap = pya.Region(self.box.to_itype(dbu)) - (signal + ground)
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(gap)
        self.ports.append(InternalPort(1, pya.DPoint(5, 0), pya.DPoint(15, 15)))


def test_internal_port_export_with_collinear_edge_endpoints(layout):
    """An angled port must export the full triangle, without an overlapping edge."""
    simulation = AngledPortSimulation(
        layout, box=pya.DBox(-30, -30, 30, 30), polygon_tolerance=0, minimum_point_spacing=0
    )
    polygon = simulation.get_port_data()[0]["polygon"]
    assert _signed_area(polygon) == -100
    assert all(point[2] == 0 for point in polygon)
