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
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.elements.element import Element


class MaskMarkerFc(Element):
    """The PCell declaration for a MaskMarkerFc.

    Mask alignment marker for flip-chip masks
    """

    window = Param(pdt.TypeBoolean, "Window in airbridge flyover and UBM layer", False)
    arrow_number = Param(pdt.TypeInt, "Number of arrow pairs in the marker", 3)

    @staticmethod
    def create_cross(arm_length, arm_width):

        m = arm_length / 2
        n = arm_width / 2

        cross = pya.DPolygon([
            pya.DPoint(-n, -m),
            pya.DPoint(-n, -n),
            pya.DPoint(-m, -n),
            pya.DPoint(-m, n),
            pya.DPoint(-n, n),
            pya.DPoint(-n, m),
            pya.DPoint(n, m),
            pya.DPoint(n, n),
            pya.DPoint(m, n),
            pya.DPoint(m, -n),
            pya.DPoint(n, -n),
            pya.DPoint(n, -m)
        ])

        return cross

    def build(self):

        arrow = pya.DPolygon([
            pya.DPoint(0, 0),
            pya.DPoint(-20, 20),
            pya.DPoint(-11, 25),
            pya.DPoint(-5, 19),
            pya.DPoint(-5, 62),
            pya.DPoint(5, 62),
            pya.DPoint(5, 19),
            pya.DPoint(11, 25),
            pya.DPoint(20, 20)

        ])

        layer_gap = self.get_layer("base_metal_gap_wo_grid")
        layer_pads = self.get_layer("airbridge_pads")
        layer_flyover = self.get_layer("airbridge_flyover")
        layer_ubm = self.get_layer("underbump_metallization")
        layer_indium_bump = self.get_layer("indium_bump")
        layer_protection = self.get_layer("ground_grid_avoidance")

        def insert_to_main_layers(shape):
            self.cell.shapes(layer_gap).insert(shape)
            if not self.window:
                self.cell.shapes(layer_flyover).insert(shape)

        # protection for the box
        protection_box = pya.DBox(
            pya.DPoint(200, 350),
            pya.DPoint(-200, -350)
        )
        self.cell.shapes(layer_protection).insert(protection_box)
        negative_layer = pya.Region(protection_box.to_itype(self.layout.dbu))

        # crosses

        arm_widths = [20, 35, 70]
        arm_lengths = [70, 124, 250]
        offset_width = [30, 43, 85]
        offset_length = [80, 132, 265]

        shift = pya.DPoint(0, 250)
        dislocation = 0
        for i, (cross_width, cross_length) in enumerate(zip(arm_widths, arm_lengths)):
            if i != 0:
                dislocation = arm_lengths[i - 1] + arm_lengths[i] + 100
            shift += pya.DPoint(0, -dislocation / 2)
            inner_shapes = pya.DCplxTrans(1, 0, False,
                                          pya.DVector(shift)) * self.create_cross(offset_length[i], offset_width[i])
            insert_to_main_layers(inner_shapes)
            inner_corner_shape = pya.DCplxTrans(1, 0, False,
                                                pya.DVector(shift)) * self.create_cross(cross_length, cross_width)
            for layer_insert in [layer_pads]:
                self.cell.shapes(layer_insert).insert(inner_corner_shape)
            negative_offset = pya.DCplxTrans(1, 0, False,
                                             pya.DVector(shift)) * self.create_cross(arm_lengths[i], arm_widths[i])
            negative_layer -= pya.Region(negative_offset.to_itype(self.layout.dbu))

            inner_shapes_offset = pya.DCplxTrans(1, 0, False,
                                                 pya.DVector(shift)) * self.create_cross(arm_lengths[i], arm_widths[i])
            self.cell.shapes(layer_indium_bump).insert(inner_shapes_offset)
        self.cell.shapes(layer_ubm).insert(negative_layer)
        # marker arrow
        for i in range(self.arrow_number):
            for j in [-1, 1]:
                arrows_shape = pya.DCplxTrans(1, 0, j != 1,
                                              j * pya.DVector(0, 200 * i + 400)) * arrow
                insert_to_main_layers(arrows_shape)
                for layer_insert in [layer_pads, layer_indium_bump]:
                    self.cell.shapes(layer_insert).insert(arrows_shape)

    @classmethod
    def get_marker_locations(cls, cell_marker, **kwargs):
        # set markers to the edge clearance
        wafer_center_x = kwargs.get('wafer_center_x', 0)
        wafer_center_y = kwargs.get('wafer_center_y', 0)
        wafer_rad = kwargs.get('wafer_rad', 75000)
        edge_clearance = kwargs.get('edge_clearance', 1000)
        margin = kwargs.get('box_margin', 1000)
        _h = cell_marker.dbbox().height()
        _w = cell_marker.dbbox().width()
        coordinate = math.sqrt((wafer_rad - edge_clearance) ** 2 - (_h / 2 + margin) ** 2)
        return [
            pya.DTrans(wafer_center_x - coordinate + (margin + _w/2), wafer_center_y) * pya.DTrans.M90,
            pya.DTrans(wafer_center_x + coordinate - (margin + _w/2), wafer_center_y) * pya.DTrans.R0]

    @classmethod  # TODO: this is a direct copy from marker.py Will be fixed in future issue
    def get_marker_region(cls, inst, **kwargs):
        margin = kwargs.get('box_margin', 1000)
        return pya.Region(inst.bbox()).extents(margin / inst.cell.layout().dbu)
