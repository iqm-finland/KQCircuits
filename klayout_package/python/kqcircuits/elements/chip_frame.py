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


from autologging import traced

from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.elements.element import Element
from kqcircuits.elements.markers.marker import Marker
from kqcircuits.defaults import default_brand, default_marker_type


@traced
def produce_label(cell, label, location, origin, dice_width, margin, layers, layer_protection):
    """Produces a Text PCell accounting for desired relative position of the text respect to the given location
    and the spacing.

    Args:
        cell: container cell for the label PCell
        label: text of the label
        location: DPoint for the location of the text
        origin: name of the corner of the text located at the location, bottomleft | topleft | topright | bottomright
        dice_width: extra spacing from the location
        margin: margin of the ground grid avoidance layer around the text
        layers: list of layers where the label text is added
        layer_protection: layer where a box around the label text is added

    Effect:
        Shapes added to the corresponding layers
    """

    layout = cell.layout()
    dbu = layout.dbu

    if not label:
        label = "A13"  # longest label on 6 inch wafer
        protection_only = True
    else:
        protection_only = False

    # text cell
    subcells = []
    for layer in layers:
        subcells.append(layout.create_cell("TEXT", "Basic", {
            "layer": layer,
            "text": label,
            "mag": 500.0
        }))

    # relative placement with margin
    margin = margin / dbu
    dice_width = dice_width / dbu

    trans = pya.DTrans(location + {
        "bottomleft": pya.Vector(
            subcells[0].bbox().p1.x - margin - dice_width,
            subcells[0].bbox().p1.y - margin - dice_width),
        "topleft": pya.Vector(
            subcells[0].bbox().p1.x - margin - dice_width,
            subcells[0].bbox().p2.y + margin + dice_width),
        "topright": pya.Vector(
            subcells[0].bbox().p2.x + margin + dice_width,
            subcells[0].bbox().p2.y + margin + dice_width),
        "bottomright": pya.Vector(
            subcells[0].bbox().p2.x + margin + dice_width,
            subcells[0].bbox().p1.y - margin - dice_width),
    }[origin] * dbu * (-1))

    if not protection_only:
        for subcell in subcells:
            cell.insert(pya.DCellInstArray(subcell.cell_index(), trans))

    # protection layer with margin
    protection = pya.DBox(pya.Point(
        subcells[0].bbox().p1.x - margin,
        subcells[0].bbox().p1.y - margin) * dbu,
                          pya.Point(
                              subcells[0].bbox().p2.x + margin,
                              subcells[0].bbox().p2.y + margin) * dbu
                          )
    cell.shapes(layout.layer(layer_protection)).insert(
        trans.trans(protection))


