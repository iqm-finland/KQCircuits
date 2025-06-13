# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
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


from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.junctions.junction import Junction
from kqcircuits.util.symmetric_polygons import polygon_with_vsym


class SuperInductor(Junction):
    """The PCell declaration for a Manhattan style single junction."""

    junction_length = Param(pdt.TypeDouble, "Junction length", 2, unit="μm")
    wire_width = Param(pdt.TypeDouble, "Wire width", 0.02, unit="μm")
    phase_slip_junction_length = Param(pdt.TypeDouble, "Phase slip junction length", 0.5, unit="μm")
    squid_area_width = Param(pdt.TypeDouble, "Width of Squids Area.", 2, unit="μm")
    squid_area_height = Param(pdt.TypeDouble, "Height of Squids Area.", 5, unit="μm")
    squid_count = Param(pdt.TypeInt, "Number of Squids in the Super Inductor.", 8)
    squid_wire_length = Param(pdt.TypeDouble, "Length of the wire between SQUIDs.", 0.25, unit="μm")
    squid_x_connector_offset = Param(
        pdt.TypeDouble,
        "Length of the horizontal connector between the corner of the junction to the wire of the squid.",
        0.5,
        unit="μm",
    )
    inductor_padding = Param(pdt.TypeDouble, "Vertical margin from bends to limit of the circuit", 1, unit="μm")
    taper_horizontal_displacement = Param(
        pdt.TypeDouble,
        "Horizontal displacement of the taper from the junction.",
        1,
        unit="μm",
    )
    taper_horizontal_displacement_step = Param(
        pdt.TypeDouble,
        "Horizontal displacement step of the taper from the junction.",
        0.25,
        unit="μm",
    )
    bend_width_multiplier = Param(
        pdt.TypeDouble,
        "Relative width of bend according to junction_width",
        1.5,
    )
    shadow_width = Param(pdt.TypeDouble, "Width of the shadow layer.", 0.125, unit="μm")
    shadow_min_height = Param(pdt.TypeDouble, "Minimum height of the shadow layer.", 0.04, unit="μm")
    include_base_metal_gap = Param(pdt.TypeBoolean, "Include base metal gap layer.", True)
    include_base_metal_addition = Param(pdt.TypeBoolean, "Include base metal addition layer.", True)
    shadow_margin = Param(pdt.TypeDouble, "Shadow layer margin near the the pads.", 0.5, unit="μm")
    finger_overlap = Param(pdt.TypeDouble, "Length of fingers inside the pads.", 1.0, unit="μm")
    inductor_height = Param(pdt.TypeDouble, "Height of the junction element.", 22.0, unit="μm")
    inductor_width = Param(pdt.TypeDouble, "Width of the junction element.", 22.0, unit="μm")

    def build(self):
        self.produce_super_inductor()

    def produce_super_inductor(self):
        # create rectangular junction-support structures and junctions
        self._make_super_inductor_junctions()
        self._produce_ground_metal_shapes()
        self._produce_ground_grid_avoidance()
        self._add_refpoints()

    def _make_super_inductor_junctions(self):
        layer_name = "SIS_junction"
        junction_shapes = self.cell.shapes(self.get_layer(layer_name))
        shadow_shapes = self.cell.shapes(self.get_layer("SIS_shadow"))

        def wire_shadow(height, i, x, y):
            shadow_shape = pya.DBox(0, 0, self.shadow_width, height)
            side = (self.wire_width) if i % 2 == 0 else -self.shadow_width
            shadow_transform = pya.DTrans(0, False, (x + side), y)
            return shadow_shape * shadow_transform

        def junction_shadow(width, height):
            shadow_shape = pya.DBox(0, -self.shadow_min_height / 2, self.shadow_width, self.shadow_min_height / 2)
            left_transform = pya.DTrans(0, False, -self.shadow_width, height / 2)
            right_transform = pya.DTrans(0, False, width, height / 2)
            return [
                left_transform * shadow_shape,
                right_transform * shadow_shape,
            ]

        # SQUID ARRAY - Corrected version
        squid_width = self.squid_area_width
        squid_count = self.squid_count
        gap_size = self.squid_wire_length

        # Calculate available space for the boxes themselves
        total_gap_space = gap_size * (squid_count - 1)
        available_space_for_boxes = self.squid_area_height - total_gap_space
        squid_height = available_space_for_boxes / squid_count
        squid_offset_x = (-squid_width / 2) + self.squid_x_connector_offset - (self.wire_width / 2)
        squid_offset_y = self.inductor_height / 2 - self.squid_area_height / 2
        squid_transform = pya.DTrans(0, False, squid_offset_x, squid_offset_y)

        # Squid Junctions
        for i in range(int(squid_count)):
            shape_lower = pya.DBox(0, 0, squid_width, self.junction_width)
            y_position = i * (squid_height + gap_size)
            squid_lower_transform = pya.DTrans(0, False, 0, y_position)
            squid_upper_transform = pya.DTrans(0, False, 0, (squid_height - self.junction_width) + y_position)
            junction_shapes.insert(squid_lower_transform * shape_lower * squid_transform)
            junction_shapes.insert(squid_upper_transform * shape_lower * squid_transform)
            [left, right] = junction_shadow(squid_width, self.junction_width)
            shadow_shapes.insert(squid_lower_transform * left * squid_transform)
            shadow_shapes.insert(squid_lower_transform * right * squid_transform)
            shadow_shapes.insert(squid_upper_transform * left * squid_transform)
            shadow_shapes.insert(squid_upper_transform * right * squid_transform)

        # Squid Pylon Wires
        for i in range(int(squid_count)):
            x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
            shape_left = pya.DBox(x_offset, 0, x_offset + self.wire_width, squid_height)
            shape_right = pya.DBox(squid_width - x_offset - self.wire_width, 0, squid_width - x_offset, squid_height)
            y_position = i * (squid_height + gap_size)
            junction_shapes.insert(pya.DTrans(0, False, 0, y_position) * shape_left * squid_transform)
            junction_shapes.insert(pya.DTrans(0, False, 0, y_position) * shape_right * squid_transform)
            ws_left = wire_shadow(
                height=squid_height - (self.junction_width * 2), i=1, x=x_offset, y=y_position + self.junction_width
            )
            shadow_shapes.insert(ws_left * squid_transform)
            ws_right = wire_shadow(
                height=squid_height - (self.junction_width * 2),
                i=2,
                x=squid_width - x_offset - self.wire_width,
                y=y_position + self.junction_width,
            )
            shadow_shapes.insert(ws_right * squid_transform)

        # SQUID Debug Gap Boxes
        for i in range(int(squid_count - 1)):
            semi_wire_width = self.wire_width / 2
            semi_squid_width = squid_width / 2
            starting_x = semi_squid_width - semi_wire_width
            ending_x = starting_x + self.wire_width
            shape = pya.DBox(starting_x, 0, ending_x, gap_size)
            y_position = (i + 1) * squid_height + i * gap_size
            gap_transform = pya.DTrans(0, False, 0, y_position)
            junction_shapes.insert(gap_transform * shape * squid_transform)
            ws = wire_shadow(gap_size, i, starting_x, y_position)
            shadow_shapes.insert(ws * squid_transform)

        # CONNECTORS
        x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
        raw_connector_length = (self.inductor_height - self.squid_area_height) / 2
        connector_length = raw_connector_length + self.finger_overlap
        wire_top = pya.DBox(x_offset, 0, x_offset + self.wire_width, connector_length)
        wire_top_transform = pya.DTrans(
            0,
            False,
            0,
            self.squid_area_height,
        )
        junction_shapes.insert(squid_transform * wire_top * wire_top_transform)
        wire_bottom = pya.DBox(x_offset, -connector_length, x_offset + self.wire_width, 0)
        wire_bottom_transform = pya.DTrans(
            0,
            False,
            0,
            0,
        )
        junction_shapes.insert(squid_transform * wire_bottom * wire_bottom_transform)
        ws_top = wire_shadow(raw_connector_length, 2, x_offset, 0)
        shadow_shapes.insert(ws_top * squid_transform * wire_top_transform)
        ws_bottom = wire_shadow(raw_connector_length, 2, x_offset, -raw_connector_length)
        shadow_shapes.insert(ws_bottom * squid_transform * wire_bottom_transform)

        # TAPPER North
        taper_unit_width = self.junction_length
        taper_unit_height = self.squid_wire_length
        double_connect_offset = self.squid_x_connector_offset * 2
        taper_north_offset_x = squid_offset_x + taper_unit_width - double_connect_offset
        taper_north_offset_y = squid_offset_y + self.squid_area_height
        taper_north_transform = pya.DTrans(0, False, taper_north_offset_x, taper_north_offset_y)
        taper_steps = int(self.taper_horizontal_displacement / self.taper_horizontal_displacement_step)
        adjusted_taper_horizontal_displacement = taper_steps * self.taper_horizontal_displacement_step
        last_taper_north_transform = None
        for i in range(taper_steps):
            taper_step_transform = pya.DTrans(
                0, False, i * self.taper_horizontal_displacement_step, i * taper_unit_height
            )
            # pylon
            if i == 0:
                x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
            else:
                x_offset = (taper_unit_width / 2) - (self.wire_width / 2)
            pylon = pya.DBox(x_offset, 0, x_offset + self.wire_width, taper_unit_height)
            junction_shapes.insert(taper_step_transform * pylon * taper_north_transform)
            # junction
            junction = pya.DBox(0, taper_unit_height - self.junction_width, taper_unit_width, taper_unit_height)
            junction_shapes.insert(taper_step_transform * junction * taper_north_transform)
            # shadow
            ws = wire_shadow(taper_unit_height - self.junction_width, i - 1, x_offset, 0)
            shadow_shapes.insert(ws * taper_north_transform * taper_step_transform)
            [jsl, jsr] = junction_shadow(taper_unit_width, self.junction_width)
            shadow_transform = pya.DTrans(0, False, 0, taper_unit_height - self.junction_width)
            shadow_shapes.insert(jsl * taper_north_transform * taper_step_transform * shadow_transform)
            shadow_shapes.insert(jsr * taper_north_transform * taper_step_transform * shadow_transform)

        last_taper_north_step_count = taper_steps
        last_taper_north_transform = taper_north_transform * pya.DTrans(
            0,
            False,
            adjusted_taper_horizontal_displacement - taper_unit_width,
            last_taper_north_step_count * taper_unit_height,
        )

        # TAPPER South
        taper_unit_width = self.junction_length
        taper_unit_height = self.squid_wire_length
        double_connect_offset = self.squid_x_connector_offset * 2
        taper_south_offset_x = squid_offset_x + taper_unit_width - double_connect_offset
        taper_south_offset_y = squid_offset_y - self.squid_wire_length
        taper_south_transform = pya.DTrans(0, False, taper_south_offset_x, taper_south_offset_y)
        taper_steps = int(self.taper_horizontal_displacement / self.taper_horizontal_displacement_step)
        adjusted_taper_horizontal_displacement = taper_steps * self.taper_horizontal_displacement_step
        for i in range(taper_steps):
            taper_step_transform = pya.DTrans(
                0, False, i * self.taper_horizontal_displacement_step, -i * taper_unit_height
            )
            # pylon
            if i == 0:
                x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
            else:
                x_offset = (taper_unit_width / 2) - (self.wire_width / 2)
            pylon = pya.DBox(x_offset, 0, x_offset + self.wire_width, taper_unit_height)
            junction_shapes.insert(taper_step_transform * pylon * taper_south_transform)
            # junction
            junction = pya.DBox(0, 0, taper_unit_width, self.junction_width)
            junction_shapes.insert(taper_step_transform * junction * taper_south_transform)
            # shadow
            ws = wire_shadow(taper_unit_height - self.junction_width, i - 1, x_offset, self.junction_width)
            shadow_shapes.insert(ws * taper_south_transform * taper_step_transform)
            [jsl, jsr] = junction_shadow(taper_unit_width, self.junction_width)
            shadow_shapes.insert(jsl * taper_south_transform * taper_step_transform)
            shadow_shapes.insert(jsr * taper_south_transform * taper_step_transform)

        last_taper_south_step_count = taper_steps
        last_taper_south_transform = taper_south_transform * pya.DTrans(
            0,
            False,
            adjusted_taper_horizontal_displacement - taper_unit_width,
            -(last_taper_north_step_count - 1) * taper_unit_height,
        )

        bend_height = self.squid_wire_length

        # Tower NordWest
        tower_unit_width = self.junction_length
        tower_unit_height = self.squid_wire_length
        tower_north_transform = last_taper_north_transform
        last_point = pya.DPoint(0, 0) * tower_north_transform
        available_height = (self.inductor_height - (self.inductor_padding + bend_height)) - last_point.y
        stored_available_height = available_height
        tower_desired_height = available_height
        tower_steps = int(tower_desired_height / tower_unit_height)
        adjusted_tower_height = tower_steps * tower_unit_height
        tower_unit_height = adjusted_tower_height / tower_steps
        for i in range(tower_steps):
            tower_step_transform = pya.DTrans(0, False, tower_unit_width, i * tower_unit_height)
            x_offset = (tower_unit_width / 2) - (self.wire_width / 2)
            # pylon
            pylon = pya.DBox(x_offset, 0, x_offset + self.wire_width, tower_unit_height)
            junction_shapes.insert(tower_step_transform * pylon * tower_north_transform)
            # junction
            junction = pya.DBox(0, tower_unit_height - self.junction_width, tower_unit_width, tower_unit_height)
            junction_shapes.insert(tower_step_transform * junction * tower_north_transform)
            # shadow
            ws = wire_shadow(tower_unit_height - self.junction_width, i + last_taper_north_step_count - 1, x_offset, 0)
            shadow_shapes.insert(ws * tower_north_transform * tower_step_transform)
            [jsl, jsr] = junction_shadow(tower_unit_width, self.junction_width)
            shadow_transform = pya.DTrans(0, False, 0, tower_unit_height - (self.junction_width))
            shadow_shapes.insert(jsl * tower_north_transform * tower_step_transform * shadow_transform)
            shadow_shapes.insert(jsr * tower_north_transform * tower_step_transform * shadow_transform)

        # North Bend
        last_tower_north_transform = (
            pya.DTrans(0, False, tower_unit_width, tower_steps * tower_unit_height) * tower_north_transform
        )
        bend_unit_width = self.junction_length * self.bend_width_multiplier
        bend_unit_height = self.squid_wire_length
        x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
        bend_transform = pya.DTrans(0, False, tower_unit_width - (x_offset * 2), 0)
        pylon_left = pya.DBox(x_offset, 0, x_offset + self.wire_width, bend_unit_height)
        junction_shapes.insert(bend_transform * pylon_left * last_tower_north_transform)
        pylon_right = pya.DBox(
            bend_unit_width - x_offset, 0, bend_unit_width - x_offset + self.wire_width, bend_unit_height
        )
        junction_shapes.insert(bend_transform * pylon_right * last_tower_north_transform)
        bend_junction = pya.DBox(0, bend_unit_height - self.junction_width, bend_unit_width, bend_unit_height)
        junction_shapes.insert(bend_transform * bend_junction * last_tower_north_transform)
        # shadow
        wsl = wire_shadow(bend_unit_height - self.junction_width, 0, x_offset, 0)
        shadow_shapes.insert(wsl * last_tower_north_transform * bend_transform)
        wsr = wire_shadow(bend_unit_height - self.junction_width, 1, x_offset, 0)
        wsr_transform = pya.DTrans(0, False, bend_unit_width - (x_offset * 2), 0)
        shadow_shapes.insert(wsr * last_tower_north_transform * bend_transform * wsr_transform)
        [jsl, jsr] = junction_shadow(bend_unit_width, self.junction_width)
        js_transform = pya.DTrans(0, False, 0, bend_unit_height - self.junction_width)
        shadow_shapes.insert(jsl * last_tower_north_transform * bend_transform * js_transform)
        shadow_shapes.insert(jsr * last_tower_north_transform * bend_transform * js_transform)

        # Tower NordEast
        tower_unit_width = self.junction_length
        tower_unit_height = self.squid_wire_length
        x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
        last_bend_transform = pya.DTrans(0, False, bend_unit_width - (x_offset * 2), 0)
        tower_north_bend_transform = last_tower_north_transform * last_bend_transform
        last_point = pya.DPoint(0, 0) * tower_north_bend_transform
        available_height = (self.inductor_height / 2) - (self.inductor_padding + bend_height)
        tower_north_east_transform = pya.DTrans(
            0, False, last_point.x - (x_offset * 2), last_point.y - available_height
        )
        tower_desired_height = available_height
        tower_steps = int(tower_desired_height / tower_unit_height)
        adjusted_tower_height = tower_steps * tower_unit_height
        tower_unit_height = adjusted_tower_height / tower_steps
        for i in range(tower_steps):
            x_offset = (tower_unit_width / 2) - (self.wire_width / 2)
            tower_step_transform = pya.DTrans(0, False, tower_unit_width, i * tower_unit_height)
            # wire
            pylon = pya.DBox(x_offset, 0, x_offset + self.wire_width, tower_unit_height)
            junction_shapes.insert(tower_step_transform * pylon * tower_north_east_transform)
            # junction
            junction = pya.DBox(0, tower_unit_height - self.junction_width, tower_unit_width, tower_unit_height)
            junction_shapes.insert(tower_step_transform * junction * tower_north_east_transform)
            # shadow
            last_shadow_offset = 0
            if i == 0:
                last_shadow_offset = -self.junction_width / 2
            ws = wire_shadow(
                tower_unit_height - self.junction_width + last_shadow_offset,
                i + last_taper_north_step_count - 1,
                x_offset,
                -last_shadow_offset,
            )
            shadow_shapes.insert(ws * tower_north_east_transform * tower_step_transform)
            [jsl, jsr] = junction_shadow(tower_unit_width, self.junction_width)
            shadow_transform = pya.DTrans(0, False, 0, tower_unit_height - (self.junction_width))
            shadow_shapes.insert(jsl * tower_north_east_transform * tower_step_transform * shadow_transform)
            shadow_shapes.insert(jsr * tower_north_east_transform * tower_step_transform * shadow_transform)

        # Tower SouthWest (Inverted version of Tower NordWest)
        tower_unit_width = self.junction_length
        tower_unit_height = self.squid_wire_length
        tower_south_transform = last_taper_south_transform
        last_point = pya.DPoint(0, 0) * tower_south_transform
        available_height = (
            stored_available_height  # ((self.inductor_height) - (self.inductor_padding + bend_height)) - last_point.y
        )
        tower_desired_height = available_height
        tower_steps = int(tower_desired_height / tower_unit_height)
        adjusted_tower_height = tower_steps * tower_unit_height
        tower_unit_height = adjusted_tower_height / tower_steps
        for i in range(tower_steps):
            tower_step_transform = pya.DTrans(0, False, tower_unit_width, -i * tower_unit_height)
            x_offset = (tower_unit_width / 2) - (self.wire_width / 2)
            # wire
            pylon = pya.DBox(x_offset, -tower_unit_height, x_offset + self.wire_width, 0)
            junction_shapes.insert(tower_step_transform * pylon * tower_south_transform)
            # junction
            junction = pya.DBox(0, -tower_unit_height, tower_unit_width, -tower_unit_height + self.junction_width)
            junction_shapes.insert(tower_step_transform * junction * tower_south_transform)
            # shadow
            ws = wire_shadow(
                tower_unit_height - self.junction_width,
                i + last_taper_south_step_count - 1,
                x_offset,
                self.junction_width,
            )
            shadow_transform = pya.DTrans(0, False, 0, -tower_unit_height)
            shadow_shapes.insert(ws * tower_south_transform * tower_step_transform * shadow_transform)
            [jsl, jsr] = junction_shadow(tower_unit_width, self.junction_width)
            shadow_shapes.insert(jsl * tower_south_transform * tower_step_transform * shadow_transform)
            shadow_shapes.insert(jsr * tower_south_transform * tower_step_transform * shadow_transform)

        # South Bend (Inverted version of North Bend)
        last_tower_south_transform = (
            pya.DTrans(0, False, tower_unit_width, -tower_steps * tower_unit_height) * tower_south_transform
        )
        bend_unit_width = self.junction_length * self.bend_width_multiplier
        bend_unit_height = self.squid_wire_length
        x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
        bend_transform = pya.DTrans(0, False, tower_unit_width - (x_offset * 2), 0)
        pylon_left = pya.DBox(x_offset, -bend_unit_height, x_offset + self.wire_width, 0)
        junction_shapes.insert(bend_transform * pylon_left * last_tower_south_transform)
        pylon_right = pya.DBox(
            bend_unit_width - x_offset, -bend_unit_height, bend_unit_width - x_offset + self.wire_width, 0
        )
        junction_shapes.insert(bend_transform * pylon_right * last_tower_south_transform)
        bend_junction = pya.DBox(0, -bend_unit_height, bend_unit_width, -bend_unit_height + self.junction_width)
        junction_shapes.insert(bend_transform * bend_junction * last_tower_south_transform)
        # shadow
        shadow_bend_transform = pya.DTrans(0, False, 0, -bend_unit_height)
        wsl = wire_shadow(bend_unit_height - self.junction_width, 0, x_offset, self.junction_width)
        shadow_shapes.insert(wsl * last_tower_south_transform * bend_transform * shadow_bend_transform)
        wsr = wire_shadow(bend_unit_height - self.junction_width, 1, x_offset, self.junction_width)
        wsr_transform = pya.DTrans(0, False, bend_unit_width - (x_offset * 2), 0)
        shadow_shapes.insert(wsr * last_tower_south_transform * bend_transform * wsr_transform * shadow_bend_transform)
        [jsl, jsr] = junction_shadow(bend_unit_width, self.junction_width)
        shadow_shapes.insert(jsl * last_tower_south_transform * bend_transform * shadow_bend_transform)
        shadow_shapes.insert(jsr * last_tower_south_transform * bend_transform * shadow_bend_transform)

        # Tower SouthEast (Inverted version of Tower NordEast)
        tower_unit_width = self.junction_length
        tower_unit_height = self.squid_wire_length
        x_offset = self.squid_x_connector_offset - (self.wire_width / 2)
        last_bend_transform = pya.DTrans(0, False, bend_unit_width - (x_offset * 2), 0)
        tower_south_bend_transform = last_tower_south_transform * last_bend_transform
        last_point = pya.DPoint(0, 0) * tower_south_bend_transform
        available_height = (self.inductor_height / 2) - (self.inductor_padding + bend_height)
        tower_south_east_transform = pya.DTrans(
            0, False, last_point.x - (x_offset * 2), last_point.y + available_height
        )
        tower_desired_height = available_height
        tower_steps = int(tower_desired_height / tower_unit_height)
        adjusted_tower_height = tower_steps * tower_unit_height
        tower_unit_height = adjusted_tower_height / tower_steps
        last_mid_point = None
        for i in range(tower_steps):
            x_offset = (tower_unit_width / 2) - (self.wire_width / 2)
            tower_step_transform = pya.DTrans(0, False, tower_unit_width, -i * tower_unit_height)
            # wire
            pylon = pya.DBox(x_offset, -tower_unit_height, x_offset + self.wire_width, 0)
            junction_shapes.insert(tower_step_transform * pylon * tower_south_east_transform)
            last_mid_point = tower_step_transform * tower_south_east_transform
            # junction
            junction = pya.DBox(0, -tower_unit_height, tower_unit_width, -tower_unit_height + self.junction_width)
            junction_shapes.insert(tower_step_transform * junction * tower_south_east_transform)
            # shadow
            last_shadow_offset = 0
            if i == 0:
                last_shadow_offset = -self.junction_width / 2
            shadow_transform = pya.DTrans(0, False, 0, -tower_unit_height)
            ws = wire_shadow(
                tower_unit_height - self.junction_width + last_shadow_offset,
                i + last_taper_north_step_count - 1,
                x_offset,
                self.junction_width,
            )
            shadow_shapes.insert(ws * tower_south_east_transform * tower_step_transform * shadow_transform)
            [jsl, jsr] = junction_shadow(tower_unit_width, self.junction_width)
            shadow_shapes.insert(jsl * tower_south_east_transform * tower_step_transform * shadow_transform)
            shadow_shapes.insert(jsr * tower_south_east_transform * tower_step_transform * shadow_transform)

        # Phase Slip Junction
        slip_unit_width = self.phase_slip_junction_length
        slip_unit_height = self.junction_width
        last_tower_point = pya.DPoint(0, 0) * last_mid_point
        phase_junction = pya.DBox(
            -slip_unit_width / 2, -slip_unit_height / 2, slip_unit_width / 2, slip_unit_height / 2
        )
        phase_junction_transform = pya.DTrans(
            0, False, last_tower_point.x + (tower_unit_width / 2), self.inductor_height / 2
        )
        junction_shapes.insert(phase_junction * phase_junction_transform)
        phase_junction_shadow_transform = pya.DTrans(
            0,
            False,
            last_tower_point.x + ((tower_unit_width - slip_unit_width) / 2),
            (self.inductor_height / 2) - (self.junction_width / 2),
        )
        [jsl, jsr] = junction_shadow(slip_unit_width, self.junction_width)
        shadow_shapes.insert(jsl * phase_junction_shadow_transform)
        shadow_shapes.insert(jsr * phase_junction_shadow_transform)

    def _add_shapes(self, shapes, layer):
        """Merge shapes into a region and add it to layer."""
        region = pya.Region(shapes).merged()
        self.cell.shapes(self.get_layer(layer)).insert(region)

    def _add_refpoints(self):
        """Adds the "origin_squid" refpoint and port "common"."""
        self.refpoints["origin_squid"] = pya.DPoint(0, 0)
        self.add_port("common", pya.DPoint(0, self.inductor_height))

    def _produce_ground_metal_shapes(self):
        """Produces hardcoded shapes in metal gap and metal addition layers."""
        # metal additions bottom
        # x0 = -self.a / 2
        # y0 = self.inductor_height / 2
        bottom_pts = []
        if self.include_base_metal_addition:
            shape = polygon_with_vsym(bottom_pts)
            # self.cell.shapes(self.get_layer("base_metal_addition")).insert(shape)
            # metal additions top
            top_pts = []
            shape = polygon_with_vsym(top_pts)
            self.cell.shapes(self.get_layer("base_metal_addition")).insert(shape)
        # metal gap
        if self.include_base_metal_gap:
            if self.include_base_metal_addition:
                pts = (
                    bottom_pts
                    + [
                        pya.DPoint(-self.inductor_width / 2, 0),
                        pya.DPoint(-self.inductor_width / 2, self.inductor_height),
                    ]
                    + top_pts[::-1]
                )
            else:
                pts = [
                    pya.DPoint(-self.inductor_width / 2, 0),
                    pya.DPoint(-self.inductor_width / 2, self.inductor_height),
                ]
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
