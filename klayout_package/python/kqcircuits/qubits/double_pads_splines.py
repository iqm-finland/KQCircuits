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


from kqcircuits.util.geometry_helper import bspline_points
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.qubits.double_pads import DoublePads
from kqcircuits.pya_resolver import pya

class DoublePadsSplines(DoublePads):
    """A two-island qubit, consisting of two spline-constructed islands shunted by a junction,
    with one capacitive coupler.

    Contains a coupler on the north edge and two separate qubit islands in the center
    joined by a junction or SQUID loaded from another library.
    Refpoint for a readout line at the opening to the coupler and a modifiable refpoint for
    a driveline outside of the rectangle.
    """

    island_spline = Param(pdt.TypeList, "Control points of a B-Spline that defines left half of the island",
        [-250, 20, -250, 80, -100, 100, 0, 100])
    island_spline_samples = Param(pdt.TypeInt, "Number of samples taken from each island spline", 100,
        docstring=( "Number of samples taken from each island spline. "
                    "There is a spline for each consequent series of four control points"))


    def _build_island1(self, squid_height):
        island1_bottom = self.squid_offset + squid_height / 2
        curve_start = pya.DPoint(0, island1_bottom + self.island1_taper_height)
        island1_control_points = [curve_start + pya.DPoint(-self.island1_taper_width / 2, 0)] + \
            [curve_start + pya.DPoint(float(self.island_spline[idx]), float(self.island_spline[idx+1]))
                for idx in range(0, len(self.island_spline), 2)]
        island1_control_points += [pya.DPoint(-p.x, p.y) for p in reversed(island1_control_points[:-1])]
        for i, p in enumerate(island1_control_points):
            self.refpoints[f"island1_control_point_{i}"] = p
        island1_polygon = pya.DPolygon(bspline_points(island1_control_points,
                                                        self.island_spline_samples,
                                                        startpoint=True, endpoint=True))
        island1_region = pya.Region(island1_polygon.to_itype(self.layout.dbu))
        island1_taper = pya.Region(pya.DPolygon([
            #pertrude taper into island in case of precision errors
            pya.DPoint( self.island1_taper_width / 2, island1_bottom + self.island1_taper_height + 1),
            pya.DPoint( self.island1_taper_width / 2, island1_bottom + self.island1_taper_height),
            pya.DPoint( self.island1_taper_junction_width / 2, island1_bottom),
            pya.DPoint(-self.island1_taper_junction_width / 2, island1_bottom),
            pya.DPoint(-self.island1_taper_width / 2, island1_bottom + self.island1_taper_height),
            #pertrude taper into island in case of precision errors
            pya.DPoint(-self.island1_taper_width / 2, island1_bottom + self.island1_taper_height + 1),
        ]).to_itype(self.layout.dbu))
        return island1_region + island1_taper


    def _build_island2(self, squid_height):
        island2_top = self.squid_offset - squid_height / 2
        curve_start = pya.DPoint(0, island2_top - self.island2_taper_height)
        island2_control_points = [curve_start + pya.DPoint(-self.island2_taper_width / 2, 0)] + \
            [curve_start + pya.DPoint(float(self.island_spline[idx]), -float(self.island_spline[idx+1]))
                for idx in range(0, len(self.island_spline), 2)]
        island2_control_points += [pya.DPoint(-p.x, p.y) for p in reversed(island2_control_points[:-1])]
        for i, p in enumerate(island2_control_points):
            self.refpoints[f"island2_control_point_{i}"] = p
        island2_polygon = pya.DPolygon(bspline_points(island2_control_points,
                                                        self.island_spline_samples,
                                                        startpoint=True, endpoint=True))
        island2_region = pya.Region(island2_polygon.to_itype(self.layout.dbu))
        island2_taper = pya.Region(pya.DPolygon([
            #pertrude taper into island in case of precision errors
            pya.DPoint( self.island2_taper_width / 2, island2_top - self.island2_taper_height - 1),
            pya.DPoint( self.island2_taper_width / 2, island2_top - self.island2_taper_height),
            pya.DPoint( self.island2_taper_junction_width / 2, island2_top),
            pya.DPoint(-self.island2_taper_junction_width / 2, island2_top),
            pya.DPoint(-self.island2_taper_width / 2, island2_top - self.island2_taper_height),
            #pertrude taper into island in case of precision errors
            pya.DPoint(-self.island2_taper_width / 2, island2_top - self.island2_taper_height - 1),
        ]).to_itype(self.layout.dbu))
        return island2_region + island2_taper
