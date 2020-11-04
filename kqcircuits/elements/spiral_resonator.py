# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import math

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_coplanar_curved import WaveguideCoplanarCurved
from kqcircuits.elements.waveguide_coplanar_straight import WaveguideCoplanarStraight
from kqcircuits.util.geometry_helper import vector_length_and_direction
from kqcircuits.defaults import default_layers

from kqcircuits.elements.airbridge import Airbridge

numerical_inaccuracy = 1e-7


class SpiralResonator(Element):
    """The PCell declaration for a rectangular spiral resonator.

    The input of the resonator (refpoint `base`) is at left edge of the resonator. The space above, below,
    and right of the input are parameters, so the resonator will be within a box right of the input. The resonator
    length and spacings between spiral segments are parameters. Optionally, airbridge crossings can be added to all
    spiral segments on one side of the spiral.
    """

    PARAMETERS_SCHEMA = {
        "above_space": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Space above the input",
            "default": 500
        },
        "below_space": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Space below the input",
            "default": 400
        },
        "right_space": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Space right of the input",
            "default": 1000
        },
        "length": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Length of the resonator",
            "default": 5000
        },
        "x_spacing": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Spacing between vertical segments",
            "default": 30,
        },
        "y_spacing": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Spacing between horizontal segments",
            "default": 30,
        },
        "term1": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Termination length start [μm]",
            "default": 0
        },
        "term2": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Termination length end [μm]",
            "default": 0
        },
        "bridges_left": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Crossing airbridges left",
            "default": False,
        },
        "bridges_bottom": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Crossing airbridges bottom",
            "default": False,
        },
        "bridges_right": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Crossing airbridges right",
            "default": False,
        },
        "bridges_top": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Crossing airbridges top",
            "default": False,
        }
    }

    def produce_impl(self):

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

        # create the first segments, which follow the edges of the available area and thus do not depend on the spacings
        if top == 0:
            guide_points = [
                pya.DPoint(0 - self.r, 0),
                pya.DPoint(right, top),
                pya.DPoint(right, bottom)
            ]
            first_rotation = 0
            top_right_point_idx = 1
            # start termination
            WaveguideCoplanar.produce_end_termination(self, res_trans*pya.DPoint(self.r, 0), res_trans*pya.DPoint(0, 0),
                                                      self.term1)
        else:
            curve_cell = self.add_element(WaveguideCoplanarCurved, Element.PARAMETERS_SCHEMA, alpha=math.pi/2)
            trans = pya.DTrans(-1, False, pya.DPoint(0, self.r))
            self.insert_cell(curve_cell, res_trans*trans)
            current_len = WaveguideCoplanar.get_length(self.cell, self.get_layer("annotations"))
            guide_points = [
                pya.DPoint(self.r, 0),
                pya.DPoint(self.r, top),
                pya.DPoint(right, top),
                pya.DPoint(right, bottom)
            ]
            first_rotation = -3
            top_right_point_idx = 2
            # start termination
            WaveguideCoplanar.produce_end_termination(self, res_trans*guide_points[0], res_trans*pya.DPoint(0, 0),
                                                      self.term1)

        for i in range(1, len(guide_points)):
            rotation = (first_rotation - i + 1) % 4
            current_len, final_segment, can_create_resonator = self.add_segment(guide_points[i-1], guide_points[i],
                                                                                current_len, rotation, res_trans)

        # if we have above_space == 0 or below_space == 0, the x-spacing must be adjusted
        if self.above_space == 0 or self.below_space == 0:
            left_extra = 0
        else:
            left_extra = 1

        # create the spiral segments which depend on the spacings
        previous_point = guide_points[-1]
        segment_idx = 0
        while current_len < self.length and not final_segment:
            if segment_idx % 4 == 0:
                point = pya.DPoint(left + (segment_idx//4 + left_extra)*self.x_spacing,
                                   bottom + (segment_idx//4)*self.y_spacing)
                rotation = 2
            elif segment_idx % 4 == 1:
                point = pya.DPoint(left + (segment_idx//4 + left_extra)*self.x_spacing,
                                   top - (segment_idx//4 + 1)*self.y_spacing)
                rotation = 1
            elif segment_idx % 4 == 2:
                point = pya.DPoint(right - (segment_idx//4 + 1)*self.x_spacing,
                                   top - (segment_idx//4 + 1)*self.y_spacing)
                rotation = 0
            else:
                point = pya.DPoint(right - (segment_idx//4 + 1)*self.x_spacing,
                                   bottom + (segment_idx//4 + 1)*self.y_spacing)
                rotation = 3

            current_len, final_segment, can_create_resonator = self.add_segment(previous_point, point, current_len,
                                                                                rotation, res_trans)
            if not can_create_resonator:
                return False

            guide_points.append(point)

            if final_segment:
                break
            else:
                previous_point = point
                segment_idx += 1

        self.produce_crossing_airbridges(guide_points, top_right_point_idx, res_trans)

        self.add_port("in", pya.DPoint(0,0), pya.DVector(-1, 0))
        super().produce_impl()
        return True

    def add_segment(self, point1, point2, current_len, rotation, res_trans):
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

        Returns:
            ``(current_len, final_segment, can_create_resonator)``

            Where ``current_len`` is length of the resonator waveguide after adding this segment.
            ``final_segment`` is True if this is the last segment of the resonator, False otherwise.
            ``can_create_resonator`` is True if it was possible to create the resonator with the
            given parameters, False otherwise.
        """

        can_create_resonator = True

        segment_len, segment_dir, corner_offset, straight_len, curve_angle, final_segment = \
            self.get_segment_data(point1, point2, current_len, rotation, res_trans)
        if segment_len < 2*self.r + numerical_inaccuracy:
            can_create_resonator = False

        # straight waveguide part
        if straight_len > numerical_inaccuracy:
            subcell = self.add_element(WaveguideCoplanarStraight, Element.PARAMETERS_SCHEMA, l=straight_len)
            trans = pya.DTrans(rotation, False, point1 + self.r * segment_dir)
            self.insert_cell(subcell, res_trans*trans)
        else:
            # (not sure if this can ever be reached, but might be possible due to numerical issues)
            # in this case the previous curve was really the last segment, so need to terminate that
            WaveguideCoplanar.produce_end_termination(self, res_trans*point1, res_trans*(point1 + self.r*segment_dir),
                                                      self.term2)
            final_segment = True
        # curved waveguide part
        if curve_angle < -numerical_inaccuracy:
            subcell = self.add_element(WaveguideCoplanarCurved, Element.PARAMETERS_SCHEMA, alpha=curve_angle)
            trans = res_trans*pya.DTrans(rotation + 1, False, point2 - self.r*segment_dir + corner_offset)
            self.insert_cell(subcell, trans)
            if final_segment:
                WaveguideCoplanarCurved.produce_curve_termination(self, curve_angle, self.term2, trans)
        else:
            # in this case the straight segment was really the last segment, so need to terminate that
            WaveguideCoplanar.produce_end_termination(self, res_trans*point1,
                                                      res_trans*(point1 + (self.r + straight_len)*segment_dir),
                                                      self.term2)
            final_segment = True

        current_len = WaveguideCoplanar.get_length(self.cell, self.get_layer("annotations"))

        return current_len, final_segment, can_create_resonator

    def get_segment_data(self, point1, point2, current_len, rotation, res_trans):
        """Get data about spiral segment.

        Args:
            point1: start point of the segment
            point2: end point of the segment
            current_len: current length of the resonator waveguide
            rotation: rotation in units of 90-degrees, 0 for left-to-right segment, 1 for bottom-to-up segment,
                2 for right-to-left segment, 3 for up-to-bottom segment
            res_trans: transformation applied to the entire resonator

        Returns:
            ``(segment_len, segment_dir, corner_offset, straight_len, curve_angle, final_segment)``

            * segment_len (float): length of the segment
            * segment_dir (DVector): direction of the segment
            * corner_offset (DVector): offset to be applied to the curved waveguide position
            * straight_len (float): length of the straight part of the segment
            * curve_angle (float): angle (alpha) for the curved waveguide
            * final_segment: True if this is the last segment of the resonator, False otherwise
        """
        final_segment = False
        segment_len, segment_dir = vector_length_and_direction(point2 - point1)

        full_straight_len = segment_len - 2*self.r
        full_corner_len = math.pi*self.r/2

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
        elif current_len + full_straight_len + full_corner_len > self.length:
            straight_len = full_straight_len
            curve_angle = -((self.length - current_len - full_straight_len)/full_corner_len)*math.pi/2
            final_segment = True
        # full straight and full corner
        else:
            straight_len = full_straight_len
            curve_angle = -math.pi/2

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
        side = 1
        for direction_name, (rotation, include_bridges) in directions_dict.items():
            if include_bridges:
                for i in range(top_right_point_idx, len(guide_points)):
                    if (i - top_right_point_idx) % 4 == rotation:
                        segment_len, segment_dir = vector_length_and_direction(guide_points[i] - guide_points[i-1])
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

        mirrored = False

        if (self.above_space > self.below_space != 0) or self.above_space == 0:
            top = self.above_space
            bottom = -self.below_space
        if (self.below_space > self.above_space != 0) or self.below_space == 0:
            top = self.below_space
            bottom = -self.above_space
            mirrored = True

        # if we have above_space == 0 or below_space == 0, we adjust the spacing to get more optimal values
        if self.above_space == 0 or self.below_space == 0:
            left = 0
        else:
            left = self.r

        right = self.right_space

        return left, bottom, right, top, mirrored
