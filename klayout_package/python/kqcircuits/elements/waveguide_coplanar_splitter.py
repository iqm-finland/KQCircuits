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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).
from math import cos, sin, pi, radians

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.util.geometry_helper import arc_points
from kqcircuits.elements.element import Element
from kqcircuits.elements.airbridges.airbridge import Airbridge


@add_parameters_from(Airbridge, "airbridge_type")
class WaveguideCoplanarSplitter(Element):
    """
    The PCell declaration of a multiway waveguide splitter. The number of ports is defined by the length of the
    parameter lists. Ports are labelled by letters starting from ``a``
    """
    lengths = Param(pdt.TypeList, "Waveguide length per port, measured from origin", [11, 11, 11])
    angles = Param(pdt.TypeList, "Angle of each port (degrees)", [0, 120, 240])
    use_airbridges = Param(pdt.TypeBoolean, "Use airbridges at a distance from the centre", False)
    bridge_distance = Param(pdt.TypeDouble, "Bridges distance from centre", 80)
    a_list = Param(pdt.TypeList, "Center conductor widths", [], unit="[μm]",
                   docstring="List of center conductor widths for each port."
                             " If empty, self.a will be used for all ports instead. [μm]")
    b_list = Param(pdt.TypeList, "Gap widths", [], unit="[μm]",
                   docstring="List of gap widths for each port."
                             " If empty, self.b will be used for all ports instead. [μm]")

    def build(self):

        gap_shapes = []
        trace_shapes = []
        avoidance_shapes = []

        # Tolerance to make sure that the trace shape is larger than the gap shape after integer conversion
        rounding_tolerance = 10 * self.layout.dbu

        # Convert a, b to lists of right length
        a_list = self.a_list if (len(self.a_list) > 0 and self.a_list[0] != "") else [self.a] * len(self.angles)
        b_list = self.b_list if (len(self.b_list) > 0 and self.b_list[0] != "") else [self.b] * len(self.angles)

        port_names = ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j')
        for length_str, angle_str, port_name, a, b in zip(self.lengths, self.angles, port_names, a_list, b_list):
            angle_deg = float(angle_str)
            angle_rad = radians(angle_deg)
            length = float(length_str)
            a = float(a)
            b = float(b)

            # Generate port shapes
            gap_shapes.append(self._get_port_shape(
                angle_rad=angle_rad,
                length=length,
                width=a + 2*b
            ).to_itype(self.layout.dbu))

            trace_shapes.append(self._get_port_shape(
                angle_rad=angle_rad,
                length=length + rounding_tolerance,
                width=a
            ).to_itype(self.layout.dbu))

            avoidance_shapes.append(self._get_port_shape(
                angle_rad=angle_rad,
                length=length + self.margin,
                width=a + 2*b + 2*self.margin
            ).to_itype(self.layout.dbu))

            # Port refpoints
            self.add_port(
                port_name,
                pya.DPoint(length*cos(angle_rad), length*sin(angle_rad)),
                pya.DVector(self.r*cos(angle_rad), self.r*sin(angle_rad))
            )

            # Waveguide length annotation
            self.cell.shapes(self.get_layer("waveguide_path")).insert(
                pya.DPath([self.refpoints[f"port_{port_name}"], self.refpoints["base"]], a)
            )

            # Airbridges
            if self.use_airbridges:
                ab_trans = pya.DCplxTrans(1, angle_deg, False,
                                          self.bridge_distance*cos(angle_rad),
                                          self.bridge_distance*sin(angle_rad))
                ab_cell = self.add_element(Airbridge, pad_length=14, pad_extra=2)
                self.insert_cell(ab_cell, ab_trans)

        # Merge and insert shapes
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(
            pya.Region(gap_shapes) - pya.Region(trace_shapes)
        )
        self.add_protection(pya.Region(avoidance_shapes).merged())

    def _get_port_shape(self, angle_rad, length, width):
        # Generate a shape consisting of a rectangle (length, width) starting at (0, 0), with a round cap at the origin
        # side.

        r = width/2  # Radius of round cap

        # Corner section
        points = arc_points(r, angle_rad + pi / 2, angle_rad + 3 * pi / 2, self.n)

        # Straight section
        points.append(pya.DPoint(length*cos(angle_rad) + r*cos(angle_rad - pi/2),
                                 length*sin(angle_rad) + r*sin(angle_rad - pi/2)))

        points.append(pya.DPoint(length*cos(angle_rad) + r*cos(angle_rad + pi/2),
                                 length*sin(angle_rad) + r*sin(angle_rad + pi/2)))

        return pya.DPolygon(points)
