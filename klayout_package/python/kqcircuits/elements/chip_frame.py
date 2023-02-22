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
from kqcircuits.util.label import produce_label, LabelOrigin
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.elements.element import Element
from kqcircuits.elements.markers.marker import Marker
from kqcircuits.defaults import default_brand, default_marker_type, default_chip_label_face_prefixes


class ChipFrame(Element):
    """The PCell declaration for a chip frame.

    The chip frame consists of a dicing edge, and labels and markers in the corners.

     .. MARKERS_FOR_PNG 0,5000,10000,5000 5000,0,5000,10000
    """

    box = Param(pdt.TypeShape, "Border", pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000)),
        docstring="Bounding box of the chip frame")
    dice_width = Param(pdt.TypeDouble, "Dicing width", 200, unit="μm")
    dice_grid_margin = Param(pdt.TypeDouble, "Margin between dicing edge and ground grid", 100,
        docstring="Margin of the ground grid avoidance layer for dicing edge")
    name_mask = Param(pdt.TypeString, "Name of the mask", "M000")
    name_chip = Param(pdt.TypeString, "Name of the chip", "CTest")
    name_copy = Param(pdt.TypeString, "Name of the copy", None)
    name_brand = Param(pdt.TypeString, "Name of the brand", default_brand)
    text_margin = Param(pdt.TypeDouble, "Margin for labels", 100,
        docstring="Margin of the ground grid avoidance layer around the text")
    marker_dist = Param(pdt.TypeDouble, "Marker distance from edges", 1500,
        docstring="Distance of markers from closest edges of the chip face")
    diagonal_squares = Param(pdt.TypeInt, "Number of diagonal squares for the markers", 10)
    use_face_prefix = Param(pdt.TypeBoolean, "Use face prefix for chip name label", False)
    marker_types = Param(pdt.TypeList, "Marker type for each chip corner, clockwise starting from lower left",
                         default=[default_marker_type]*4)
    chip_dicing_width = Param(pdt.TypeDouble, "Width of the chip dicing reference line", 10.0, unit="µm")
    chip_dicing_line_length = Param(pdt.TypeDouble, "Length of the chip dicing reference line", 100.0, unit="µm")
    chip_dicing_gap_length = Param(pdt.TypeDouble, "Gap between two chip dicing reference dashes", 50.0, unit="µm")

    def build(self):
        """Produces dicing edge, markers, labels and ground grid for the chip face."""
        self._produce_dicing_edge()
        self._produce_labels()
        self._produce_markers()

    def _produce_labels(self):
        x_min, x_max, y_min, y_max = self._box_points()
        if self.use_face_prefix:
            face_id = self.face()["id"]
            face_prefix = default_chip_label_face_prefixes[face_id].upper() \
                if default_chip_label_face_prefixes and (face_id in default_chip_label_face_prefixes)\
                else face_id.upper()
            chip_name = face_prefix + self.name_chip
        else:
            chip_name = self.name_chip
        labels = [self.name_mask, chip_name, self.name_copy, self.name_brand]
        if self.name_mask:
            self._produce_label(labels[0], pya.DPoint(x_min, y_max), LabelOrigin.TOPLEFT)
        if self.name_chip:
            self._produce_label(labels[1], pya.DPoint(x_max, y_max), LabelOrigin.TOPRIGHT)
        self._produce_label(labels[2], pya.DPoint(x_max, y_min), LabelOrigin.BOTTOMRIGHT)
        self._produce_label(labels[3], pya.DPoint(x_min, y_min), LabelOrigin.BOTTOMLEFT)

    def _produce_label(self, label, location, origin):
        """Produces Text PCells with text `label` with `origin` of the text at `location`.

        Wrapper for the stand alone function `produce_label`.
        Text size scales with chip dimension for chips smaller than 7 mm.

        Args:
            label: the produced text
            location: DPoint of the location of the text
            origin: LabelOrigin of the corner of the label to be placed at the location

        Effect:
            label PCells added to the layout into the parent PCell
        """
        size = 350 * min(1, self.box.width() / 7000, self.box.height() / 7000)
        produce_label(self.cell, label, location, origin, self.dice_width, self.text_margin,
                      [self.face()["base_metal_gap_wo_grid"], self.face()["base_metal_gap_for_EBL"]],
                      self.face()["ground_grid_avoidance"], size)

    def _produce_markers(self):
        x_min, x_max, y_min, y_max = self._box_points()
        self._produce_marker(self.marker_types[0], pya.DTrans(x_min + self.marker_dist, y_min + self.marker_dist) \
                             * pya.DTrans.R180, self.face()["id"] + "_marker_sw")
        self._produce_marker(self.marker_types[3], pya.DTrans(x_max - self.marker_dist, y_min + self.marker_dist) \
                             * pya.DTrans.R270, self.face()["id"] + "_marker_se")
        self._produce_marker(self.marker_types[1], pya.DTrans(x_min + self.marker_dist, y_max - self.marker_dist) \
                             * pya.DTrans.R90, self.face()["id"] + "_marker_nw")
        self._produce_marker(self.marker_types[2], pya.DTrans(x_max - self.marker_dist, y_max - self.marker_dist) \
                             * pya.DTrans.R0, self.face()["id"] + "_marker_ne")

    def _produce_marker(self, marker_type, trans, name):
        if not marker_type:
            return
        cell_marker = self.add_element(Marker, marker_type=marker_type)
        self.insert_cell(cell_marker, trans)
        self.refpoints[name] = trans.disp

    def _produce_dicing_edge(self):
        shape = pya.DPolygon(self._border_points(self.dice_width))
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)
        self.cell.shapes(self.get_layer("base_metal_gap_for_EBL")).insert(shape)

        protection = pya.DPolygon(self._border_points(self.dice_width + self.dice_grid_margin, self.margin))
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(protection)

        box_points = self._box_points()
        p1 = pya.DPoint(box_points[0], box_points[2])
        p2 = pya.DPoint(box_points[1], box_points[2])
        p3 = pya.DPoint(box_points[0], box_points[3])
        p4 = pya.DPoint(box_points[1], box_points[3])
        self._produce_lines_along_edge(p1.y, p3.y, True,  p1)
        self._produce_lines_along_edge(p1.x, p2.x, False, p1)
        self._produce_lines_along_edge(p2.y, p4.y, True,  p2)
        self._produce_lines_along_edge(p3.x, p4.x, False, p3)

    def _box_points(self):
        """Returns x_min, x_max, y_min, y_max for the given box."""
        x_min = min(self.box.p1.x, self.box.p2.x)
        x_max = max(self.box.p1.x, self.box.p2.x)
        y_min = min(self.box.p1.y, self.box.p2.y)
        y_max = max(self.box.p1.y, self.box.p2.y)
        return x_min, x_max, y_min, y_max

    def _border_points(self, w, extension=0):
        """Returns a set of points forming frame with outer edge on the chip boundaries, and frame thickness ``w``.
        Optional parameter ``extension`` extends the outer edge of the box.
        """
        x_min, x_max, y_min, y_max = self._box_points()
        points = [
            pya.DPoint(x_min - extension, y_min - extension),
            pya.DPoint(x_max + extension, y_min - extension),
            pya.DPoint(x_max + extension, y_max + extension),
            pya.DPoint(x_min - extension, y_max + extension),
            pya.DPoint(x_min - extension, y_min - extension),

            pya.DPoint(x_min + w, y_min + w),
            pya.DPoint(x_min + w, y_max - w),
            pya.DPoint(x_max - w, y_max - w),
            pya.DPoint(x_max - w, y_min + w),
            pya.DPoint(x_min + w, y_min + w),
        ]
        return points

    def _produce_lines_along_edge(self, line_start, line_end, is_vertical, position):
        """Adds chip dicing reference lines along one edge of the chip.
        The line pattern is tied to the global coordinate system

        Args:
            line_start: One-dimensional coordinate of start of the line
            line_end: One-dimensional coordinate of end of the line
            is_vertical: True to draw a line along y-axis, False to draw along x-axis
            position: A DPoint that is in the line
        """
        start = line_start
        segment_length = self.chip_dicing_line_length + self.chip_dicing_gap_length
        end = math.floor(line_start / segment_length) * segment_length + self.chip_dicing_line_length
        if end > start:
            self._add_chip_dicing_line_dash(start, end, is_vertical, position)
        while True:
            start = end + self.chip_dicing_gap_length
            if start > line_end:
                break
            end = start + self.chip_dicing_line_length
            if end > line_end:
                self._add_chip_dicing_line_dash(start, line_end, is_vertical, position)
                break
            self._add_chip_dicing_line_dash(start, end, is_vertical, position)

    def _add_chip_dicing_line_dash(self, start, end, is_vertical, position):
        """Adds a dash as part of a chip dicing reference line.

        Args:
            start: One-dimensional coordinate of start of the dash
            end: One-dimensional coordinate of end of the dash
            is_vertical: True to draw a dash along y-axis, False to draw along x-axis
            position: A DPoint that is in the line to which the dash belongs to
        """
        if is_vertical:
            box = pya.DBox(position.x - self.chip_dicing_width/2, start, position.x + self.chip_dicing_width/2, end)
        else:
            box = pya.DBox(start, position.y - self.chip_dicing_width/2, end, position.y + self.chip_dicing_width/2)
        self.cell.shapes(self.get_layer("chip_dicing")).insert(box)
