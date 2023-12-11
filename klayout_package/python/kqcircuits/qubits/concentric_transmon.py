# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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
from kqcircuits.pya_resolver import pya
from kqcircuits.qubits.qubit import Qubit
from kqcircuits.util.geometry_helper import circle_polygon, arc_points
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.util.refpoints import WaveguideToSimPort, JunctionSimPort


@add_parameters_from(Element, n=180)
class ConcentricTransmon(Qubit):
    """The PCell declaration for a concentric transmon.
    A concentric transmon consists of two islands, one inner and one outer, connected by a Josephson Junction/s.
    Multiple couplers can be defined. They can have custom waveguide impedance, size and shape.
    Each coupler has reference points, numbered starting from 1. Driveline can be connected to the drive port.

    """
    # Qubit geometry
    r_inner = Param(pdt.TypeDouble, "Internal island radius", 120, unit="μm",
                    docstring="Radius of the outer edge of the inner island")
    r_outer = Param(pdt.TypeDouble, "External island radius, measured at the outer edge", 250, unit="μm",
                    docstring="Radius of the external qubit island")
    outer_island_width = Param(pdt.TypeDouble, "Outer island radial width", 80, unit="μm",
                               docstring="Width of the external island")
    ground_gap = Param(pdt.TypeDouble, "Ground plane padding", 80, unit="μm")
    squid_angle = Param(pdt.TypeDouble, "Angular position of the Josephson Junction/s, where the positive x-axis",
                        120, unit="degrees")

    # Couplers parameters (the list size define the number of couplers)
    couplers_r = Param(pdt.TypeDouble, "Radius of the couplers positioning", 290, unit="[μm]")
    couplers_a = Param(pdt.TypeList, "Width of the coupler waveguide's center conductors", [10, 3, 4.5], unit="[μm]")
    couplers_b = Param(pdt.TypeList, "Width of the coupler waveguide's gaps", [6, 32, 20], unit="[μm]")
    couplers_angle = Param(pdt.TypeList,
                           "Positioning angles of the couplers, where 0deg corresponds to positive x-axis",
                           [340, 60, 210], unit="[degrees]")
    couplers_width = Param(pdt.TypeList, "Radial widths of the arc couplers", [10, 20, 30], unit="[μm]")
    couplers_arc_amplitude = Param(pdt.TypeList, "Couplers angular extension", [35, 45, 15], unit="[degrees]")

    # Drive port parameters
    drive_angle = Param(pdt.TypeDouble, "Angle of the drive port, where 0deg corresponds to positive x-axis", 300,
                        unit="degrees")
    drive_distance = Param(pdt.TypeDouble, "Distance of the driveline, measured from qubit centre", 400, unit="µm")

    def build(self):
        self.x_end = self.r_outer + self.ground_gap  # Define the outermost qubit coordinate

        # Generate the qubit islands (they are the negative shape of the final geometry)
        qubit_negative = self._make_qubit_islands()

        # Generate the coupler islands
        coupler_islands_region = self._make_coupler_island()

        # Add the waveguides connecting the couplers to external waveguides
        waveguide, waveguide_gap = self._make_waveguides()

        # Add the Josephson Junction/s
        self._add_junction(qubit_negative)

        # Define the capacitor in the ground (final polarity)
        ground_region = self._make_ground_region()
        qubit = ground_region - qubit_negative + waveguide_gap - coupler_islands_region - \
                waveguide  # Operations order is important!
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(qubit)

        # Protection region from the ground grid
        region_protection = self._get_protection_region(ground_region)
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(region_protection)

        # Couplers and driveline ports
        self._add_ports()

    def _make_arc_island(self, island_outer_radius, island_width, swept_angle):
        # Generate a polygon arc of any size and angle
        angle_rad = math.radians(swept_angle)
        points_outside = arc_points(island_outer_radius, -angle_rad / 2, angle_rad / 2, self.n)
        points_inside = arc_points(island_outer_radius - island_width, angle_rad / 2, -angle_rad / 2, self.n)
        points = points_inside + points_outside
        arc_island = pya.DPolygon(points)
        return arc_island

    def _make_qubit_islands(self):
        # Generate a region of the qubit shunting capacitor
        capacitor_islands = []
        # Inner circular island
        inner_island = circle_polygon(self.r_inner, self.n)
        capacitor_islands.append(inner_island)
        # Outer cylindrical island
        outer_island = self._make_arc_island(self.r_outer, self.outer_island_width, 360)
        capacitor_islands.append(outer_island)
        return pya.Region([poly.to_itype(self.layout.dbu) for poly in capacitor_islands])

    def _make_coupler_island(self):
        # Generate the regions of the coupler islands.
        round_corner = 5
        coupler_islands_region = pya.Region()
        # Generate all the couplers in the same region
        for (c_angle, c_width, c_arc_ampl) in zip(self.couplers_angle, self.couplers_width,
                                                  self.couplers_arc_amplitude):
            coupler_island = self._make_arc_island(self.couplers_r + float(c_width) / 2, float(c_width),
                                                   float(c_arc_ampl))
            coupler_island_region = pya.Region(coupler_island.to_itype(self.layout.dbu)).round_corners(
                round_corner / self.layout.dbu, round_corner / self.layout.dbu, self.n).transformed(
                pya.ICplxTrans(1, float(c_angle), False, 0, 0))
            coupler_islands_region += coupler_island_region
        return coupler_islands_region

    def _make_waveguides(self):
        # Make the waveguides for each coupler with custom impedance and return the region
        waveguides_signal_region = pya.Region()
        waveguides_gap_region = pya.Region()
        # Add the waveguides inside the ground padding
        overlapping_margin = 0.5
        for (c_a, c_b, c_angle) in zip(self.couplers_a, self.couplers_b, self.couplers_angle):
            waveguide_signal = pya.Region(pya.DPolygon([
                pya.DPoint(self.x_end + overlapping_margin, float(c_a) / 2),
                pya.DPoint(self.couplers_r, float(c_a) / 2),
                pya.DPoint(self.couplers_r, -float(c_a) / 2),
                pya.DPoint(self.x_end + overlapping_margin, -float(c_a) / 2),
            ]).to_itype(self.layout.dbu)).transformed(pya.ICplxTrans(1, float(c_angle), False, 0, 0))
            waveguide_gap = pya.Region(pya.DPolygon([
                pya.DPoint(self.x_end, float(c_a) / 2 + float(c_b)),
                pya.DPoint(self.couplers_r, float(c_a) / 2 + float(c_b)),
                pya.DPoint(self.couplers_r, -float(c_a) / 2 - float(c_b)),
                pya.DPoint(self.x_end, -float(c_a) / 2 - float(c_b)),
            ]).to_itype(self.layout.dbu)).transformed(pya.ICplxTrans(1, float(c_angle), False, 0, 0))
            waveguides_signal_region += waveguide_signal
            waveguides_gap_region += waveguide_gap
        return waveguides_signal_region, waveguides_gap_region

    def _add_junction(self, region):
        # Add the junction to the qubit islands
        squid_origin = \
            arc_points(self.r_outer - self.outer_island_width, self.squid_angle * math.pi / 180, 2 * math.pi, self.n,
                       pya.DPoint(0, 0))[0]
        squid_transf = pya.DCplxTrans(1, self.squid_angle + 90, False, squid_origin)
        self.produce_squid(squid_transf)
        squid_distance_from_centre = self.refpoints['squid_port_common'].distance(self.refpoints['base'])
        # Connect the junction to the inner island
        squid_connection = pya.Region(squid_transf * pya.DPolygon([
            pya.DPoint(-4, 0),
            pya.DPoint(-4, -squid_distance_from_centre - 0.5),
            pya.DPoint(4, -squid_distance_from_centre - 0.5),
            pya.DPoint(4, 0)]
        ).to_itype(self.layout.dbu))
        region += squid_connection

    def _make_ground_region(self):
        # Generate the ground region as a filled circle of the maximum size
        return pya.Region(circle_polygon(self.x_end, self.n).to_itype(self.layout.dbu))

    def _add_ports(self):
        # Add couplers ports
        for i, c_angle in enumerate(map(float, self.couplers_angle)):
            coupler_origin = arc_points(self.x_end, c_angle * math.pi / 180, 2 * math.pi, self.n, pya.DPoint(0, 0))[0]
            coupler_transf = pya.DCplxTrans(1, 90 + c_angle, False, coupler_origin)
            self.add_port(f"coupler_{i + 1}", coupler_transf * pya.DPoint(0, 0),
                          direction=pya.DVector(coupler_transf * pya.DPoint(0, 0)))
        # Add driveline port
        drive_origin = arc_points(self.drive_distance, self.drive_angle * math.pi / 180, 2 * math.pi, self.n,
                                  pya.DPoint(0, 0))[0]
        drive_transf = pya.DCplxTrans(1, 90 + self.drive_angle, False, drive_origin)
        self.add_port("drive", drive_transf * pya.DPoint(0, 0), direction=pya.DVector(drive_transf * pya.DPoint(0, 0)))

    def _get_protection_region(self, region):
        # Region which we don't want to cover with the automatically generated ground grid
        protection_region = region.sized(self.margin / self.layout.dbu, self.margin / self.layout.dbu, 2)
        return protection_region

    @classmethod
    def get_sim_ports(cls, simulation):
        ports = [JunctionSimPort()]
        return ports + [WaveguideToSimPort(f"port_coupler_{i+1}", side="bottom",
                                           a=simulation.couplers_a[i],
                                           b=simulation.couplers_b[i]) for i in range(len(simulation.couplers_angle))]
