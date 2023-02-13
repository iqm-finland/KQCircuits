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
from autologging import logged
from tqdm import tqdm

from kqcircuits.pya_resolver import pya
from kqcircuits.defaults import default_layers, default_brand, default_faces, default_mask_parameters, \
    default_layers_to_mask, default_covered_region_excluded_layers, default_mask_export_layers, default_bar_format
from kqcircuits.elements.markers.marker import Marker
from kqcircuits.elements.mask_marker_fc import MaskMarkerFc
from kqcircuits.util.label import produce_label, LabelOrigin
from kqcircuits.util.merge import merge_layout_layers_on_face, convert_child_instances_to_static


@logged
class MaskLayout:
    """Class representing the mask for a certain face.

    A MaskLayout is used to create the cells for the mask.

    Attributes:
        layout: pya.Layout for this mask
        name: Name of the mask
        version: Mask version
        with_grid: Boolean determining if ground grid is generated
        face_id: face_id of this mask layout, "1t1" | "2b1" | "2t1"
        layers_to_mask: dictionary of layers with mask label postfix for mask label and mask covered region creation
        covered_region_excluded_layers: list of layers in `layers_to_mask` for which mask covered region is not created
        chips_map: List of lists (2D-array) of strings, each string is a chip name (or --- for no chip)
        chips_map_legend: Dictionary where keys are chip names, values are chip cells
        wafer_rad: Wafer radius
        wafer_center: Wafer center as a pya.DVector
        chips_map_offset: Offset to make chips_map centered on wafer
        wafer_top_flat_length: length of flat edge at the top of the wafer
        wafer_bottom_flat_length: length of flat edge at the bottom of the wafer
        dice_width: Dicing width for this mask layout
        text_margin: Text margin for this mask layout
        chip_size: side width of the chips (assuming square chips)
        edge_clearance: minimum clearance of outer chips from the edge of the mask, measured from the chip center
        chip_box_offset: Offset (pya.DVector) from chip origin of the chip frame boxes for this face
        chip_trans: DTrans applied to all chips
        mask_name_offset: mask name label offset from default position (DPoint)
        mask_name_scale: text scaling factor for mask name label (float)
        mask_text_scale: text scaling factor for graphical representation layer (float)
        mask_marker_offset: offset of mask markers from wafer center in horizontal and vertical directions (float)
        mask_export_layers: list of layer names (without face_ids) to be exported as individual mask `.oas` files
        submasks: list of submasks, each element is a tuple (submask mask_layout, submask position)
        extra_id: extra string used to create unique name for mask layouts with the same face_id
        extra_chips: List of tuples (name, position, trans) for chips placed outside chips_map, trans is an optional
            transformation to use in place of self.chip_trans
        top_cell: Top cell of this mask layout
        added_chips: List of (chip name, chip position, chip bounding box, chip dtrans) populated by chips added during
            build()
    """

    def __init__(self, layout, name, version, with_grid, chips_map, face_id, **kwargs):

        self.layout: pya.Layout = layout
        self.name = name
        self.version = version
        self.with_grid = with_grid
        self.face_id = face_id
        self.chips_map = chips_map
        self.chips_map_legend = None

        self.layers_to_mask = kwargs.get("layers_to_mask", default_layers_to_mask)
        self.covered_region_excluded_layers = kwargs.get("covered_region_excluded_layers",
                                                        default_covered_region_excluded_layers) + ["mask_edge"]
        self.wafer_rad = kwargs.get("wafer_rad", default_mask_parameters[self.face_id]["wafer_rad"])
        self.wafer_center = (pya.DVector(0, 0))
        self.chips_map_offset = kwargs.get("chips_map_offset",
                                              default_mask_parameters[self.face_id]["chips_map_offset"])
        self.wafer_top_flat_length = kwargs.get("wafer_top_flat_length", 0)
        self.wafer_bottom_flat_length = kwargs.get("wafer_bottom_flat_length", 0)
        self.dice_width = kwargs.get("dice_width", default_mask_parameters[self.face_id]["dice_width"])
        self.text_margin = kwargs.get("text_margin", default_mask_parameters[self.face_id]["text_margin"])
        self.chip_size = kwargs.get("chip_size", default_mask_parameters[self.face_id]["chip_size"])
        self.edge_clearance = kwargs.get("edge_clearance", self.chip_size)
        self.chip_box_offset = kwargs.get("chip_box_offset", default_mask_parameters[self.face_id]["chip_box_offset"])
        self.chip_trans = kwargs.get("chip_trans", default_mask_parameters[self.face_id]["chip_trans"])
        self.mask_name_offset = kwargs.get("mask_name_offset", default_mask_parameters[self.face_id][
            "mask_name_offset"])
        self.mask_name_scale = kwargs.get("mask_name_scale", 1)
        self.mask_text_scale = kwargs.get("mask_text_scale", default_mask_parameters[self.face_id]["mask_text_scale"])
        self.mask_markers_type = kwargs.get("mask_markers_type", "all")
        self.mask_marker_offset = kwargs.get("mask_marker_offset", default_mask_parameters[self.face_id][
            "mask_marker_offset"])
        self.mask_export_layers = kwargs.get("mask_export_layers", default_mask_export_layers)
        self.submasks = kwargs.get("submasks", [])
        self.extra_id = kwargs.get("extra_id", "")
        self.extra_chips = kwargs.get("extra_chips", [])

        self.top_cell = self.layout.create_cell(f"{self.name} {self.face_id}")
        self.added_chips = []

    def build(self, chips_map_legend):
        """Builds the cell hierarchy for this mask layout.

        Inserts cells copied from chips_map_legend to self.top_cell at positions determined by self.chips_map. The
        copied cells are modified to only have layers corresponding to self.face_id, and they are translated and/or
        mirrored correctly based on self.face_id. Also inserts cells for mask markers, mask name label, and the circular
        area covered by the mask.

        Args:
            chips_map_legend: Dictionary where keys are chip names, values are chip cells

        """
        self.chips_map_legend = {}

        for name, cell in tqdm(chips_map_legend.items(), desc='Building cell hierarchy', bar_format=default_bar_format):

            # pylint: disable=use-a-generator
            if any([name in row for row in self.chips_map] + [chip[0] == name for chip in self.extra_chips]):

                # create copies of the chips, so that modifying these only affects the ones in this MaskLayout
                new_cell = self.layout.create_cell(name)
                new_cell.copy_tree(cell)
                # remove layers belonging to another face
                for face_id, face_dictionary in default_faces.items():
                    if face_id != self.face_id:
                        for layer_info in face_dictionary.values():
                            shapes_iter = new_cell.begin_shapes_rec(self.layout.layer(layer_info))

                            # iterating shapes using shapes_iter.at_end() fails:
                            # https://www.klayout.de/forum/discussion/comment/4275
                            # solution is to use a separate buffer list to iterate
                            shapes = []
                            while not shapes_iter.at_end():
                                try:
                                    shapes.append(shapes_iter.shape())
                                    shapes_iter.next()
                                except ValueError:
                                    print("error occurs at %s at %s" % (name, face_id))

                            for shapes_to_remove in shapes:
                                shapes_to_remove.delete()

                self.chips_map_legend[name] = new_cell

        step_ver = pya.DVector(0, -self.chip_size)
        step_hor = pya.DVector(self.chip_size, 0)

        region_covered = self._mask_create_geometry()
        if len(self.submasks) > 0:
            region_covered = pya.Region()  # don't fill with metal gap layer if using submasks
            for submask_layout, submask_pos in self.submasks:
                self.top_cell.insert(
                    pya.DCellInstArray(submask_layout.top_cell.cell_index(),
                                       pya.DTrans(submask_pos - submask_layout.wafer_center + self.wafer_center))
                )

        # add chips from chips_map
        for (i, row) in enumerate(tqdm(self.chips_map, desc='Adding chips to mask', bar_format=default_bar_format)):
            for (j, chip_name) in enumerate(row):
                position = pya.DPoint(step_ver * (i + 1) + step_hor * j) - self.chips_map_offset \
                           + pya.DVector(-self.wafer_rad, self.wafer_rad)
                if (position - step_ver*0.5 + step_hor*0.5 - self.wafer_center).abs() - self.wafer_rad < \
                        -self.edge_clearance:
                    added_chip, region_chip = self._add_chip(chip_name, position, self.chip_trans)
                else:
                    added_chip, region_chip = False, pya.Region()
                region_covered -= region_chip
                if not added_chip:
                    self.chips_map[i][j] = "---"

        # add chips outside chips_map
        for name, pos, *trans in self.extra_chips:  # trans is optional
            if name in chips_map_legend:
                region_covered -= self._add_chip(name, pos, trans[0] if trans else self.chip_trans)[1]
                self.chips_map.append([name])  # to get correct amount of chips in mask documentation

        maskextra_cell: pya.Cell = self.layout.create_cell("MaskExtra")

        self._insert_mask_name_label(self.top_cell, default_layers["mask_graphical_rep"])
        self._mask_create_covered_region(maskextra_cell, region_covered, self.layers_to_mask)
        convert_child_instances_to_static(self.layout, maskextra_cell, only_elements=True, prune=True)
        merge_layout_layers_on_face(self.layout, maskextra_cell, self.face())

    def insert_chip_copy_labels(self, labels_cell, layers):
        """Inserts chip copy labels to all chips in this mask layout and its submasks

        Args:
            labels_cell: Cell to which the labels are inserted
            layers: list of layer names (without face_ids) where the labels are produced
        """

        # find labels_cell for this mask and each submask
        labels_cells = {self: labels_cell}
        for submask_layout, submask_pos in self.submasks:
            for inst in submask_layout.top_cell.each_inst():
                # workaround for getting the cell due to KLayout bug, see
                # https://www.klayout.de/forum/discussion/1191
                # TODO: replace by `inst_cell = inst.cell` once KLayout bug is fixed
                inst_cell = submask_layout.layout.cell(inst.cell_index)
                if inst_cell.name.startswith("ChipLabels"):
                    labels_cells[submask_layout] = inst_cell
                    break

        # find all unique x and y coords of chips and place them in the corresponding keys in chips_dict
        chips_dict = {}  # {(pos_x, pos_y): chip_name, chip_pos (in submask coordinates), chip_inst, mask_layout}
        xvals = set()
        yvals = set()
        for chip_name, pos, bbox, dtrans in self.added_chips:
            xvals.add(pos.x)
            yvals.add(pos.y)
            chips_dict[(pos.x, pos.y)] = chip_name, pos, bbox, dtrans, self
        for submask_layout, submask_pos in self.submasks:
            for chip_name, pos, bbox, dtrans in submask_layout.added_chips:
                pos2 = pos + submask_pos
                xvals.add(pos2.x)
                yvals.add(pos2.y)
                chips_dict[(pos2.x, pos2.y)] = chip_name, pos, bbox, dtrans, submask_layout

        # produce the labels such that chips with identical x-coordinate (y-coordinate) have identical number (letter)
        for i, y in enumerate(sorted(yvals, reverse=True)):
            for j, x in enumerate(sorted(xvals)):
                if (x, y) in chips_dict:
                    chip_name, _, bbox, dtrans, mask_layout = chips_dict[(x, y)]
                    labels_cell_2 = labels_cells[mask_layout]
                    pos_index_name = chr(ord("A") + i) + ("{:02d}".format(j))
                    bbox_x1 = bbox.left if dtrans.is_mirror() else bbox.right
                    produce_label(labels_cell_2, pos_index_name, dtrans*(pya.DPoint(bbox_x1, bbox.bottom)),
                                  LabelOrigin.BOTTOMRIGHT, mask_layout.dice_width, mask_layout.text_margin,
                                  [mask_layout.face()[layer] for layer in layers],
                                  mask_layout.face()["ground_grid_avoidance"])
                    bbox_x2 = bbox.right if dtrans.is_mirror() else bbox.left
                    mask_layout._add_chip_graphical_representation_layer(chip_name,
                                                                         dtrans*(pya.DPoint(bbox_x2, bbox.bottom)),
                                                                         pos_index_name, bbox.width(), labels_cell_2)

    def face(self):
        """Returns the face dictionary for this mask layout"""
        return default_faces[self.face_id]

    def _mask_create_geometry(self):
        y_clip = -14.5e4

        points = []
        for a in range(0, 256 + 1):
            x = math.cos(a / 128 * math.pi) * self.wafer_rad
            y = max(math.sin(a / 128 * math.pi) * self.wafer_rad, y_clip)
            if (y > 0 and (x > self.wafer_top_flat_length/2 or x < -self.wafer_top_flat_length/2)) or \
               (y < 0 and (x > self.wafer_bottom_flat_length/2 or x < -self.wafer_bottom_flat_length/2)):
                points.append(pya.DPoint(self.wafer_center.x + x, self.wafer_center.y + y))

        region_covered = pya.Region(pya.DPolygon(points).to_itype(self.layout.dbu))
        return region_covered

    def _add_chip(self, name, position, trans):
        """Returns a tuple (Boolean telling if the chip was added, Region which the chip covers)."""
        chip_region = pya.Region()
        if name in self.chips_map_legend.keys():
            chip_cell, bounding_box, bbox_offset = self._get_chip_cell_and_bbox(name)
            trans = pya.DTrans(position + pya.DVector(bbox_offset, 0) - self.chip_box_offset)*trans
            self.top_cell.insert(pya.DCellInstArray(chip_cell.cell_index(), trans))
            chip_region = pya.Region(pya.Box(trans*bounding_box*(1/self.layout.dbu)))
            self.added_chips.append((name, position, bounding_box, trans))
            return True, chip_region
        return False, chip_region

    def _mask_create_covered_region(self, maskextra_cell, region_covered, layers_dict):
        dbu = self.layout.dbu

        leftmost_label_x = 1e10
        labels = []
        for layer, postfix in layers_dict.items():
            label_cell, label_trans = self._create_mask_name_label(self.face()[layer], postfix)
            if label_trans.disp.x < leftmost_label_x:
                leftmost_label_x = label_trans.disp.x
            labels.append((label_cell, label_trans))
        # align left edges of mask name labels in different layers
        for (label_cell, label_trans) in labels:
            label_trans = pya.DTrans(label_trans.rot, label_trans.is_mirror(), leftmost_label_x, label_trans.disp.y)
            inst = maskextra_cell.insert(pya.DCellInstArray(label_cell.cell_index(), label_trans))
            region_covered -= pya.Region(inst.bbox()).extents(1e3 / dbu)

        circle = pya.DTrans(self.wafer_center) * pya.DPath(
            [pya.DPoint(math.cos(a / 32 * math.pi) * self.wafer_rad, math.sin(a / 32 * math.pi) * self.wafer_rad)
             for a in range(0, 64 + 1)], 100)
        maskextra_cell.shapes(self.layout.layer(default_layers["mask_graphical_rep"])).insert(circle)

        offset = self.mask_marker_offset
        # Corner mask markers
        if self.mask_markers_type in ["all", "only_corners"]:
            cell_marker = Marker.create(self.layout, window=True, face_ids=[self.face_id])
            marker_transes = [pya.DTrans(self.wafer_center.x - offset, self.wafer_center.y - offset) * pya.DTrans.R180,
                              pya.DTrans(self.wafer_center.x + offset, self.wafer_center.y - offset) * pya.DTrans.R270,
                              pya.DTrans(self.wafer_center.x - offset, self.wafer_center.y + offset) * pya.DTrans.R90,
                              pya.DTrans(self.wafer_center.x + offset, self.wafer_center.y + offset) * pya.DTrans.R0]
            self._add_markers(maskextra_cell, region_covered, cell_marker, marker_transes)
        # Side mask markers
        if self.mask_markers_type in ["all", "only_sides"]:
            cell_marker = MaskMarkerFc.create(self.layout,  window=True, face_ids=[self.face_id])
            marker_transes = [
                              pya.DTrans(self.wafer_center.x - offset * 1.9**0.5, self.wafer_center.y) * pya.DTrans.M90,
                              pya.DTrans(self.wafer_center.x + offset * 1.9**0.5, self.wafer_center.y) * pya.DTrans.R0]
            self._add_markers(maskextra_cell, region_covered, cell_marker, marker_transes)

        maskextra_cell.shapes(self.layout.layer(default_layers["mask_graphical_rep"])).insert(region_covered)
        # remove unwanted circle boundary and filling from `layers_to_mask` which have been excluded in
        # `covered_region_excluded_layers`
        for layer_name in layers_dict.keys():
            if layer_name not in self.covered_region_excluded_layers:
                maskextra_cell.shapes(self.layout.layer(self.face()[layer_name])).insert(region_covered)

        self.top_cell.insert(pya.DCellInstArray(maskextra_cell.cell_index(), pya.DTrans()))

    def _add_markers(self, maskextra_cell, region_covered, cell_marker, marker_transes):
        for trans in marker_transes:
            inst = maskextra_cell.insert(pya.DCellInstArray(cell_marker.cell_index(), trans))
            region_covered -= pya.Region(inst.bbox()).extents(1e3/self.layout.dbu)

    def _get_chip_name(self, search_cell):
        for chip_name, cell in self.chips_map_legend.items():
            if search_cell == cell:
                return chip_name
        return ""

    def _get_chip_cell_and_bbox(self, chip_name):
        chip_cell = self.chips_map_legend[chip_name]
        bounding_box = chip_cell.dbbox_per_layer(self.layout.layer(self.face()["base_metal_gap_wo_grid"]))
        bbox_offset = self.chip_size - bounding_box.width()  # for chips that are smaller than self.chip_size
        return chip_cell, bounding_box, bbox_offset

    def _add_chip_graphical_representation_layer(self, chip_name, position, pos_index_name, chip_size, cell):
        chip_name_text = self.layout.create_cell("TEXT", "Basic", {
            "layer": default_layers["mask_graphical_rep"],
            "text": chip_name,
            "mag": 15000 * self.mask_text_scale / len(chip_name),
        })
        pos_index_name_text = self.layout.create_cell("TEXT", "Basic", {
            "layer": default_layers["mask_graphical_rep"],
            "text": pos_index_name,
            "mag": 4000 * self.mask_text_scale,
        })
        chip_name_trans = pya.DTrans(position + pya.DVector((chip_size - chip_name_text.dbbox().width()) / 2,
                                                            self.mask_text_scale * 750))
        cell.insert(pya.DCellInstArray(chip_name_text.cell_index(), chip_name_trans))
        pos_index_trans = pya.DTrans(position + pya.DVector((chip_size - pos_index_name_text.dbbox().width()) / 2,
                                                            self.mask_text_scale * 6000))
        cell.insert(pya.DCellInstArray(pos_index_name_text.cell_index(), pos_index_trans))

    def _insert_mask_name_label(self, cell, layer, postfix=""):
        cell_mask_name, trans = self._create_mask_name_label(layer, postfix)
        inst = cell.insert(pya.DCellInstArray(cell_mask_name.cell_index(), trans))
        return inst

    def _create_mask_name_label(self, layer, postfix=""):
        if postfix != "":
            postfix = "-" + postfix
        cell_mask_name = self.layout.create_cell("TEXT", "Basic", {
            "layer": layer,
            "text": default_brand + "-" + self.name + "v" + str(self.version) + postfix,
            "mag": self.mask_name_scale*5000.0,
        })
        cell_mask_name_h = cell_mask_name.dbbox().height()
        cell_mask_name_w = cell_mask_name.dbbox().width()
        trans = pya.DTrans(self.wafer_center.x + self.mask_name_offset.x - cell_mask_name_w / 2,
                           self.wafer_rad + self.mask_name_offset.y - cell_mask_name_h / 2)

        return cell_mask_name, trans
