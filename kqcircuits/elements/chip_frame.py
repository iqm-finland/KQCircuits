# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from autologging import traced

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.element import Element
from kqcircuits.elements.marker import Marker
from kqcircuits.defaults import default_brand


@traced
def produce_label(cell, label, location, origin, dice_width, margin, layer_optical, layer_protection):
    """ Produces a Text PCell accounting for desired relative position of the text respect to the given location
    and the spacing.

    Args:
        cell: container cell for the label PCell
        label: text of the label
        location: DPoint for the location of the text
        origin: name of the corner of the text located at the location, bottomleft | topleft | topright | bottomright
        dice_width: extra spacing from the location
        margin: margin of the ground grid avoidance layer around the text
        layer_optical: layer name for the label
        layer_protection: layer name for the ground gird avoidance layer

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
    subcell = layout.create_cell("TEXT", "Basic", {
        "layer": layer_optical,
        "text": label,
        "mag": 500.0
    })

    # relative placement with margin
    margin = margin / dbu
    dice_width = dice_width / dbu

    trans = pya.DTrans(location + {
        "bottomleft": pya.Vector(
            subcell.bbox().p1.x - margin - dice_width,
            subcell.bbox().p1.y - margin - dice_width),
        "topleft": pya.Vector(
            subcell.bbox().p1.x - margin - dice_width,
            subcell.bbox().p2.y + margin + dice_width),
        "topright": pya.Vector(
            subcell.bbox().p2.x + margin + dice_width,
            subcell.bbox().p2.y + margin + dice_width),
        "bottomright": pya.Vector(
            subcell.bbox().p2.x + margin + dice_width,
            subcell.bbox().p1.y - margin - dice_width),
    }[origin] * dbu * (-1))

    if not protection_only:
        cell.insert(pya.DCellInstArray(subcell.cell_index(), trans))

    # protection layer with margin
    protection = pya.DBox(pya.Point(
        subcell.bbox().p1.x - margin,
        subcell.bbox().p1.y - margin) * dbu,
                          pya.Point(
                              subcell.bbox().p2.x + margin,
                              subcell.bbox().p2.y + margin) * dbu
                          )
    cell.shapes(layout.layer(layer_protection)).insert(
        trans.trans(protection))


class ChipFrame(Element):
    """
    The PCell declaration for a chip frame.

    The chip frame consists of a dicing edge, and labels and markers in the corners.

    Attributes:
        box: bounding box of the chip frame (pya.Box)
        with_grid: make ground grid or not (Boolean)
        dice_width: dicing edge width
        dice_grid_margin: margin of the ground grid avoidance layer for dicing edge
        name_mask: name of the mask
        name_chip: name of the chip
        name_copy: name of the copy
        text_margin: margin of the ground grid avoidance layer around the text
        marker_dist: distance of markers from closest edges of the chip face
        marker_diagonals: number of diagonal squares for the markers
    """

    PARAMETERS_SCHEMA = {
        "box": {
            "type": pya.PCellParameterDeclaration.TypeShape,
            "description": "Border",
            "default": pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000))
        },
        "with_grid": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Make ground plane grid",
            "default": False
        },
        "dice_width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Dicing width (um)",
            "default": 200
        },
        "dice_grid_margin": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Margin between dicing edge and ground grid",
            "default": 100,
        },
        "name_mask": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Name of the mask",
            "default": "M99"
        },
        "name_chip": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Name of the chip",
            "default": "CTest"
        },
        "name_copy": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Name of the copy"
        },
        "text_margin": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Margin for labels",
            "default": 100,
        },
        "marker_dist": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Marker distance from edges",
            "default": 1500,
        },
        "marker_diagonals": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Number of diagonal squares for the markers",
            "default": 10
        },
        "use_face_prefix": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Use face prefix for chip name label",
            "default": False
        },
    }

    def __init__(self):
        super().__init__()

    def produce_impl(self):
        """Produces dicing edge, markers, labels and ground grid for the chip face.
        """
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
        if True:
            self._produce_label(labels[2], pya.DPoint(x_max, y_min), "bottomright")
        if True:
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
        produce_label(self.cell, label, location, origin, self.dice_width, self.text_margin, self.face()["base metal gap wo grid"],
                      self.face()["ground grid avoidance"])

    def _produce_markers(self):
        x_min, x_max, y_min, y_max = self._box_points()
        self._produce_marker_sqr(pya.DTrans(x_min + self.marker_dist, y_min + self.marker_dist) * pya.DTrans.R180,
                                 self.face()["id"] + "_marker_sw")
        self._produce_marker_sqr(pya.DTrans(x_max - self.marker_dist, y_min + self.marker_dist) * pya.DTrans.R270,
                                 self.face()["id"] + "_marker_se")
        self._produce_marker_sqr(pya.DTrans(x_min + self.marker_dist, y_max - self.marker_dist) * pya.DTrans.R90,
                                 self.face()["id"] + "_marker_nw")
        self._produce_marker_sqr(pya.DTrans(x_max - self.marker_dist, y_max - self.marker_dist) * pya.DTrans.R0,
                                 self.face()["id"] + "_marker_ne")

    def _produce_marker_sqr(self, trans, name):
        parameters = {
            **self.cell.pcell_parameters_by_name(),
            **{"window": False, "diagonal_squares": self.marker_diagonals,
               "face_ids": self.face_ids}
        }
        cell_marker = Marker.create_cell(self.layout, parameters)
        self.insert_cell(cell_marker, trans)
        self.refpoints[name] = trans.disp

    def _produce_dicing_edge(self):
        shape = pya.DPolygon(self._border_points(self.dice_width))
        self.cell.shapes(self.layout.layer(self.face()["base metal gap wo grid"])).insert(shape)

        protection = pya.DPolygon(self._border_points(self.dice_width + self.dice_grid_margin))
        self.cell.shapes(self.layout.layer(self.face()["ground grid avoidance"])).insert(protection)

    def _box_points(self):
        """Returns x_min, x_max, y_min, y_max for the given box"""
        x_min = min(self.box.p1.x, self.box.p2.x)
        x_max = max(self.box.p1.x, self.box.p2.x)
        y_min = min(self.box.p1.y, self.box.p2.y)
        y_max = max(self.box.p1.y, self.box.p2.y)
        return x_min, x_max, y_min, y_max

    def _border_points(self, w):
        """returns a set of points forming frame with outer edge on the chip boundaries, and frame thickness `w`"""
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
