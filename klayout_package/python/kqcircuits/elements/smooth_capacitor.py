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


from math import pi, cos, sin, atan
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.elements.element import Element
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare


@add_parameters_from(FingerCapacitorSquare, "fixed_length", "a2", "b2", finger_width=10, finger_gap=5)
class SmoothCapacitor(Element):
    """The PCell declaration for a smooth finger capacitor.

    SmoothCapacitor is a finger capacitor, which has continuous geometry changes
    through the capacitance range. This leads to continuous capacitance function,
    which enables using capacitor inside numerical optimization methods.

    Capacitance range is achieved by changing single parameter called `finger_control`.
    """

    finger_control = Param(pdt.TypeDouble, "Continuously adjust finger number", 2.1,
               docstring="Parameter for capacitor growth (related to number of fingers per side)")
    ground_gap = Param(pdt.TypeDouble, "Gap between ground and finger", 10, unit="μm")

    def can_create_from_shape_impl(self):
        return self.shape.is_path()

    def build(self):
        # constants
        r1 = self.finger_width / 2
        r2 = r1 + self.finger_gap
        scale = self.finger_width + self.finger_gap
        x_max = max(self.finger_control, 1.0 / self.finger_control) * scale - self.finger_gap / 2
        x_mid = x_max - self.finger_width
        xport = x_max + self.ground_gap

        def unit_vector(radians):
            return pya.DVector(cos(radians), sin(radians))

        def segment_points(start_pos, start_ang, turn, length):
            if length == 0:
                return []
            if turn == 0:
                return [start_pos + length * unit_vector(start_ang)]
            r = length / turn  # signed radius
            center = start_pos + r * unit_vector(start_ang + pi / 2)  # center of the turn circle
            num_pnts = max(round(abs(turn) * self.n / (2 * pi)), 1)  # number of new points
            return [center - r * unit_vector(start_ang + pi / 2 + turn * (n + 1) / num_pnts) for n in range(num_pnts)]

        def t_poly(bend, length):
            # Bottom 180-degree bend starting from origin
            ang = 3 * pi / 2
            pnts = segment_points(pya.DPoint(0, 0), ang, -pi, pi * r1)
            ang -= pi
            # Bend before straight segment
            bend0 = min(bend, pi / 2)
            pnts += segment_points(pnts[-1], ang, bend0, bend0 * r2)
            ang += bend0
            # Straight segment, 180-degree bend, and straight segment back
            pnts += segment_points(pnts[-1], ang, 0.0, length)
            pnts += segment_points(pnts[-1], ang, -pi, pi * r1)
            ang -= pi
            pnts += segment_points(pnts[-1], ang, 0.0, length)
            # Possible turn upwards if bend > pi/2
            turn = bend - pi / 2
            if turn > 0.0:
                pnts += segment_points(pnts[-1], ang, turn, turn * r2)
                ang += turn
            # The last bend back to origin
            last_bend = ang + pi / 2
            if last_bend > 1e-13:
                r3 = pnts[-1].x / (cos(last_bend) - 1)
                pnts += segment_points(pnts[-1], ang, -last_bend, last_bend * r3)
                pnts += segment_points(pnts[-1], -pi / 2, 0.0, max(pnts[-1].y, 0.0))
            return pya.DPolygon(pnts)

        def finger_polygon(order_number):
            if self.finger_control <= order_number:  # The finger does not exist for given order_number.
                return None
            trans = pya.DTrans(0, order_number % 2 == 1) * pya.DTrans(x_max, (order_number - 0.5) * scale)
            if self.finger_control <= 1.0:
                return t_poly(0.0, scale).transformed(trans)
            t_len = scale * pi/2  # length of 90-degree turn segment
            s_len = scale * (2 * self.finger_control - 3)  # length of straight segment
            f_len = s_len + 2 * t_len  # total length of finger (including two 90-degree turns and straight)
            x = (self.finger_control - order_number) * f_len
            if x < t_len:  # The first turn is not full 90 degrees.
                return t_poly((x / t_len) * pi / 2, 0.0).transformed(trans)
            if s_len < 0.0:  # The first turn is limited by finger length. This only happens when order_number=0.
                return t_poly(pi / 2 - 2 * atan(-s_len / scale), -s_len).transformed(trans)
            if x < t_len + s_len:  # The straight segment is not full length.
                return t_poly(pi / 2, x - t_len).transformed(trans)
            if x < 2 * f_len - t_len:  # The straight segment is full, but the last turn does not exist yet.
                return t_poly(pi / 2, s_len).transformed(trans)
            if x < 2 * f_len:  # The last turn is below 90 degrees.
                return t_poly(pi * (1 + (x - 2 * f_len) / (2 * t_len)), s_len).transformed(trans)
            return t_poly(pi, s_len).transformed(trans)

        def insert_wg_joint(reg, x0, xr, r):
            rr = r / self.layout.dbu
            reg += pya.Region(pya.DBox(xr, -r, 2*x0 - xr, r).to_itype(self.layout.dbu)).rounded_corners(rr, rr, self.n)
            reg -= pya.Region(pya.DBox(x0, -r, 2*x0 - xr, r).to_itype(self.layout.dbu))

        def middle_gap_fill():
            y = scale / 2
            x = (x_mid + x_max) / 2
            l = 2 * x if self.finger_control < 1 else scale
            rr = (self.finger_width / 2 + self.ground_gap) / self.layout.dbu
            return pya.Region(pya.DPolygon([pya.DPoint(-x, y), pya.DPoint(l - x, y),
                                            pya.DPoint(x, -y), pya.DPoint(x - l, -y)]).to_itype(self.layout.dbu)
                              ).sized(rr, 5).rounded_corners(rr, rr, self.n)

        def super_smoothen_region(reg, r):
            rr = r / self.layout.dbu
            reg_mod = reg.sized(rr, 5).sized(-rr, 5).rounded_corners(rr, 0, self.n).rounded_corners(0, rr, self.n)
            reg += reg_mod
            return reg.smoothed(1)

        # List of finger polygons
        i = 0
        polys = []
        while True:
            poly = finger_polygon(i)
            if poly is None:
                break
            polys.append(poly)
            i += 1

        # Create finger pad regions
        right_fingers = pya.Region([
            poly.to_itype(self.layout.dbu) for poly in polys
        ])
        left_fingers = right_fingers.transformed(pya.Trans(2))

        # Ground etch region
        region_ground = right_fingers + left_fingers
        region_ground.size(self.ground_gap / self.layout.dbu, 5)
        region_ground += middle_gap_fill()
        a2 = self.a if self.a2 < 0 else self.a2
        b2 = self.b if self.b2 < 0 else self.b2
        insert_wg_joint(region_ground, xport, x_mid - self.ground_gap, b2 + a2/2)
        insert_wg_joint(region_ground, -xport, -x_mid + self.ground_gap, self.b + self.a/2)
        region_ground = super_smoothen_region(region_ground, self.finger_gap + self.ground_gap)

        # Finalize finger pad regions
        insert_wg_joint(right_fingers, xport, x_mid, a2/2)
        insert_wg_joint(left_fingers, -xport, -x_mid, self.a/2)
        right_fingers = super_smoothen_region(right_fingers, self.finger_gap)
        left_fingers = super_smoothen_region(left_fingers, self.finger_gap)

        # Insert waveguide segments in both ends, if fixed_length is set
        if self.fixed_length != 0:
            xfixed = self.fixed_length / 2
            if xfixed < xport:
                raise ValueError(f"SmoothCapacitor parameters not compatible with fixed_length={self.fixed_length}")
            region_ground += pya.Region(pya.DBox(xport, -b2 - a2/2, xfixed, b2 + a2/2).to_itype(self.layout.dbu)) + \
                pya.Region(pya.DBox(-xfixed, -self.b - self.a/2, -xport, self.b + self.a/2).to_itype(self.layout.dbu))
        else:
            xfixed = xport
        # Always insert tolerance to secure trace connection
        right_fingers += pya.Region(pya.DBox(xport-0.001, -a2/2, xfixed+1, a2/2).to_itype(self.layout.dbu))
        left_fingers += pya.Region(pya.DBox(-xfixed-1, -self.a/2, -xport+0.001, self.a/2).to_itype(self.layout.dbu))
        xport = xfixed

        # Create shapes into cell
        region = region_ground - right_fingers - left_fingers
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(region)

        # protection
        region_protection = region_ground.sized(self.margin / self.layout.dbu, 5)
        self.add_protection(region_protection)

        # Add size into annotation layer
        self.cell.shapes(self.get_layer("annotations")).insert(pya.DText(str(round(self.finger_control, 5)), 0, 0))

        # Create ports
        self.add_port("a", pya.DPoint(-xport, 0), pya.DVector(-1, 0))
        self.add_port("b", pya.DPoint(xport, 0), pya.DVector(1, 0))