class ChipFrame(Element):
    """The PCell declaration for a chip frame.

    The chip frame consists of a dicing edge, and labels and markers in the corners.
    """

    box = Param(pdt.TypeShape, "Border", pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000)),
        docstring="Bounding box of the chip frame")
    with_grid = Param(pdt.TypeBoolean, "Make ground plane grid", False)
    dice_width = Param(pdt.TypeDouble, "Dicing width", 200, unit="μm")
    dice_grid_margin = Param(pdt.TypeDouble, "Margin between dicing edge and ground grid", 100,
        docstring="Margin of the ground grid avoidance layer for dicing edge")
    name_mask = Param(pdt.TypeString, "Name of the mask", "M99")
    name_chip = Param(pdt.TypeString, "Name of the chip", "CTest")
    name_copy = Param(pdt.TypeString, "Name of the copy", None)
    text_margin = Param(pdt.TypeDouble, "Margin for labels", 100,
        docstring="Margin of the ground grid avoidance layer around the text")
    marker_dist = Param(pdt.TypeDouble, "Marker distance from edges", 1500,
        docstring="Distance of markers from closest edges of the chip face")
    marker_diagonals = Param(pdt.TypeInt, "Number of diagonal squares for the markers", 10)
    use_face_prefix = Param(pdt.TypeBoolean, "Use face prefix for chip name label", False)
    marker_type = Param(pdt.TypeList, "Market type for each chip corner, starting from lower left and going clockwise",
                       default=[default_marker_type]*4)

    def produce_impl(self):
        """Produces dicing edge, markers, labels and ground grid for the chip face."""
        self._produce_dicing_edge()
        self._produce_labels()
        self._produce_markers()
        super().produce_impl()

    def _produce_labels(self):
        x_min, x_max, y_min, y_max = self._box_points()
        chip_name = self.face()["id"].upper() + self.name_chip if self.use_face_prefix else self.name_chip
        labels = [self.name_mask, chip_name, self.name_copy, default_brand]
        if self.name_mask:
            self._produce_label(labels[0], pya.DPoint(x_min, y_max), "topleft")
        if self.name_chip:
            self._produce_label(labels[1], pya.DPoint(x_max, y_max), "topright")
        self._produce_label(labels[2], pya.DPoint(x_max, y_min), "bottomright")
        self._produce_label(labels[3], pya.DPoint(x_min, y_min), "bottomleft")

    def _produce_label(self, label, location, origin):
        """Produces Text PCells with text `label` with `origin` of the text at `location`.

        Wrapper for the stand alone function `produce_label`

        Args:
            label: the produced text
            location: DPoint of the location of the text
            origin: the name of the corner of the label to be placed at the location

        Effect:
            label PCells added to the layout into the parent PCell
        """
        produce_label(self.cell, label, location, origin, self.dice_width, self.text_margin,
                      [self.face()["base_metal_gap_wo_grid"], self.face()["base_metal_gap_for_EBL"]],
                      self.face()["ground_grid_avoidance"])

    def _produce_markers(self):
        x_min, x_max, y_min, y_max = self._box_points()
        self._produce_marker(self.marker_type[0], pya.DTrans(x_min + self.marker_dist, y_min + self.marker_dist) \
                             * pya.DTrans.R180, self.face()["id"] + "_marker_sw")
        self._produce_marker(self.marker_type[3], pya.DTrans(x_max - self.marker_dist, y_min + self.marker_dist) \
                             * pya.DTrans.R270, self.face()["id"] + "_marker_se")
        self._produce_marker(self.marker_type[1], pya.DTrans(x_min + self.marker_dist, y_max - self.marker_dist) \
                             * pya.DTrans.R90, self.face()["id"] + "_marker_nw")
        self._produce_marker(self.marker_type[2], pya.DTrans(x_max - self.marker_dist, y_max - self.marker_dist) \
                             * pya.DTrans.R0, self.face()["id"] + "_marker_ne")

    def _produce_marker(self, marker_type, trans, name):
        parameters = {
            **self.cell.pcell_parameters_by_name(),
            **{"marker_type": marker_type, "window": False, "diagonal_squares": self.marker_diagonals,
               "face_ids": self.face_ids}
        }
        cell_marker = self.add_element(Marker, **parameters)
        self.insert_cell(cell_marker, trans)
        self.refpoints[name] = trans.disp

    def _produce_dicing_edge(self):
        shape = pya.DPolygon(self._border_points(self.dice_width))
        self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(shape)
        self.cell.shapes(self.get_layer("base_metal_gap_for_EBL")).insert(shape)

        protection = pya.DPolygon(self._border_points(self.dice_width + self.dice_grid_margin))
        self.cell.shapes(self.get_layer("ground_grid_avoidance")).insert(protection)

    def _box_points(self):
        """Returns x_min, x_max, y_min, y_max for the given box."""
        x_min = min(self.box.p1.x, self.box.p2.x)
        x_max = max(self.box.p1.x, self.box.p2.x)
        y_min = min(self.box.p1.y, self.box.p2.y)
        y_max = max(self.box.p1.y, self.box.p2.y)
        return x_min, x_max, y_min, y_max

    def _border_points(self, w):
        """Returns a set of points forming frame with outer edge on the chip boundaries, and frame thickness `w`."""
        x_min, x_max, y_min, y_max = self._box_points()
        points = [
            pya.DPoint(x_min, y_min),
            pya.DPoint(x_max, y_min),
            pya.DPoint(x_max, y_max),
            pya.DPoint(x_min, y_max),
            pya.DPoint(x_min, y_min),

            pya.DPoint(x_min + w, y_min + w),
            pya.DPoint(x_min + w, y_max - w),
            pya.DPoint(x_max - w, y_max - w),
            pya.DPoint(x_max - w, y_min + w),
            pya.DPoint(x_min + w, y_min + w),
        ]
        return points
