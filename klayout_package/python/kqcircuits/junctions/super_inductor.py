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

    # wire_length < junction_length
    # wire_width = ??
    # junction_count = exclude squid count; resize all
    # bend_length
    # connection_wires_length =
    # junction_base_tappering = 

    wire_width = Param(pdt.TypeDouble, "Wire width", 0.02, unit="μm")
    phase_slip_junction_length = Param(pdt.TypeDouble, "Phase slip junction length", 0.5, unit="μm")
    squid_area_width = Param(pdt.TypeDouble, "Width of Squids Area.", 0.5, unit="μm")
    squid_area_height = Param(pdt.TypeDouble, "Height of Squids Area.", 1.0, unit="μm")
    squid_count = Param(pdt.TypeInt, "Number of Squids in the Super Inductor.", 4)
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
        """Create junction fingers and add them to some SIS layer.
        Choose 'SIS_junction' layer by default but 'SIS_junction_2' if ``separate_junctions`` is True.
        """
        layer_name = "SIS_junction_2" if self.separate_junctions else "SIS_junction"
        shape_into = self.cell.shapes(self.get_layer(layer_name))

        # SQUID ARRAY - Corrected version
        squid_width = self.squid_area_width
        squid_count = self.squid_count
        gap_size = self.squid_junction_length 

        # Calculate available space for the boxes themselves
        total_gap_space = gap_size * (squid_count - 1)
        available_space_for_boxes = self.squid_area_height - total_gap_space
        squid_height = available_space_for_boxes / squid_count

        squid_offset_x = -squid_width / 2
        squid_offset_y = self.height / 2 - self.squid_area_height / 2

        enclosing_box = pya.DBox(0, 0, self.squid_area_width, self.squid_area_height)
        squid_transform = pya.DTrans(0, False, squid_offset_x, squid_offset_y)
        # shape_into.insert(squid_transform * enclosing_box)

        # SQUID Debug Boxes
        for i in range(int(squid_count)):
            shape = pya.DBox(0, 0, squid_width, squid_height)
            y_position = i * (squid_height + gap_size)
            moved = pya.DTrans(0, False, 0, y_position) * shape * squid_transform
            #shape_into.insert(moved)
        
        # Squid Junctions
        for i in range(int(squid_count)):
            shape_lower = pya.DBox(0, 0, squid_width, self.junction_width)
            shape_upper = pya.DBox(
                0, squid_height - self.junction_width, 
                squid_width, squid_height
            )
            y_position = i * (squid_height + gap_size)
            shape_into.insert(
                pya.DTrans(0, False, 0, y_position) * shape_lower * squid_transform
            )
            shape_into.insert(
                pya.DTrans(0, False, 0, y_position) * shape_upper * squid_transform
            )

        # Squid Pillar Wires
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

        # Tower NordEast
        last_tapper_north_x = (adjusted_tapper_horizontal_displacement * tapper_steps)
        last_tapper_north_y = (tapper_unit_height * tapper_steps)

        tower_unit_width = self.squid_area_width
        tower_unit_height = self.squid_junction_length
        tower_north_offset_x = squid_offset_x + last_tapper_north_x
        tower_north_offset_y = squid_offset_y + last_tapper_north_y
        tower_north_transform = last_tapper_north_transform
        tower_desired_height = 2.0
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


        
        # jx = top_corner.x - (top_corner.y - b_corner_y) / 2
        # jy = (top_corner.y + b_corner_y) / 2
        # ddb = self.junction_width * sqrt(0.5)
        # ddt = self.junction_width * sqrt(0.5)
        # if self.mirror_offset:
        #     ddt += self.offset_compensation * sqrt(0.5)
        # else:
        #     ddb += self.offset_compensation * sqrt(0.5)
        # fo = self.finger_overshoot * sqrt(0.5) - 1.1
        # pl = self.finger_overlap * sqrt(0.5) + 0.2  # plus length to connect despite of rounding

        # def finger_points(size):
        #     return [
        #         pya.DPoint(top_corner.x + pl, top_corner.y + size + pl),
        #         pya.DPoint(top_corner.x + size + pl, top_corner.y + pl),
        #         pya.DPoint(jx - fo, jy - fo - size),
        #         pya.DPoint(jx - fo - size, jy - fo),
        #     ]

        # finger_bottom = pya.DTrans(-jx, -jy + self.x_offset) * pya.DPolygon(finger_points(ddb))
        # finger_top = pya.DTrans(-jx + self.x_offset, -jy) * pya.DPolygon(finger_points(ddt))

        # junction_shapes = [
        #     (pya.DTrans(jx - finger_margin, jy) * finger_top).to_itype(self.layout.dbu),
        #     (pya.DTrans(0, False, jx - 2 * top_corner.x, jy) * finger_top).to_itype(self.layout.dbu),
        #     (pya.DTrans(3, False, jx - finger_margin, jy + 2.2) * finger_bottom).to_itype(self.layout.dbu),
        #     (pya.DTrans(3, False, jx - 2 * top_corner.x, jy + 2.2) * finger_bottom).to_itype(self.layout.dbu),
        # ]

        # junction_region = pya.Region(junction_shapes).merged()
        # layer_name = "SIS_junction_2" if self.separate_junctions else "SIS_junction"
        # self.cell.shapes(self.get_layer(layer_name)).insert(junction_region)

        # # place refpoint at the middle of the junctions
        # self.refpoints["c"] = pya.DPoint(jx + 1.1 - finger_margin, jy + 1.1)

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
            self.cell.shapes(self.get_layer("base_metal_addition")).insert(shape)
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
            self.cell.shapes(self.get_layer("base_metal_addition")).insert(shape)
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
