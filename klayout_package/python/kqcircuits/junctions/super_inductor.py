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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


from math import sqrt
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.junctions.junction import Junction
from kqcircuits.util.symmetric_polygons import polygon_with_vsym


class SuperInductor(Junction):
    """The PCell declaration for a Manhattan style single junction."""

    junction_length = Param(pdt.TypeDouble, "Junction length", 5, unit="μm")
    wire_width = Param(pdt.TypeDouble, "Wire width", 0.02, unit="μm")
    phase_slip_junction_length = Param(pdt.TypeDouble, "Phase slip junction length", 0.5, unit="μm")
    squid_area_width = Param(pdt.TypeDouble, "Width of Squids Area.", 0.5, unit="μm")
    squid_area_height = Param(pdt.TypeDouble, "Height of Squids Area.", 1.0, unit="μm")
    squid_count = Param(pdt.TypeInt, "Number of Squids in the Super Inductor.", 8)
    squid_junction_length = Param(pdt.TypeDouble, "Length of the SQUID junctions.", 0.25, unit="μm")
    squid_x_connector_offset = Param(
        pdt.TypeDouble, "Length of the horizontal connector between the corner of the junction to the wire of the squid.", 0.5, unit="μm"
    )
    tapper_horizontal_displacement = Param(
        pdt.TypeDouble,
        "Horizontal displacement of the tapper from the junction.",
        0.5,
        unit="μm",
    )
    tapper_horizontal_displacement_step = Param(
        pdt.TypeDouble,
        "Horizontal displacement step of the tapper from the junction.",
        0.1,
        unit="μm",
    )
    shadow_width = Param(
        pdt.TypeDouble, "Width of the shadow layer.", 0.125, unit="μm"
    )
    shadow_min_height = Param(
        pdt.TypeDouble, "Minimum height of the shadow layer.", 0.04, unit="μm"
    )
    finger_overshoot = Param(pdt.TypeDouble, "Length of fingers after the junction.", 1.0, unit="μm")
    include_base_metal_gap = Param(pdt.TypeBoolean, "Include base metal gap layer.", True)
    include_base_metal_addition = Param(pdt.TypeBoolean, "Include base metal addition layer.", True)
    shadow_margin = Param(pdt.TypeDouble, "Shadow layer margin near the the pads.", 0.5, unit="μm")
    separate_junctions = Param(pdt.TypeBoolean, "Junctions to separate layer.", False)
    offset_compensation = Param(pdt.TypeDouble, "Junction lead offset from junction width", 0, unit="μm")
    mirror_offset = Param(pdt.TypeBoolean, "Move the junction lead offset to the other lead", False)
    finger_overlap = Param(pdt.TypeDouble, "Length of fingers inside the pads.", 1.0, unit="μm")
    height = Param(pdt.TypeDouble, "Height of the junction element.", 22.0, unit="μm")
    width = Param(pdt.TypeDouble, "Width of the junction element.", 22.0, unit="μm")
    pad_height = Param(pdt.TypeDouble, "Height of the junction pad.", 6.0, unit="μm")
    pad_width = Param(pdt.TypeDouble, "Width of the junction pad.", 12.0, unit="μm")
    pad_to_pad_separation = Param(pdt.TypeDouble, "Pad separation.", 6.0, unit="μm")
    x_offset = Param(pdt.TypeDouble, "Horizontal junction offset.", 0, unit="μm")
    pad_rounding_radius = Param(pdt.TypeDouble, "Rounding radius of the junction pad.", 0.5, unit="μm")

    def build(self):
        self.produce_super_inductor()

    def produce_super_inductor(self):

        # corner rounding parameters
        rounding_params = {
            "rinner": self.pad_rounding_radius,  # inner corner rounding radius
            "router": self.pad_rounding_radius,  # outer corner rounding radius
            "n": 64,  # number of point per rounded corner
        }

        junction_shapes_top = []
        junction_shapes_bottom = []
        shadow_shapes = []

        # create rounded bottom part
        y0 = (self.height / 2) - self.pad_height / 2
        bp_pts_left = [pya.DPoint(-self.pad_width / 2, y0), pya.DPoint(-self.pad_width / 2, y0 + self.pad_height)]
        bp_shape = pya.DTrans(0, False, 0, -self.pad_height / 2 - self.pad_to_pad_separation / 2) * polygon_with_vsym(
            bp_pts_left
        )
        self._round_corners_and_append(bp_shape, junction_shapes_bottom, rounding_params)

        bp_shadow_pts_left = [
            bp_pts_left[0] + pya.DPoint(-self.shadow_margin, -self.shadow_margin),
            bp_pts_left[1] + pya.DPoint(-self.shadow_margin, self.shadow_margin),
        ]
        bp_shadow_shape = pya.DTrans(
            0, False, 0, -self.pad_height / 2 - self.pad_to_pad_separation / 2
        ) * polygon_with_vsym(bp_shadow_pts_left)
        self._round_corners_and_append(bp_shadow_shape, shadow_shapes, rounding_params)

        # create rounded top part
        tp_shape = pya.DTrans(0, False, 0, self.pad_height / 2 + self.pad_to_pad_separation / 2) * polygon_with_vsym(
            bp_pts_left
        )
        self._round_corners_and_append(tp_shape, junction_shapes_top, rounding_params)

        tp_shadow_shape = pya.DTrans(
            0, False, 0, self.pad_height / 2 + self.pad_to_pad_separation / 2
        ) * polygon_with_vsym(bp_shadow_pts_left)
        self._round_corners_and_append(tp_shadow_shape, shadow_shapes, rounding_params)

        # create rectangular junction-support structures and junctions
        self._make_super_inductor_junctions(offset = pya.DPoint(0, 0))
        #self._add_shapes(junction_shapes_bottom, "SIS_junction")
        #self._add_shapes(junction_shapes_top, "SIS_junction")
        #self._add_shapes(shadow_shapes, "SIS_shadow")
        self._produce_ground_metal_shapes()
        self._produce_ground_grid_avoidance()
        self._add_refpoints()

    def _make_super_inductor_junctions(self, offset):
        layer_name = "SIS_junction_2" if self.separate_junctions else "SIS_junction"
        shape_into = self.cell.shapes(self.get_layer(layer_name))
        shadow = self.cell.shapes(self.get_layer("SIS_shadow"))

        def wire_shadow(height, i, x, y):
            shadow_shape = pya.DBox(0, 0, self.shadow_width, height)
            side = (self.wire_width) if i % 2 == 0 else -self.shadow_width
            shadow_transform = pya.DTrans(0, False, (x + side), y)
            return shadow_shape * shadow_transform
        
        def junction_shadow(width, height):
            shadow_shape = pya.DBox(0, -self.shadow_min_height/2, self.shadow_width, self.shadow_min_height/2)
            left_transform = pya.DTrans(0, False, -self.shadow_width, height/2)
            right_transform = pya.DTrans(0, False, width, height/2)
            return [
                left_transform * shadow_shape,
                right_transform * shadow_shape,
            ]

        # SQUID ARRAY - Corrected version
        squid_width = self.squid_area_width
        squid_count = self.squid_count
        gap_size = self.squid_junction_length 

        # Calculate available space for the boxes themselves
        total_gap_space = gap_size * (squid_count - 1)
        available_space_for_boxes = self.squid_area_height - total_gap_space
        squid_height = available_space_for_boxes / squid_count

        squid_offset_x = (-squid_width / 2) + self.squid_x_connector_offset - (self.wire_width / 2)
        squid_offset_y = self.height / 2 - self.squid_area_height / 2

        squid_transform = pya.DTrans(0, False, squid_offset_x, squid_offset_y)
        
        # Squid Junctions
        for i in range(int(squid_count)):
            shape_lower = pya.DBox(0, 0, squid_width, self.junction_width)
            y_position = i * (squid_height + gap_size)
            squid_lower_transform = pya.DTrans(0, False, 0, y_position)
            squid_upper_transform = pya.DTrans(0, False, 0, (squid_height - self.junction_width)+y_position)
            shape_into.insert(
                squid_lower_transform * shape_lower * squid_transform
            )
            shape_into.insert(
                squid_upper_transform * shape_lower * squid_transform
            )
            [left, right] = junction_shadow(squid_width, self.junction_width)
            shadow.insert(squid_lower_transform * left * squid_transform)
            shadow.insert(squid_lower_transform * right * squid_transform)
            shadow.insert(squid_upper_transform * left * squid_transform)
            shadow.insert(squid_upper_transform * right * squid_transform)


        # Squid Pylon Wires
        for i in range(int(squid_count)):
            x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
            shape_left = pya.DBox(
                x_offset, 0, 
                x_offset + self.wire_width, squid_height
            )
            shape_right = pya.DBox(
                squid_width - x_offset - self.wire_width, 0,
                squid_width - x_offset, squid_height
            )
            y_position = i * (squid_height + gap_size)
            shape_into.insert(
                pya.DTrans(0, False, 0, y_position) * shape_left * squid_transform
            )
            shape_into.insert(
                pya.DTrans(0, False, 0, y_position) * shape_right * squid_transform
            )
            ws_left = wire_shadow(squid_height-(self.junction_width*2), 1, x_offset, y_position+self.junction_width)
            shadow.insert(ws_left * squid_transform)
            ws_right = wire_shadow(squid_height-(self.junction_width*2), 2, squid_width - x_offset - self.wire_width, y_position+self.junction_width)
            shadow.insert(ws_right * squid_transform)

        # SQUID Debug Gap Boxes
        for i in range(int(squid_count - 1)):
            semi_wire_width = self.wire_width / 2
            semi_squid_width = squid_width / 2
            starting_x = semi_squid_width - semi_wire_width
            ending_x = starting_x + self.wire_width
            shape = pya.DBox(
                starting_x, 0, 
                ending_x, gap_size
            )
            y_position = (i + 1) * squid_height + i * gap_size
            moved = pya.DTrans(0, False, 0, y_position) * shape * squid_transform
            shape_into.insert(moved)
            ws = wire_shadow(gap_size, i, starting_x, y_position)
            shadow.insert(ws * squid_transform)
            # shadow_shape = pya.DBox(0, 0, self.shadow_width, gap_size)
            # side = (self.wire_width) if i % 2 == 0 else -self.shadow_width
            # shadow_transform = pya.DTrans(0, False, (starting_x + side), y_position)
            # shadow.insert(shadow_shape * shadow_transform * squid_transform)
        

        # CONNECTORS
        x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
        conector_length = (self.height - self.squid_area_height) / 2
        wire_top = pya.DBox(
            x_offset, 0, 
            x_offset + self.wire_width, conector_length
        )
        wire_top_transform = pya.DTrans(
            0, False,
            0, self.squid_area_height,
        )
        shape_into.insert(squid_transform * wire_top * wire_top_transform)
        wire_bottom = pya.DBox(
            x_offset, -conector_length,
            x_offset + self.wire_width, 0
        )
        wire_bottom_transform = pya.DTrans(
            0, False,
            0, 0,
        )
        shape_into.insert(squid_transform * wire_bottom * wire_bottom_transform)

        # TAPPER North
        tapper_unit_width = self.squid_area_width
        tapper_unit_height = self.squid_junction_length
        double_connect_offset = self.squid_x_connector_offset * 2
        tapper_north_offset_x = squid_offset_x + tapper_unit_width - double_connect_offset
        tapper_north_offset_y = squid_offset_y + self.squid_area_height
        tapper_north_transform = pya.DTrans(
            0, False, 
            tapper_north_offset_x, tapper_north_offset_y
        )
        tapper_steps = int(self.tapper_horizontal_displacement / self.tapper_horizontal_displacement_step)
        adjusted_tapper_horizontal_displacement = tapper_steps * self.tapper_horizontal_displacement_step
        tapper_height = tapper_unit_height * tapper_steps
        last_tapper_north_transform = None
        for i in range(tapper_steps):
            tapper_step_transform = pya.DTrans(
                0, False, 
                i * adjusted_tapper_horizontal_displacement,
                i * tapper_unit_height
            )
            # pylon
            if i == 0:
                x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
            else:
                x_offset = (tapper_unit_width / 2) - (self.wire_width / 2)
            pylon = pya.DBox(
                x_offset, 0, 
                x_offset + self.wire_width, tapper_unit_height
            )
            shape_into.insert(
                tapper_step_transform * pylon * tapper_north_transform
            )
            # junction
            junction = pya.DBox(
                0, tapper_unit_height - self.junction_width, 
                tapper_unit_width, tapper_unit_height
            )
            shape_into.insert(
                tapper_step_transform * junction * tapper_north_transform
            )
        last_tapper_north_transform = tapper_north_transform * pya.DTrans(
            0, False, 
            0, (tapper_steps) * tapper_unit_height
        )
            # debug box
            # tapper_step_box = pya.DBox(0, 0, tapper_unit_width, tapper_unit_height)
            # shape_into.insert(
            #     tapper_step_transform * tapper_step_box * tapper_north_transform
            # )
        #tapper_north_box = pya.DBox(0, 0, tapper_unit_width, tapper_height)
        #shape_into.insert(tapper_north_transform * tapper_north_box)

        # TAPPER South
        tapper_unit_width = self.squid_area_width
        tapper_unit_height = self.squid_junction_length
        double_connect_offset = self.squid_x_connector_offset * 2
        tapper_south_offset_x = squid_offset_x + tapper_unit_width - double_connect_offset
        tapper_south_offset_y = squid_offset_y - self.squid_junction_length
        tapper_south_transform = pya.DTrans(
            0, False, 
            tapper_south_offset_x, tapper_south_offset_y
        )
        tapper_steps = int(self.tapper_horizontal_displacement / self.tapper_horizontal_displacement_step)
        adjusted_tapper_horizontal_displacement = tapper_steps * self.tapper_horizontal_displacement_step
        tapper_height = tapper_unit_height * tapper_steps
        for i in range(tapper_steps):
            tapper_step_transform = pya.DTrans(
                0, False, 
                i * adjusted_tapper_horizontal_displacement,
                -i * tapper_unit_height
            )
            # pylon
            if i == 0:
                x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
            else:
                x_offset = (tapper_unit_width / 2) - (self.wire_width / 2)
            pylon = pya.DBox(
                x_offset, 0, 
                x_offset + self.wire_width, tapper_unit_height
            )
            shape_into.insert(
                tapper_step_transform * pylon * tapper_south_transform
            )
            # junction
            junction = pya.DBox(
                0, 0, 
                tapper_unit_width, self.junction_width
            )
            shape_into.insert(
                tapper_step_transform * junction * tapper_south_transform
            )
            # debug box
            # tapper_step_box = pya.DBox(0, -tapper_unit_height, tapper_unit_width, 0)
            # shape_into.insert(
            #     tapper_step_transform * tapper_step_box * tapper_south_transform
            # )
        #tapper_south_box = pya.DBox(0, -tapper_height, tapper_unit_width, 0)
        #shape_into.insert(tapper_south_transform * tapper_south_box)
        last_tapper_south_transform = tapper_south_transform * pya.DTrans(
            0, False, 
            0, -(tapper_steps - 1) * tapper_unit_height
        )

        bend_height = self.squid_junction_length

        # Tower NordWest
        tower_unit_width = self.squid_area_width
        tower_unit_height = self.squid_junction_length
        tower_north_transform = last_tapper_north_transform
        last_point = pya.DPoint(0,0) * tower_north_transform
        inductor_padding = 1
        available_height = (self.height - (inductor_padding + bend_height)) - last_point.y
        stored_available_height = available_height
        tower_desired_height = available_height
        tower_steps = int(tower_desired_height / tower_unit_height)
        adjusted_tower_height = tower_steps * tower_unit_height
        tower_unit_height = adjusted_tower_height / tower_steps
        for i in range(tower_steps):
            tower_step_transform = pya.DTrans(
                0, False, 
                tower_unit_width,
                i * tower_unit_height
            )
            x_offset = (tower_unit_width / 2) - (self.wire_width / 2)
            # wire
            pylon = pya.DBox(
                x_offset, 0, 
                x_offset + self.wire_width, tower_unit_height
            )
            shape_into.insert(
                tower_step_transform * pylon * tower_north_transform
            )
            # junction
            junction = pya.DBox(
                0, tower_unit_height - self.junction_width, 
                tower_unit_width, tower_unit_height
            )
            shape_into.insert(
                tower_step_transform * junction * tower_north_transform
            )

        # North Bend
        bend_width_multiplier = 1.5
        last_tower_north_transform = pya.DTrans(
            0, False, 
            tower_unit_width, tower_steps * tower_unit_height
        ) * tower_north_transform
        bend_unit_width = self.squid_area_width * bend_width_multiplier
        bend_unit_height = self.squid_junction_length
        x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
        bend_transform = pya.DTrans(
            0, False, 
            tower_unit_width - (x_offset * 2), 0
        )
        pylon_left = pya.DBox(
            x_offset, 0, 
            x_offset + self.wire_width, bend_unit_height
        )
        shape_into.insert(
            bend_transform * pylon_left * last_tower_north_transform
        )
        pylon_right = pya.DBox(
            bend_unit_width - x_offset, 0,
            bend_unit_width - x_offset + self.wire_width, bend_unit_height
        )
        shape_into.insert(
            bend_transform * pylon_right * last_tower_north_transform
        )
        bend_junction = pya.DBox(
            0, bend_unit_height - self.junction_width, 
            bend_unit_width, bend_unit_height
        )
        shape_into.insert(
            bend_transform * bend_junction * last_tower_north_transform
        )


        # Tower NordEast
        #tower_unit_width = self.squid_area_width
        #tower_unit_height = self.squid_junction_length
        x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
        last_bend_transform = pya.DTrans(
            0, False,
            bend_unit_width - (x_offset * 2), 0
        )
        tower_north_bend_transform = last_tower_north_transform * last_bend_transform
        last_point = pya.DPoint(0,0) * tower_north_bend_transform
        available_height = ((self.height / 2) - (inductor_padding + bend_height))
        tower_west_transform = pya.DTrans(
            0, False, 
            last_point.x - (x_offset * 2), last_point.y - available_height
        )
        tower_desired_height = available_height
        tower_steps = int(tower_desired_height / tower_unit_height)
        adjusted_tower_height = tower_steps * tower_unit_height
        tower_unit_height = adjusted_tower_height / tower_steps
        for i in range(tower_steps):
            x_offset = (tower_unit_width / 2) - (self.wire_width / 2)
            tower_step_transform = pya.DTrans(
                0, False, 
                tower_unit_width,
                i * tower_unit_height
            )
            # wire
            pylon = pya.DBox(
                x_offset, 0, 
                x_offset + self.wire_width, tower_unit_height
            )
            shape_into.insert(
                tower_step_transform * pylon * tower_west_transform
            )
            # junction
            junction = pya.DBox(
                0, tower_unit_height - self.junction_width, 
                tower_unit_width, tower_unit_height
            )
            shape_into.insert(
                tower_step_transform * junction * tower_west_transform
            )

        # ----
        # Tower SouthWest (Inverted version of Tower NordWest)
        tower_unit_width = self.squid_area_width
        tower_unit_height = self.squid_junction_length
        tower_south_transform = last_tapper_south_transform
        last_point = pya.DPoint(0,0) * tower_south_transform
        inductor_padding = 1
        available_height = stored_available_height#((self.height) - (inductor_padding + bend_height)) - last_point.y
        tower_desired_height = available_height
        tower_steps = int(tower_desired_height / tower_unit_height)
        adjusted_tower_height = tower_steps * tower_unit_height
        tower_unit_height = adjusted_tower_height / tower_steps
        for i in range(tower_steps):
            tower_step_transform = pya.DTrans(
                0, False, 
                tower_unit_width,
                -i * tower_unit_height
            )
            x_offset = (tower_unit_width / 2) - (self.wire_width / 2)
            # wire
            pylon = pya.DBox(
                x_offset, -tower_unit_height, 
                x_offset + self.wire_width, 0
            )
            shape_into.insert(
                tower_step_transform * pylon * tower_south_transform
            )
            # junction
            junction = pya.DBox(
                0, -tower_unit_height, 
                tower_unit_width, -tower_unit_height + self.junction_width
            )
            shape_into.insert(
                tower_step_transform * junction * tower_south_transform
            )

        # South Bend (Inverted version of North Bend)
        bend_width_multiplier = 1.5
        last_tower_south_transform = pya.DTrans(
            0, False, 
            tower_unit_width, -tower_steps * tower_unit_height
        ) * tower_south_transform
        bend_unit_width = self.squid_area_width * bend_width_multiplier
        bend_unit_height = self.squid_junction_length
        x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
        bend_transform = pya.DTrans(
            0, False, 
            tower_unit_width - (x_offset * 2), 0
        )
        pylon_left = pya.DBox(
            x_offset, -bend_unit_height, 
            x_offset + self.wire_width, 0
        )
        shape_into.insert(
            bend_transform * pylon_left * last_tower_south_transform
        )
        pylon_right = pya.DBox(
            bend_unit_width - x_offset, -bend_unit_height,
            bend_unit_width - x_offset + self.wire_width, 0
        )
        shape_into.insert(
            bend_transform * pylon_right * last_tower_south_transform
        )
        bend_junction = pya.DBox(
            0, -bend_unit_height, 
            bend_unit_width, -bend_unit_height + self.junction_width
        )
        shape_into.insert(
            bend_transform * bend_junction * last_tower_south_transform
        )

        # Tower SouthEast (Inverted version of Tower NordEast)
        #tower_unit_width = self.squid_area_width
        #tower_unit_height = self.squid_junction_length
        x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
        last_bend_transform = pya.DTrans(
            0, False,
            bend_unit_width - (x_offset * 2), 0
        )
        tower_south_bend_transform = last_tower_south_transform * last_bend_transform
        last_point = pya.DPoint(0,0) * tower_south_bend_transform
        available_height = ((self.height / 2) - (inductor_padding + bend_height))
        tower_east_transform = pya.DTrans(
            0, False, 
            last_point.x - (x_offset * 2), last_point.y + available_height
        )
        tower_desired_height = available_height
        tower_steps = int(tower_desired_height / tower_unit_height)
        adjusted_tower_height = tower_steps * tower_unit_height
        tower_unit_height = adjusted_tower_height / tower_steps
        last_mid_point = None
        for i in range(tower_steps):
            x_offset = (tower_unit_width / 2) - (self.wire_width / 2)
            tower_step_transform = pya.DTrans(
                0, False, 
                tower_unit_width,
                -i * tower_unit_height
            )
            # wire
            pylon = pya.DBox(
                x_offset, -tower_unit_height, 
                x_offset + self.wire_width, 0
            )
            shape_into.insert(
                tower_step_transform * pylon * tower_east_transform
            )
            last_mid_point = tower_step_transform * tower_east_transform
            # junction
            junction = pya.DBox(
                0, -tower_unit_height, 
                tower_unit_width, -tower_unit_height + self.junction_width
            )
            shape_into.insert(
                tower_step_transform * junction * tower_east_transform
            )
        # ----

        # Phase Slip Junction
        slip_unit_width = self.phase_slip_junction_length
        slip_unit_height = self.junction_width
        last_tower_point = pya.DPoint(0,0) * last_mid_point
        phase_junction = pya.DBox(
            -slip_unit_width / 2, -slip_unit_height / 2, 
            slip_unit_width / 2, slip_unit_height / 2
        )
        phase_junction_transform = pya.DTrans(
            0, False,
            last_tower_point.x + (tower_unit_width / 2), self.height / 2
        )
        shape_into.insert(
            phase_junction * phase_junction_transform
        )


    def _add_shapes(self, shapes, layer):
        """Merge shapes into a region and add it to layer."""
        region = pya.Region(shapes).merged()
        self.cell.shapes(self.get_layer(layer)).insert(region)

    def _add_refpoints(self):
        """Adds the "origin_squid" refpoint and port "common"."""
        self.refpoints["origin_squid"] = pya.DPoint(0, 0)
        self.add_port("common", pya.DPoint(0, self.height))

    def _produce_ground_metal_shapes(self):
        """Produces hardcoded shapes in metal gap and metal addition layers."""
        # metal additions bottom
        x0 = -self.a / 2
        y0 = self.height / 2
        bottom_pts = [
            pya.DPoint(x0 + 2, y0 - 7),
            pya.DPoint(x0 + 2, y0 - 5),
            pya.DPoint(x0 + 3, y0 - 5),
            pya.DPoint(x0 + 3, y0 - 4),
            pya.DPoint(x0, y0 - 4),
            pya.DPoint(x0, 0),
        ]
        if self.include_base_metal_addition:
            shape = polygon_with_vsym(bottom_pts)
            #self.cell.shapes(self.get_layer("base_metal_addition")).insert(shape)
            # metal additions top
            top_pts = [
                pya.DPoint(x0 + 2, y0 + 7),
                pya.DPoint(x0 + 2, y0 + 5),
                pya.DPoint(x0 + 3, y0 + 5),
                pya.DPoint(x0 + 3, y0 + 4),
                pya.DPoint(x0, y0 + 4),
                pya.DPoint(x0, self.height),
            ]

            shape = polygon_with_vsym(top_pts)
            #self.cell.shapes(self.get_layer("base_metal_addition")).insert(shape)
        # metal gap
        if self.include_base_metal_gap:
            if self.include_base_metal_addition:
                pts = (
                    bottom_pts
                    + [pya.DPoint(-self.width / 2, 0), pya.DPoint(-self.width / 2, self.height)]
                    + top_pts[::-1]
                )
            else:
                pts = [pya.DPoint(-self.width / 2, 0), pya.DPoint(-self.width / 2, self.height)]
            shape = polygon_with_vsym(pts)
            self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)

    def _produce_ground_grid_avoidance(self):
        """Add ground grid avoidance."""
        w = self.cell.dbbox().width()
        h = self.cell.dbbox().height()
        protection = pya.DBox(-w / 2 - self.margin, -self.margin, w / 2 + self.margin, h + self.margin)
        self.add_protection(protection)

    def _round_corners_and_append(self, polygon, polygon_list, rounding_params):
        """Rounds the corners of the polygon, converts it to integer coordinates, and adds it to the polygon list."""
        polygon = polygon.round_corners(rounding_params["rinner"], rounding_params["router"], rounding_params["n"])
        polygon_list.append(polygon.to_itype(self.layout.dbu))
