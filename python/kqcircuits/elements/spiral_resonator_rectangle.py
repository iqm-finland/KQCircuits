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


import math

from kqcircuits.defaults import default_layers
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_curved import WaveguideCoplanarCurved
from kqcircuits.elements.waveguide_coplanar_straight import WaveguideCoplanarStraight
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import vector_length_and_direction
from kqcircuits.util.parameters import Param, pdt

numerical_inaccuracy = 1e-7


class SpiralResonatorRectangle(Element):
    """The PCell declaration for a rectangular spiral resonator.

    The input of the resonator (refpoint `base`) is at left edge of the resonator. The space above, below,
    and right of the input are parameters, so the resonator will be within a box right of the input. The resonator
    length and spacings between spiral segments are parameters. Optionally, airbridge crossings can be added to all
    spiral segments on one side of the spiral.
    """

    above_space = Param(pdt.TypeDouble, "Space above the input", 500)
    below_space = Param(pdt.TypeDouble, "Space below the input", 400)
    right_space = Param(pdt.TypeDouble, "Space right of the input", 1000)
    length = Param(pdt.TypeDouble, "Length of the resonator", 4200)
    auto_spacing = Param(pdt.TypeBoolean, "Automatic determination of spacing", True)
    x_spacing = Param(pdt.TypeDouble, "Spacing between vertical segments", 100)
    y_spacing = Param(pdt.TypeDouble, "Spacing between horizontal segments", 100)
    term1 = Param(pdt.TypeDouble, "Termination length start", 0, unit="μm")
    term2 = Param(pdt.TypeDouble, "Termination length end", 0, unit="μm")
    bridges_left = Param(pdt.TypeBoolean, "Crossing airbridges left", False)
    bridges_bottom = Param(pdt.TypeBoolean, "Crossing airbridges bottom", False)
    bridges_right = Param(pdt.TypeBoolean, "Crossing airbridges right", False)
    bridges_top = Param(pdt.TypeBoolean, "Crossing airbridges top", False)

    def produce_impl(self):
        can_create_resonator = False
        if self.auto_spacing:
            left, bottom, right, top, _ = self.get_spiral_dimensions()
            spacing = max(right - left, top - bottom) / 4
            step = spacing
            best_spacing = None

            while step > 0.1:  # 0.1 um accuracy on spacing
                step /= 2
                self.x_spacing = spacing
                self.y_spacing = spacing
                self.cell.clear()
                if self.produce_spiral_resonator():
                    best_spacing = spacing
                    spacing += step
                else:
                    spacing -= step

            if best_spacing is not None:
                self.cell.clear()
                self.x_spacing = best_spacing
                self.y_spacing = best_spacing
                can_create_resonator = self.produce_spiral_resonator()

        else:
            can_create_resonator = self.produce_spiral_resonator()

        if not can_create_resonator:
            self.cell.clear()
            error_msg = "Cannot create a resonator with the given parameters. Try decreasing the " \
                        "spacings or increasing the available area."
            error_text_cell = self.layout.create_cell("TEXT", "Basic", {
                "layer": default_layers["annotations"],
                "text": error_msg,
                "mag": 10.0
            })
            self.insert_cell(error_text_cell)
            raise ValueError(error_msg)

    def produce_spiral_resonator(self):
        """Produces the spiral resonator waveguide and airbridges.

        Returns:
            True, if it was possible to create the resonator with the current spacings
            False, if it was not possible to create the resonator with the current spacings
        """

        left, bottom, right, top, mirrored = self.get_spiral_dimensions()
        res_trans = pya.DTrans(0, mirrored)  # transformation for the whole spiral resonator

        current_len = 0
        final_segment = False

        # start termination
        WaveguideCoplanar.produce_end_termination(self, res_trans * pya.DPoint(self.r, 0), res_trans * pya.DPoint(0, 0),
                                                  self.term1)

        # create the first segments, which follow the edges of the available area and thus do not depend on the spacings
        if top == 0:
            guide_points = [pya.DPoint(0 - self.r, 0)]
        elif top < 2 * self.r:
            curve_angle = math.acos(1.0 - top / (2 * self.r))
            curve_x = 2 * self.r * math.sin(curve_angle)
            curve_cell = self.add_element(WaveguideCoplanarCurved, Element, alpha=curve_angle)
            self.insert_cell(curve_cell, res_trans * pya.DTrans(-1, False, pya.DPoint(0, self.r)))
            self.insert_cell(curve_cell, res_trans * pya.DTrans(1, False, pya.DPoint(curve_x, top - self.r)))
            current_len += 2 * curve_angle * self.r
            guide_points = [pya.DPoint(curve_x - self.r, top)]
            left = max(0, curve_x - self.r + self.x_spacing)

        else:
            curve_cell = self.add_element(WaveguideCoplanarCurved, Element, alpha=math.pi/2)
            trans = pya.DTrans(-1, False, pya.DPoint(0, self.r))
            self.insert_cell(curve_cell, res_trans*trans)
            current_len += self.r * math.pi / 2
            guide_points = [pya.DPoint(self.r, top)]
            current_len, final_segment, can_create_resonator = self.add_segment(pya.DPoint(self.r, 0), guide_points[0],
                                                                                current_len, 1, res_trans,
                                                                                right - self.r)
            if not can_create_resonator:
                return False
            left = self.r + self.x_spacing

        # create the spiral segments which depend on the spacings
        previous_point = guide_points[-1]
        segment_idx = 0
        while not final_segment:
            p_left = left + (segment_idx // 4) * self.x_spacing
            p_bottom = bottom + ((segment_idx + 1) // 4) * self.y_spacing
            p_right = right - ((segment_idx + 2) // 4) * self.x_spacing
            p_top = top - ((segment_idx + 3) // 4) * self.y_spacing
            if segment_idx % 4 == 0:
                point = pya.DPoint(p_right, p_top)
                space = p_top - p_bottom
                rotation = 0
            elif segment_idx % 4 == 1:
                point = pya.DPoint(p_right, p_bottom)
                space = p_right - p_left
                rotation = 3
            elif segment_idx % 4 == 2:
                point = pya.DPoint(p_left, p_bottom)
                space = p_top - p_bottom
                rotation = 2
            else:
                point = pya.DPoint(p_left, p_top)
                space = p_right - p_left
                rotation = 1

            current_len, final_segment, can_create_resonator = self.add_segment(previous_point, point, current_len,
                                                                                rotation, res_trans, space)
            if not can_create_resonator:
                return False

            guide_points.append(point)
            previous_point = point
            segment_idx += 1

        self.produce_crossing_airbridges(guide_points, 1, res_trans)

        self.add_port("in", pya.DPoint(0,0), pya.DVector(-1, 0))
        super().produce_impl()
        return True

    def add_segment(self, point1, point2, current_len, rotation, res_trans, space):
        """Inserts waveguides for a segment between point1 and point2.

        This assumes that there is already a 90-degree corner waveguide ending at point1. It then creates either a
        straight waveguide, or straight waveguide and less than 90-degree corner, or straight waveguide and
        90-degree corner, such that the entire waveguide in the resonator is within self.length. The straight segment
        will start at distance self.r from point1 and end at distance self.r from point2 (or closer to point1,
        if length would be exceeded).

        Args:
            point1: start point of the segment
            point2: end point of the segment
            current_len: current length of the resonator waveguide
            rotation: rotation in units of 90-degrees, 0 for left-to-right segment, 1 for
                      bottom-to-up segment, 2 for right-to-left segment, 3 for up-to-bottom segment
            res_trans: transformation applied to the entire resonator
            space: space left for the next turn

        Returns:
            ``(current_len, final_segment, can_create_resonator)``

            Where ``current_len`` is length of the resonator waveguide after adding this segment.
            ``final_segment`` is True if this is the last segment of the resonator, False otherwise.
            ``can_create_resonator`` is True if it was possible to create the resonator with the
            given parameters, False otherwise.
        """

        if space + numerical_inaccuracy < 0.0:
            return current_len, False, False

        _, segment_dir, corner_offset, straight_len, curve_angle, final_segment = \
            self.get_segment_data(point1, point2, current_len, rotation, max(0.0, space))

        if (not final_segment and space < 2 * self.r) or \
                straight_len + numerical_inaccuracy < 0.0 or curve_angle - numerical_inaccuracy > 0.0:
            return current_len, False, False

        # straight waveguide part
        if straight_len > numerical_inaccuracy:
            subcell = self.add_element(WaveguideCoplanarStraight, Element, l=straight_len)
            trans = pya.DTrans(rotation, False, point1 + self.r * segment_dir)
            self.insert_cell(subcell, res_trans*trans)
        # curved waveguide part
        if curve_angle < -numerical_inaccuracy:
            subcell = self.add_element(WaveguideCoplanarCurved, Element, alpha=curve_angle)
            trans = res_trans*pya.DTrans(rotation + 1, False,
                                         point1 + (self.r + straight_len) * segment_dir + corner_offset)
            self.insert_cell(subcell, trans)
            if final_segment:
                WaveguideCoplanarCurved.produce_curve_termination(self, curve_angle, self.term2, trans)
        elif final_segment:
            # in this case the straight segment was the last segment, so need to terminate that
            WaveguideCoplanar.produce_end_termination(self, res_trans*point1,
                                                      res_trans*(point1 + (self.r + straight_len)*segment_dir),
                                                      self.term2)

        return current_len + straight_len - curve_angle * self.r, final_segment, True

    def get_segment_data(self, point1, point2, current_len, rotation, space):
        """Get data about spiral segment.

        Args:
            point1: start point of the segment
            point2: end point of the segment
            current_len: current length of the resonator waveguide
            rotation: rotation in units of 90-degrees, 0 for left-to-right segment, 1 for bottom-to-up segment,
                2 for right-to-left segment, 3 for up-to-bottom segment
            space: space left for the next turn

        Returns:
            ``(segment_len, segment_dir, corner_offset, straight_len, curve_angle, final_segment)``

            * segment_len (float): length of the segment
            * segment_dir (DVector): direction of the segment
            * corner_offset (DVector): offset to be applied to the curved waveguide position
            * straight_len (float): length of the straight part of the segment
            * curve_angle (float): angle (alpha) for the curved waveguide
            * final_segment: True if this is the last segment of the resonator, False otherwise
        """
        segment_len, segment_dir = vector_length_and_direction(point2 - point1)

        max_curve = math.acos(1.0 - space / (2 * self.r)) if space < 2 * self.r else math.pi / 2
        full_straight_len = segment_len - (1.0 + math.sin(max_curve)) * self.r

        corner_offset = {
            0: pya.DVector(0, -self.r),
            1: pya.DVector(self.r, 0),
            2: pya.DVector(0, self.r),
            3: pya.DVector(-self.r, 0),
        }[rotation]

        # reduced straight
        if current_len + full_straight_len > self.length:
            straight_len = self.length - current_len
            curve_angle = 0
            final_segment = True
        # full straight and reduced corner
        elif current_len + full_straight_len + max_curve * self.r > self.length:
            straight_len = full_straight_len
            curve_angle = (current_len + full_straight_len - self.length) / self.r
            final_segment = True
        # full straight and full corner
        else:
            straight_len = full_straight_len
            curve_angle = -max_curve
            final_segment = False

        return segment_len, segment_dir, corner_offset, straight_len, curve_angle, final_segment

    def produce_crossing_airbridges(self, guide_points, top_right_point_idx, res_trans):
        """Produces crossing airbridges on the sides defined by pcell parameters.

        Args:
            guide_points: points for the spiral waveguide, where each point (except possibly the last) marks a corner
            top_right_point_idx: index of the top-right-most point in guide_points
            res_trans: transformation applied to the entire resonator

        """

        # dict of {direction name: (rotation in units of 90-degrees, include bridges)}
        directions_dict = {
            "Left": (3, self.bridges_left),
            "Bottom": (0 if res_trans.is_mirror() else 2, self.bridges_bottom),
            "Right": (1, self.bridges_right),
            "Top": (2 if res_trans.is_mirror() else 0, self.bridges_top)
        }
        cell = self.add_element(Airbridge)
        dist_from_corner = 20
        for _, (rotation, include_bridges) in directions_dict.items():
            side = 1
            if include_bridges:
                for i in range(top_right_point_idx, len(guide_points)):
                    if (i - top_right_point_idx) % 4 == rotation:
                        _, segment_dir = vector_length_and_direction(guide_points[i] - guide_points[i-1])
                        if side == 1:
                            trans = pya.DTrans(rotation, False,
                                               guide_points[i] - (self.r + dist_from_corner)*segment_dir)
                        else:
                            trans = pya.DTrans(rotation, False,
                                               guide_points[i-1] + (self.r + dist_from_corner)*segment_dir)
                        self.insert_cell(cell, res_trans*trans)
                        side = -side

    def get_spiral_dimensions(self):
        """Get the spiral edges.

        Returns:
            A tuple composed of the following elements

            * left: x-coordinate of the left edge
            * bottom: x-coordinate of the left edge
            * right: x-coordinate of the left edge
            * top: x-coordinate of the left edge
            * mirrored: if top and bottom are flipped
        """

        if self.above_space == 0 or self.above_space > self.below_space:
            top = self.above_space
            bottom = -self.below_space
            mirrored = False
        else:
            top = self.below_space
            bottom = -self.above_space
            mirrored = True

        left = 0
        right = self.right_space

        return left, bottom, right, top, mirrored
