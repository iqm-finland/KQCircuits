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


from math import sqrt
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.junctions.squid import Squid
from kqcircuits.util.symmetric_polygons import polygon_with_vsym


class Manhattan(Squid):
    """The PCell declaration for a Manhattan style SQUID.

    This SQUID has two distinct sub-types automatically selected by loop-area.
    """

    finger_overshoot = Param(pdt.TypeDouble, "Length of fingers after the junction.", 1.0, unit="μm")
    include_base_metal_gap = Param(pdt.TypeBoolean, "Include base metal gap layer", True)
    shadow_margin = Param(pdt.TypeDouble, "Shadow layer margin near the the pads", 1.0, unit="μm")
    compact_geometry = Param(pdt.TypeBoolean, "Compact geometry for metal addition.", False)
    separate_junctions = Param(pdt.TypeBoolean, "Junctions to separate layer", False)
    offset_compensation = Param(pdt.TypeDouble, "Junction lead offset from junction width", 0, unit="μm")
    mirror_offset = Param(pdt.TypeBoolean, "Move the junction lead offset to the other lead", False)
    finger_overlap = Param(pdt.TypeDouble, "Length of fingers inside the pads", 0.2, unit="μm")
    single_junction = Param(pdt.TypeBoolean, "Disable the second junction", False)

    def build(self):
        self.produce_manhattan_squid(top_pad_layer="SIS_junction")

    def produce_manhattan_squid(self, top_pad_layer):

        # geometry constants
        big_loop_height = 10
        loop_bottom_y = 1.5
        self.metal_gap_top_y = 20 if self.compact_geometry else 26.5
        self.width = 36 if self.compact_geometry else 38  # total width of junction layer
        self.height = 17 if self.compact_geometry else 20.2  # total height of junction layer
        bp_height = 5  # bottom pad height
        tp_width = 10  # top pad width
        brim_height = 1  # thickness of the "top-hat's" brim
        small_loop_height = 5.2
        small_hat_width = 2  # width of the small hat shape, in case of small loop

        # corner rounding parameters
        rounding_params = {
            "rinner": 0.5,  # inner corner rounding radius
            "router": 0.5,  # outer corner rounding radius
            "n": 64,  # number of point per rounded corner
        }

        # convenience variables
        delta_j = self.loop_area / big_loop_height # junction distance, a.k.a. loop width
        tp_height = self.height - loop_bottom_y - big_loop_height  # top pad height
        bp_gap_x = -self.width / 2 + (self.width - delta_j) / 2  # bottom gap left edge x-coordinate
        bp_gap_x_min = -self.width / 2 + 7  # fixed at minimum size
        finger_margin = brim_height  # make hats brim this much wider for good finger connection

        # adjust for small loop geometry
        small_loop = tp_width > -bp_gap_x * 2
        if small_loop:
            bp_gap_x = bp_gap_x_min
            delta_j = self.loop_area / small_loop_height

        junction_shapes_top = []
        junction_shapes_bottom = []
        shadow_shapes = []

        # create rounded bottom part and top parts
        self.produce_contact_pads(top_pad_layer, bp_height, bp_gap_x, tp_height, tp_width,
                                  big_loop_height, junction_shapes_bottom, rounding_params,
                                  shadow_shapes, junction_shapes_top)

        # create rectangular junction-support structures and junctions
        if small_loop:
            small_hat = [
                pya.DPoint(-small_hat_width / 2, self.height - tp_height),
                pya.DPoint(-small_hat_width / 2, small_loop_height + loop_bottom_y + brim_height),
                pya.DPoint(-delta_j / 2 - finger_margin, small_loop_height + loop_bottom_y + brim_height),
                pya.DPoint(-delta_j / 2 - finger_margin, small_loop_height + loop_bottom_y)
            ]
            junction_shapes_top.append(polygon_with_vsym(small_hat).to_itype(self.layout.dbu))
            if top_pad_layer != "SIS_junction":
                junction_shapes_bottom.append(polygon_with_vsym(small_hat).to_itype(self.layout.dbu))
            small_hat_shadow = [
                small_hat[0] + pya.DPoint(-self.shadow_margin, -self.shadow_margin),
                small_hat[1] + pya.DPoint(-self.shadow_margin, self.shadow_margin),
                small_hat[2] + pya.DPoint(-self.shadow_margin, self.shadow_margin),
                small_hat[3] + pya.DPoint(-self.shadow_margin, -self.shadow_margin),
            ]
            shadow_shapes.append(polygon_with_vsym(small_hat_shadow).to_itype(self.layout.dbu))
            small_hat[3].x += finger_margin
            self._make_junctions(small_hat[3], loop_bottom_y)
        else:
            tp_brim_left = [
                pya.DPoint(-delta_j / 2 - finger_margin, self.height - tp_height + brim_height),
                pya.DPoint(-delta_j / 2 - finger_margin, self.height - tp_height)
            ]
            junction_shapes_top.append(polygon_with_vsym(tp_brim_left).to_itype(self.layout.dbu))
            if top_pad_layer != "SIS_junction":
                junction_shapes_bottom.append(polygon_with_vsym(tp_brim_left).to_itype(self.layout.dbu))
            tp_brim_shadow_pts = [
                tp_brim_left[0] + pya.DPoint(-self.shadow_margin, self.shadow_margin),
                tp_brim_left[1] + pya.DPoint(-self.shadow_margin, -self.shadow_margin),
            ]
            shadow_shapes.append(polygon_with_vsym(tp_brim_shadow_pts).to_itype(self.layout.dbu))
            tp_brim_left[1].x += finger_margin
            self._make_junctions(tp_brim_left[1], bp_height, finger_margin)

        self._add_shapes(junction_shapes_bottom, "SIS_junction")
        self._add_shapes(junction_shapes_top, top_pad_layer)
        self._add_shapes(shadow_shapes, "SIS_shadow")
        self._produce_ground_grid_avoidance()
        self._produce_ground_metal_shapes()
        self._add_refpoints()

    def produce_contact_pads(self,top_pad_layer, bp_height, bp_gap_x, tp_height,tp_width, big_loop_height,
                             junction_shapes_bottom, rounding_params, shadow_shapes, junction_shapes_top):

        bp_pts_left = [
            pya.DPoint(-self.width / 2, -0.5),
            pya.DPoint(-self.width / 2, bp_height),
            pya.DPoint(bp_gap_x, bp_height),
            pya.DPoint(bp_gap_x, self.height - tp_height - big_loop_height)
        ]
        bp_shape = polygon_with_vsym(bp_pts_left)
        self._round_corners_and_append(bp_shape, junction_shapes_bottom, rounding_params)

        bp_shadow_pts_left = [
            bp_pts_left[0] + pya.DPoint(-self.shadow_margin, -self.shadow_margin),
            bp_pts_left[1] + pya.DPoint(-self.shadow_margin, self.shadow_margin),
            bp_pts_left[2] + pya.DPoint(self.shadow_margin, self.shadow_margin),
            bp_pts_left[3] + pya.DPoint(self.shadow_margin, self.shadow_margin),
        ]
        bp_shadow_shape = polygon_with_vsym(bp_shadow_pts_left)
        self._round_corners_and_append(bp_shadow_shape, shadow_shapes, rounding_params)

        # create rounded top part

        tp_pts_left = [
            pya.DPoint(-tp_width / 2, self.height),
            pya.DPoint(-tp_width / 2, self.height - tp_height),
        ]
        tp_shape = polygon_with_vsym(tp_pts_left)
        self._round_corners_and_append(tp_shape, junction_shapes_top, rounding_params)

        # add top pad to bottom shapes in case another layer is used for the upper part of the squid

        if top_pad_layer != "SIS_junction":
            self._round_corners_and_append(tp_shape, junction_shapes_bottom, rounding_params)

        tp_shadow_pts_left = [
            tp_pts_left[0] + pya.DPoint(-self.shadow_margin, self.shadow_margin),
            tp_pts_left[1] + pya.DPoint(-self.shadow_margin, -self.shadow_margin),
        ]
        tp_shadow_shape = polygon_with_vsym(tp_shadow_pts_left)
        self._round_corners_and_append(tp_shadow_shape, shadow_shapes, rounding_params)

    def _make_junctions(self, top_corner, b_corner_y, finger_margin=0):
        """Create junction fingers and add them to some SIS layer.

        Choose 'SIS_junction' layer by default but 'SIS_junction_2' if ``separate_junctions`` is True.
        """
        jx = top_corner.x - (top_corner.y - b_corner_y) / 2
        jy = (top_corner.y + b_corner_y) / 2
        ddb = self.junction_width * sqrt(0.5)
        ddt = self.junction_width * sqrt(0.5)
        if self.mirror_offset:
            ddt += self.offset_compensation * sqrt(0.5)
        else:
            ddb += self.offset_compensation * sqrt(0.5)
        fo = self.finger_overshoot * sqrt(0.5)
        pl = self.finger_overlap * sqrt(0.5)  # plus length to connect despite of rounding

        def finger_points(size):
            return [
                pya.DPoint(top_corner.x + pl, top_corner.y + size + pl),
                pya.DPoint(top_corner.x + size + pl, top_corner.y + pl),
                pya.DPoint(jx - fo, jy - fo - size),
                pya.DPoint(jx - fo - size, jy - fo),
            ]

        finger_bottom = pya.DTrans(-jx, -jy) * pya.DPolygon(finger_points(ddb))
        finger_top = pya.DTrans(-jx, -jy) * pya.DPolygon(finger_points(ddt))

        squa = sqrt(2) / 2
        if self.single_junction:
            junction_shapes = [
                (pya.DTrans(jx - finger_margin, jy) * finger_top).to_itype(self.layout.dbu),
                (pya.DTrans(3, False, jx - finger_margin, jy) * finger_bottom).to_itype(self.layout.dbu),
            ]
            # place refpoints at the middle of the junction. In this case, "l" and "r" coincide.
            self.refpoints["l"] = pya.DPoint(jx - fo - finger_margin + self.finger_overshoot * squa,
                                            jy - fo + self.finger_overshoot * squa)
            self.refpoints["r"] = self.refpoints["l"]
        else:
            junction_shapes = [
                (pya.DTrans(jx - finger_margin, jy) * finger_top).to_itype(self.layout.dbu),
                (pya.DTrans(0, False, jx - 2 * top_corner.x, jy) * finger_top).to_itype(self.layout.dbu),
                (pya.DTrans(3, False, jx - finger_margin, jy) * finger_bottom).to_itype(self.layout.dbu),
                (pya.DTrans(3, False, jx - 2 * top_corner.x, jy) * finger_bottom).to_itype(self.layout.dbu)
            ]
            # place refpoints at the middle of the left and right junctions
            self.refpoints["l"] = pya.DPoint(jx - fo - finger_margin + self.finger_overshoot * squa,
                                            jy - fo + self.finger_overshoot * squa)
            self.refpoints["r"] = pya.DPoint(jx - fo - 2 * top_corner.x + self.finger_overshoot * squa,
                                            jy - fo + self.finger_overshoot * squa)

        junction_region = pya.Region(junction_shapes).merged()
        layer_name = "SIS_junction_2" if self.separate_junctions else "SIS_junction"
        self.cell.shapes(self.get_layer(layer_name)).insert(junction_region)

    def _add_shapes(self, shapes, layer):
        """Merge shapes into a region and add it to layer."""
        region = pya.Region(shapes).merged()
        self.cell.shapes(self.get_layer(layer)).insert(region)

    def _add_refpoints(self):
        """Adds the "origin_squid" refpoint and port "common"."""
        self.refpoints["origin_squid"] = pya.DPoint(0, 0)
        self.add_port("common", pya.DPoint(0, self.metal_gap_top_y))

    def _produce_ground_metal_shapes(self):
        """Produces hardcoded shapes in metal gap and metal addition layers."""
        # metal additions bottom
        x0 = -12 if self.compact_geometry else -13
        y0 = -1
        bottom_pts = [
            pya.DPoint(x0 - 3, y0 - 1),
            pya.DPoint(x0 - 3, y0 + 2),
            pya.DPoint(x0 - 5, y0 + 2),
            pya.DPoint(x0 - 5, y0 + 5),
            pya.DPoint(x0, y0 + 5),
            pya.DPoint(x0, y0 + 1)
        ]
        shape = polygon_with_vsym(bottom_pts)
        self.cell.shapes(self.get_layer("base_metal_addition")).insert(shape)
        # metal additions top
        y0 = 12 if self.compact_geometry else 14.5
        top_pts = [
            pya.DPoint(-2, y0 + 3),
            pya.DPoint(-2, y0 + 1),
            pya.DPoint(-1, y0 + 1),
            pya.DPoint(-1, y0),
            pya.DPoint(-4, y0),
            pya.DPoint(-4, self.metal_gap_top_y),
        ]
        shape = polygon_with_vsym(top_pts)
        self.cell.shapes(self.get_layer("base_metal_addition")).insert(shape)
        # metal gap
        if self.include_base_metal_gap:
            pts = bottom_pts[::-1] + [pya.DPoint(-20.5, -2), pya.DPoint(-20.5, self.metal_gap_top_y)] + top_pts[::-1]
            shape = polygon_with_vsym(pts)
            self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)

    def _produce_ground_grid_avoidance(self):
        """Add ground grid avoidance."""
        w = self.cell.dbbox().width()
        h = self.cell.dbbox().height()
        protection = pya.DBox(-w / 2 - self.margin, -2 - self.margin, w / 2 + self.margin, h - 2 + self.margin)
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(protection)

    def _round_corners_and_append(self, polygon, polygon_list, rounding_params):
        """Rounds the corners of the polygon, converts it to integer coordinates, and adds it to the polygon list."""
        polygon = polygon.round_corners(rounding_params["rinner"], rounding_params["router"], rounding_params["n"])
        polygon_list.append(polygon.to_itype(self.layout.dbu))
