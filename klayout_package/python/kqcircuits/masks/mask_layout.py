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
from autologging import logged, traced
from tqdm import tqdm

from kqcircuits.pya_resolver import pya
from kqcircuits.defaults import default_layers, default_brand, default_faces, default_mask_parameters, \
    default_layers_to_mask, default_covered_region_excluded_layers, default_mask_export_layers, default_bar_format
from kqcircuits.util import merge
from kqcircuits.elements.markers.marker import Marker
from kqcircuits.elements.mask_marker_fc import MaskMarkerFc
from kqcircuits.elements.chip_frame import produce_label


@traced
@logged
class MaskLayout:
    """Class representing the mask for a certain face.

    A MaskLayout is used to create the cells for the mask.

    Attributes:
        layout: pya.Layout for this mask
        name: Name of the mask
        version: Mask version
        with_grid: Boolean determining if ground grid is generated
        face_id: face_id of this mask layout, "b" | "t" | "c"
        layers_to_mask: dictionary of layers with mask label postfix for mask label and mask covered region creation
        covered_region_excluded_layers: list of layers in `layers_to_mask` for which mask covered region is not created
        chips_map: List of lists (2D-array) of strings, each string is a chip name (or --- for no chip)
        chips_map_legend: Dictionary where keys are chip names, values are chip cells
        wafer_rad: Wafer radius
        wafer_center: Wafer center as a pya.DVector
        wafer_top_flat_length: length of flat edge at the top of the wafer
        wafer_bottom_flat_length: length of flat edge at the bottom of the wafer
        dice_width: Dicing width for this mask layout
        text_margin: Text margin for this mask layout
        chip_size: side width of the chips (assuming square chips)
        chip_box_offset: Offset (pya.DVector) from chip origin of the chip frame boxes for this face
        chip_trans: DTrans applied to all chips
        mask_name_offset: mask name label offset from default position in vertical direction (float)
        mask_name_scale: text scaling factor for mask name label (float)
        mask_text_scale: text scaling factor for graphical representation layer (float)
        mask_marker_offset: offset of mask markers from wafer center in horizontal and vertical directions (float)
        mask_export_layers: list of layer names (without face_ids) to be exported as individual mask `.oas` files
        submasks: list of submasks, each element is a tuple (submask mask_layout, submask position)
        extra_id: extra string used to create unique name for mask layouts with the same face_id
        top_cell: Top cell of this mask layout
    """

    def __init__(self, layout, name, version, with_grid, chips_map, face_id, **kwargs):

        self.layout = layout
        self.name = name
        self.version = version
        self.with_grid = with_grid
        self.face_id = face_id
        self.chips_map = chips_map
        self.chips_map_legend = None

        self.layers_to_mask = kwargs.get("layers_to_mask", default_layers_to_mask)
        self.covered_region_excluded_layers = kwargs.get("covered_region_excluded_layers",
                                                        default_covered_region_excluded_layers)
        self.wafer_rad = kwargs.get("wafer_rad", default_mask_parameters[self.face_id]["wafer_rad"])
        self.wafer_center = (pya.DVector(self.wafer_rad, -self.wafer_rad) +
                             kwargs.get("wafer_center_offset",
                                        default_mask_parameters[self.face_id]["wafer_center_offset"]))
        self.wafer_top_flat_length = kwargs.get("wafer_top_flat_length", 0)
        self.wafer_bottom_flat_length = kwargs.get("wafer_bottom_flat_length", 0)
        self.dice_width = kwargs.get("dice_width", default_mask_parameters[self.face_id]["dice_width"])
        self.text_margin = kwargs.get("text_margin", default_mask_parameters[self.face_id]["text_margin"])
        self.chip_size = kwargs.get("chip_size", default_mask_parameters[self.face_id]["chip_size"])
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

        self.top_cell = self.layout.create_cell(f"{self.name} {self.face_id}{self.extra_id}")

    def build(self, chips_map_legend):
        """Builds the cell hierarchy for this mask layout.

        Inserts cells copied from chips_map_legend to self.top_cell at positions determined by self.chips_map. The
        copied cells are modified to only have layers corresponding to self.face_id, and they are translated and/or
        mirrored correctly based on self.face_id. Also inserts cells for mask markers, mask name label, pixel position
        labels, and the circular area covered by the mask. Finally, merges the "base_metal_gap_wo_grid" and "ground
        grid" layers into "base_metal_gap" layer.

        Args:
            chips_map_legend: Dictionary where keys are chip names, values are chip cells

        """
        self.chips_map_legend = {}

        for name, cell in tqdm(chips_map_legend.items(), desc='Building cell hierarchy', bar_format=default_bar_format):
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

        labels_cell, region_covered = self._mask_create_geometry()
        if len(self.submasks) > 0:
            region_covered = pya.Region()  # don't fill with metal gap layer if using submasks
            for submask_layout, submask_pos in self.submasks:
                self.top_cell.insert(
                    pya.DCellInstArray(submask_layout.top_cell.cell_index(),
                                       pya.DTrans(submask_pos - submask_layout.wafer_center + self.wafer_center))
                )
        self.top_cell.insert(pya.DCellInstArray(labels_cell.cell_index(), pya.DTrans(pya.DVector(0, 0))))

        for (i, row) in enumerate(tqdm(self.chips_map, desc='Adding chips to mask', bar_format=default_bar_format)):
            for (j, slot) in enumerate(row):
                position = step_ver * (i + 1) + step_hor * j
                pos_index_name = chr(ord("A") + i) + ("{:02d}".format(j))
                added_chip, region_chip = self._add_chip(labels_cell, step_ver, step_hor, position, pos_index_name,
                                                         slot)
                region_covered -= region_chip
                if not added_chip:
                    self.chips_map[i][j] = "---"

        maskextra_cell = self.layout.create_cell("MaskExtra")
        self._insert_mask_name_label(self.top_cell, default_layers["mask_graphical_rep"])
        self._mask_create_covered_region(maskextra_cell, region_covered, self.layers_to_mask)

        merge.merge_layers(self.layout, [maskextra_cell, labels_cell], self._face()["base_metal_gap_wo_grid"],
                           self._face()["ground_grid"], self._face()["base_metal_gap"])

    def _face(self):
        return default_faces[self.face_id]

    def _mask_create_geometry(self):
        labels_cell = self.layout.create_cell("ChipLabels")  # A new cell into the layout
        y_clip = -14.5e4

        points = []
        for a in range(0, 256 + 1):
            x = math.cos(a / 128 * math.pi) * self.wafer_rad
            y = max(math.sin(a / 128 * math.pi) * self.wafer_rad, y_clip)
            if (y > 0 and (x > self.wafer_top_flat_length/2 or x < -self.wafer_top_flat_length/2)) or \
               (y < 0 and (x > self.wafer_bottom_flat_length/2 or x < -self.wafer_bottom_flat_length/2)):
                points.append(pya.DPoint(self.wafer_center.x + x, self.wafer_center.y + y))

        region_covered = pya.Region(pya.DPolygon(points).to_itype(self.layout.dbu))
        return labels_cell, region_covered

    def _add_chip(self, label_cell, step_ver, step_hor, position, pos_index_name, slot):
        """Returns a tuple (Boolean telling if the chip was added, Region which the chip covers)."""
        # center of the chip at distance self.chip_size from the mask edge
        chip_region = pya.Region()
        if (position - step_ver * 0.5 + step_hor * 0.5 - self.wafer_center).length() - self.wafer_rad < \
                -self.chip_size:
            if slot in self.chips_map_legend.keys():
                trans = pya.DTrans(position - self.chip_box_offset) * self.chip_trans
                self.top_cell.insert(pya.DCellInstArray(self.chips_map_legend[slot].cell_index(), trans))
                produce_label(label_cell, pos_index_name, position + pya.DVector(self.chip_size, 0), "bottomright",
                              self.dice_width, self.text_margin,
                              [self._face()["base_metal_gap_wo_grid"], self._face()["base_metal_gap_for_EBL"]],
                              self._face()["ground_grid_avoidance"])
                trans2 = pya.DTrans(position)
                chip_region = pya.Region(pya.Box(trans2 * pya.DBox(0, 0, self.chip_size, self.chip_size) * (
                        1 / self.layout.dbu)))
                # add graphical representation
                chip_name = self._get_chip_name(self.chips_map_legend[slot])
                self._add_chip_graphical_representation_layer(chip_name, position, pos_index_name)
                return True, chip_region
        return False, chip_region

    def _mask_create_covered_region(self, maskextra_cell, region_covered, layers_dict):
        dbu = self.layout.dbu

        for layer, postfix in layers_dict.items():
            inst = self._insert_mask_name_label(maskextra_cell, self._face()[layer], postfix)
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
                maskextra_cell.shapes(self.layout.layer(self._face()[layer_name])).insert(region_covered)

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

    def _add_chip_graphical_representation_layer(self, chip_name, position, pos_index_name):
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
        chip_name_trans = pya.DTrans(position + pya.DVector((self.chip_size - chip_name_text.dbbox().width()) / 2,
                                                            self.mask_text_scale * 750))
        self.top_cell.insert(pya.DCellInstArray(chip_name_text.cell_index(), chip_name_trans))
        pos_index_trans = pya.DTrans(position + pya.DVector((self.chip_size - pos_index_name_text.dbbox().width()) / 2,
                                                            self.mask_text_scale * 6000))
        self.top_cell.insert(pya.DCellInstArray(pos_index_name_text.cell_index(), pos_index_trans))

    def _insert_mask_name_label(self, cell, layer, postfix=""):
        if postfix != "":
            postfix = "-" + postfix
        cell_mask_name = self.layout.create_cell("TEXT", "Basic", {
            "layer": layer,
            "text": default_brand + "-" + self.name + "v" + str(self.version) + postfix,
            "mag": self.mask_name_scale*5000.0,
        })
        cell_mask_name_h = cell_mask_name.dbbox().height()
        cell_mask_name_w = cell_mask_name.dbbox().width()
        trans = pya.DTrans(self.wafer_center.x - cell_mask_name_w / 2, -self.mask_name_offset - cell_mask_name_h / 2)
        inst = cell.insert(pya.DCellInstArray(cell_mask_name.cell_index(), trans))
        return inst
