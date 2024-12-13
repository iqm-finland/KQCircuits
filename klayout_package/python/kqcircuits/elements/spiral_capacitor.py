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


from math import pi, cos, sqrt

from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare, eval_a2, eval_b2
from kqcircuits.elements.smooth_capacitor import SmoothCapacitor, unit_vector, segment_points
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import get_angle
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.elements.element import Element


@add_parameters_from(SmoothCapacitor, "a2", "b2", "finger_width", "finger_gap", "ground_gap")
class SpiralCapacitor(Element):
    """The PCell declaration for a spiral capacitor."""

    finger_width2 = Param(
        pdt.TypeDouble,
        "Width of a finger on the right",
        -1,
        unit="μm",
        docstring="Non-physical value '-1' means that same width is used on both sides.",
    )
    ground_gap2 = Param(
        pdt.TypeDouble,
        "Gap between ground and finger on the right",
        -1,
        unit="μm",
        docstring="Non-physical value '-1' means that same gap is used on both sides.",
    )

    spiral_angle = Param(pdt.TypeDouble, "Angle of spiral in degrees", 180, unit="degrees")
    spiral_angle2 = Param(
        pdt.TypeDouble,
        "Angle of spiral in degrees on the right",
        -1,
        unit="degrees",
        docstring="Non-physical value '-1' means that same angle is used on both sides.",
    )

    rotation = Param(
        pdt.TypeDouble,
        "Waveguide rotation in degrees",
        -1,
        unit="degrees",
        docstring="Non-physical value '-1' means that the waveguide points towards the spiral center.",
    )
    rotation2 = Param(
        pdt.TypeDouble,
        "Waveguide rotation in degrees on the right",
        -1,
        unit="degrees",
        docstring="Non-physical value '-1' means that the same rotation is used on both sides.",
    )

    def can_create_from_shape_impl(self):
        return self.shape.is_path()

    def build(self):

        def spiral_segment(segment_index, spiral_angle, rotation):
            finger_width2 = self.finger_width if self.finger_width2 < 0 else self.finger_width2
            width = (self.finger_width + finger_width2) / 2 + self.finger_gap
            angle = (segment_index % 2 + rotation / 180) * pi
            origin = pya.DPoint(-unit_vector(angle) * width / 2)
            turn = (spiral_angle / 180 - segment_index) * pi
            radius = (segment_index + 1) * width
            return origin, angle, turn, radius

        def spiral_position(spiral_angle):
            origin, angle, turn, radius = spiral_segment(int(spiral_angle / 180), spiral_angle, 0.0)
            position = origin + unit_vector(angle + turn) * radius
            return get_angle(position), position.abs()

        def spiral_region(spiral_angle, rotation, finger_r):
            pnts = []
            stnp = []
            segments = int(spiral_angle / 180 - 1e-3)
            for s in range(segments + 1):
                o, a, t, r = spiral_segment(s, spiral_angle if s == segments else 180 * (s + 1), rotation)
                v0 = unit_vector(a)
                v1 = unit_vector(a + t)
                if s == 0:
                    pnts += segment_points(o + v0 * (r + finger_r), a - pi / 2, -pi, pi * finger_r, self.n)
                pnts += segment_points(o + v0 * (r - finger_r), a + pi / 2, t, t * (r - finger_r), self.n)
                stnp += segment_points(o + v1 * (r + finger_r), a + t - pi / 2, -t, t * (r + finger_r), self.n)[::-1]
                if s == segments:
                    pnts += segment_points(o + v1 * (r - finger_r), a + t + pi / 2, -pi, pi * finger_r, self.n)
            return pya.Region(pya.DPolygon(pnts + stnp[::-1]).to_itype(self.layout.dbu))

        def wg_region(p0, r0, p1, w1, l1=0):
            l0 = (p1 - p0).abs()
            dx = (p1 - p0) / l0
            dy = pya.DVector(dx.y, -dx.x)
            div = r0 * r0 * l0 / (w1 * w1 + l0 * l0)
            rx = (1 - sqrt(1 - (r0 * r0 - w1 * w1) / (l0 * div))) * div
            ry = sqrt(r0 * r0 - rx * rx)
            pnts = [p1 - dy * w1, p0 + dx * rx - dy * ry, p0 + dx * rx + dy * ry, p1 + dy * w1]
            if l1 > 0:
                pnts += [p1 + dx * l1 + dy * w1, p1 + dx * l1 - dy * w1]
            return pya.Region(pya.DPolygon(pnts).to_itype(self.layout.dbu))

        def port_position(position, direction, distance):
            return position + (distance - direction.sprod(position.to_v())) * direction

        # Process terms on the right
        a2, b2 = eval_a2(self), eval_b2(self)
        finger_width2 = self.finger_width if self.finger_width2 < 0 else self.finger_width2
        ground_gap2 = self.ground_gap if self.ground_gap2 < 0 else self.ground_gap2
        spiral_angle2 = self.spiral_angle if self.spiral_angle2 < 0 else self.spiral_angle2
        rotation2 = self.rotation if self.rotation2 < 0 else self.rotation2

        # Find angles for spirals
        rot, length = spiral_position(self.spiral_angle - max(0, self.rotation - 90))
        spiral_rotation = 180 - rot if self.rotation < 0 else 90 - self.spiral_angle + self.rotation
        rot2, length2 = spiral_position(spiral_angle2 - max(0, rotation2 - 90))
        spiral_rotation2 = spiral_rotation - 180
        rotation_out = spiral_rotation2 + (rot2 if rotation2 < 0 else 90 + spiral_angle2 - rotation2)

        # Create spiral regions
        finger_left = spiral_region(self.spiral_angle, spiral_rotation, self.finger_width / 2)
        finger_right = spiral_region(spiral_angle2, spiral_rotation2, finger_width2 / 2)

        # Find waveguide positions and directions
        pos = pya.DPoint(length * unit_vector((rot + spiral_rotation) / 180 * pi))
        port_dir = pya.DVector(-1, 0)
        port_pos = port_position(pos, port_dir, length + self.finger_width / 2 + self.ground_gap)
        pos2 = pya.DPoint(length2 * unit_vector((rot2 + spiral_rotation2) / 180 * pi))
        port_dir2 = unit_vector(rotation_out / 180 * pi)
        port_pos2 = port_position(pos2, port_dir2, length2 + finger_width2 / 2 + ground_gap2)

        # Create waveguide regions
        safe_scale = cos(pi / self.n)
        wg_left = wg_region(pos, self.finger_width / 2 * safe_scale, port_pos, self.a / 2, length)
        gap_left = wg_region(pos, (self.finger_width / 2 + self.ground_gap) * safe_scale, port_pos, self.a / 2 + self.b)
        wg_right = wg_region(pos2, finger_width2 / 2 * safe_scale, port_pos2, a2 / 2, length2)
        gap_right = wg_region(pos2, (finger_width2 / 2 + ground_gap2) * safe_scale, port_pos2, a2 / 2 + b2)

        # Combine gap and metal regions
        region_ground = (
            finger_left.sized(self.ground_gap / self.layout.dbu, 5)
            + finger_right.sized(ground_gap2 / self.layout.dbu, 5)
            + gap_left
            + gap_right
        )
        gap_region = region_ground - finger_left - finger_right - wg_left - wg_right

        # Create shapes into cell
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(gap_region)

        # protection
        region_protection = region_ground.sized(self.margin / self.layout.dbu, 5)
        self.add_protection(region_protection)

        # Add size into annotation layer
        self.cell.shapes(self.get_layer("annotations")).insert(pya.DText(str(round(self.spiral_angle, 5)), 0, 0))

        # Create ports
        self.add_port("a", port_pos, port_dir)
        self.add_port("b", port_pos2, port_dir2)

    @classmethod
    def get_sim_ports(cls, simulation):
        return FingerCapacitorSquare.get_sim_ports(simulation)
