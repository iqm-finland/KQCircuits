# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).


import math

from kqcircuits.elements.element import Element
from kqcircuits.junctions.squid import Squid
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.qubits.qubit import Qubit
from kqcircuits.pya_resolver import pya

@add_parameters_from(Squid, junction_type="Manhattan Single Junction")
class DoublePads(Qubit):
    """A two-island qubit, consisting of two rounded rectangles shunted by a junction, with one capacitive coupler.

    Contains a coupler on the north edge and two separate qubit islands in the center
    joined by a junction or SQUID loaded from another library.
    Refpoint for a readout line at the opening to the coupler and a modifiable refpoint for
    a driveline outside of the rectangle.
    """

    ground_gap = Param(pdt.TypeList, "Width, height of the ground gap (µm, µm)", [700, 700])
    ground_gap_r = Param(pdt.TypeDouble, "Ground gap rounding radius", 50, unit="μm")
    coupler_extent = Param(pdt.TypeList, "Width, height of the coupler (µm, µm)", [150, 20])
    coupler_r = Param(pdt.TypeDouble, "Coupler rounding radius", 10, unit="μm")
    coupler_a = Param(pdt.TypeDouble, "Width of the coupler waveguide center conductor", Element.a, unit="μm")
    coupler_offset = Param(pdt.TypeDouble, "Distance from first qubit island to coupler", 20, unit="μm")
    squid_offset = Param(pdt.TypeDouble, "Offset between SQUID center and qubit center", 0, unit="μm")
    island1_extent = Param(pdt.TypeList, "Width, height of the first qubit island (µm, µm)", [500, 100])
    island1_r = Param(pdt.TypeDouble, "First qubit island rounding radius", 50, unit="μm")
    island2_extent = Param(pdt.TypeList, "Width, height of the second qubit island (µm, µm)", [500, 100])
    island2_r = Param(pdt.TypeDouble, "Second qubit island rounding radius", 50, unit="μm")
    drive_position = Param(pdt.TypeList, "Coordinate for the drive port (µm, µm)", [-450, 0])

    def build(self):
        # Qubit base
        ground_gap_points = [
            pya.DPoint( float(self.ground_gap[0]) / 2,  float(self.ground_gap[1]) / 2),
            pya.DPoint( float(self.ground_gap[0]) / 2, -float(self.ground_gap[1]) / 2),
            pya.DPoint(-float(self.ground_gap[0]) / 2, -float(self.ground_gap[1]) / 2),
            pya.DPoint(-float(self.ground_gap[0]) / 2,  float(self.ground_gap[1]) / 2),
        ]
        ground_gap_polygon = pya.DPolygon(ground_gap_points)
        ground_gap_region = pya.Region(ground_gap_polygon.to_itype(self.layout.dbu))
        ground_gap_region.round_corners(self.ground_gap_r / self.layout.dbu,
            self.ground_gap_r / self.layout.dbu, self.n)

        # SQUID
        # Create temporary SQUID cell to calculate SQUID height
        temp_squid_cell = self.add_element(Squid, junction_type=self.junction_type)
        temp_squid_ref = self.get_refpoints(temp_squid_cell)
        squid_height = temp_squid_ref["port_common"].distance(pya.DPoint(0, 0))
        # Now actually add SQUID
        squid_transf = pya.DCplxTrans(1, 0, False, pya.DVector(0, self.squid_offset - squid_height / 2))
        self.produce_squid(squid_transf)

        # First island
        island1_polygon = pya.DPolygon([
            pya.DPoint(-float(self.island1_extent[0]) / 2,
                self.squid_offset + squid_height / 2 + float(self.island1_extent[1])),
            pya.DPoint( float(self.island1_extent[0]) / 2,
                self.squid_offset + squid_height / 2 + float(self.island1_extent[1])),
            pya.DPoint( float(self.island1_extent[0]) / 2, self.squid_offset + squid_height / 2),
            pya.DPoint(-float(self.island1_extent[0]) / 2, self.squid_offset + squid_height / 2),
        ])
        island1_region = pya.Region(island1_polygon.to_itype(self.layout.dbu))
        island1_region.round_corners(self.island1_r / self.layout.dbu, self.island1_r / self.layout.dbu, self.n)

        # Second island
        island2_polygon = pya.DPolygon([
            pya.DPoint(-float(self.island2_extent[0]) / 2,
                self.squid_offset - squid_height / 2 - float(self.island2_extent[1])),
            pya.DPoint( float(self.island2_extent[0]) / 2,
                self.squid_offset - squid_height / 2 - float(self.island2_extent[1])),
            pya.DPoint( float(self.island2_extent[0]) / 2, self.squid_offset - squid_height / 2),
            pya.DPoint(-float(self.island2_extent[0]) / 2, self.squid_offset - squid_height / 2),
        ])
        island2_region = pya.Region(island2_polygon.to_itype(self.layout.dbu))
        island2_region.round_corners(self.island2_r / self.layout.dbu, self.island2_r / self.layout.dbu, self.n)

        # Coupler gap
        coupler_region = self._build_coupler(self.squid_offset + squid_height / 2 + float(self.island1_extent[1]))

        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(
            ground_gap_region - coupler_region - island1_region - island2_region
        )

        # Protection
        protection_polygon = pya.DPolygon([
            p + pya.DVector(
                    math.copysign(self.margin, p.x),
                    math.copysign(self.margin, p.y)
            ) for p in ground_gap_points
        ])
        protection_region = pya.Region(protection_polygon.to_itype(self.layout.dbu))
        protection_region.round_corners(
            (self.ground_gap_r + self.margin) / self.layout.dbu,
            (self.ground_gap_r + self.margin) / self.layout.dbu,
            self.n
        )
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(protection_region)

        # Coupler port
        self.add_port("cplr", pya.DPoint(0, float(self.ground_gap[1]) / 2))

        # Drive port
        self.add_port("drive", pya.DPoint(float(self.drive_position[0]), float(self.drive_position[1])))


    def _build_coupler(self, first_island_top_edge):
        coupler_top_edge = first_island_top_edge + self.coupler_offset + float(self.coupler_extent[1])
        coupler_polygon = pya.DPolygon([
            pya.DPoint(-float(self.coupler_extent[0]) / 2, coupler_top_edge),
            pya.DPoint(-float(self.coupler_extent[0]) / 2, first_island_top_edge + self.coupler_offset),
            pya.DPoint( float(self.coupler_extent[0]) / 2, first_island_top_edge + self.coupler_offset),
            pya.DPoint( float(self.coupler_extent[0]) / 2, coupler_top_edge),
        ])
        coupler_region = pya.Region(coupler_polygon.to_itype(self.layout.dbu))
        coupler_region.round_corners(self.coupler_r / self.layout.dbu, self.coupler_r / self.layout.dbu, self.n)
        coupler_path_polygon = pya.DPolygon([
            pya.DPoint(-self.coupler_a / 2, (float(self.ground_gap[1]) / 2)),
            pya.DPoint( self.coupler_a / 2, (float(self.ground_gap[1]) / 2)),
            pya.DPoint( self.coupler_a / 2, coupler_top_edge),
            pya.DPoint(-self.coupler_a / 2, coupler_top_edge),
        ])
        coupler_path = pya.Region(coupler_path_polygon.to_itype(self.layout.dbu))
        return coupler_region + coupler_path
