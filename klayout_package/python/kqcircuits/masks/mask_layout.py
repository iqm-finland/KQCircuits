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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).
import math
from collections.abc import Sequence

from typing import Tuple
from tqdm import tqdm

from kqcircuits.util.label_polygons import get_text_polygon
from kqcircuits.pya_resolver import pya
from kqcircuits.defaults import (
    default_layers,
    default_brand,
    default_faces,
    default_mask_parameters,
    default_layers_to_mask,
    default_covered_region_excluded_layers,
    default_mask_export_layers,
    default_bar_format,
)
from kqcircuits.elements.markers.marker import Marker
from kqcircuits.elements.markers.mask_marker_fc import MaskMarkerFc
from kqcircuits.util.geometry_helper import circle_polygon
from kqcircuits.util.label import produce_label, LabelOrigin
from kqcircuits.util.merge import merge_layout_layers_on_face, convert_child_instances_to_static


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
            or a dictionary with keys as pya.DPoints representing chip coordinate and as value a dictionary containing
            the keys chip_name, local_chip_trans and position_label.
            example: {pya.DPoint(-500,1000):{'chip_name': 'ABC',
            'local_chip_trans': pya.DTrans(pya.DVector(1800, -1800)) * pya.DTrans().M90 , 'position_label':'H08'}}
        align_to: optional exact point of placement, an (x,  y) coordinate tuple. By default the mask is centered.
        chips_map_legend: Dictionary where keys are chip names, values are chip cells
        wafer_rad: Wafer radius
        wafer_center: Wafer center as a pya.DVector
        chips_map_offset: Offset to make chips_map centered on wafer
        wafer_top_flat_length: length of flat edge at the top of the wafer
        wafer_bottom_flat_length: length of flat edge at the bottom of the wafer
        dice_width: Dicing width for this mask layout
        text_margin: Text margin for this mask layout
        chip_size: side width of the chips (for square chips), or tuple (width, height) for rectangular chips
        edge_clearance: minimum clearance of outer chips from the edge of the mask
        remove_chips: if True (default), chips that violate edge_clearance or conflict with markers are removed from
            chip maps. Note that ``extra_chips`` are never removed.
        chip_box_offset: Offset (pya.DVector) from chip origin of the chip frame boxes for this face
        chip_trans: DTrans applied to all chips
        mask_name_offset: (DEPRECATED) mask name label offset from default position (DPoint)
        mask_name_scale: text scaling factor for mask name label (float)
        mask_name_box_margin: margin around the mask name that determines the box size around the name (float)
        mask_text_scale: text scaling factor for graphical representation layer (float)
        mask_markers_dict: dictionary of all markers to be placed and kwargs to determine their position (dict)
        mask_marker_offset: offset of mask markers from wafer center in horizontal and vertical directions (float)
        mask_export_layers: list of layer names (without face_ids) to be exported as individual mask `.oas` files
        mask_export_density_layers: list of layer names (without face_ids) for which we want to calculate the coverage
            density
        submasks: list of submasks, each element is a tuple (submask mask_layout, submask position)
        extra_id: extra string used to create unique name for mask layouts with the same face_id
        extra_chips: List of tuples (name, position, trans, position_label) for chips placed outside chips_map
            trans is an optional transformation to use in place of self.chip_trans
            position_label is an optional string that overrides the automatic chip position label in the mask grid
        top_cell: Top cell of this mask layout
        added_chips: List of (chip name, chip_cell, chip position, chip bounding box, chip dtrans, position_label)
            populated by chips added during build()
        chips_placed_by_position_label: Dictionary of ``{position_label: chip_name}`` where the chip exists in
            chips_map_legend and will be placed according to the position_label
        chip_copies: Dictionary of ``{name_copy: properties}`` where ``properties`` contains the name and location data
            for each chip that was actually added to the mask.
        mirror_labels: Boolean, if True mask and chip copy labels are mirrored. Default False.
        bbox_face_ids: List of face_ids to consider when calcualting the bounding box of chips. Defaults to [face_id]
    """

    def __init__(self, layout, name, version, with_grid, chips_map, face_id, **kwargs):

        self.layout: pya.Layout = layout
        self.name = name
        self.version = version
        self.with_grid = with_grid
        self.face_id = face_id
        self.chips_map = chips_map
        self.chips_map_legend = None
        self.chip_bounding_boxes = None

        self.layers_to_mask = kwargs.get("layers_to_mask", default_layers_to_mask)
        self.covered_region_excluded_layers = kwargs.get(
            "covered_region_excluded_layers", default_covered_region_excluded_layers
        ) + ["mask_edge"]
        self.wafer_rad = kwargs.get("wafer_rad", default_mask_parameters[self.face_id]["wafer_rad"])
        self.wafer_center = pya.DVector(0, 0)
        self.chips_map_offset = kwargs.get(
            "chips_map_offset", default_mask_parameters[self.face_id]["chips_map_offset"]
        )
        self.wafer_top_flat_length = kwargs.get("wafer_top_flat_length", 0)
        self.wafer_bottom_flat_length = kwargs.get("wafer_bottom_flat_length", 0)
        self.dice_width = kwargs.get("dice_width", default_mask_parameters[self.face_id]["dice_width"])
        self.text_margin = kwargs.get("text_margin", default_mask_parameters[self.face_id]["text_margin"])
        self.chip_size = kwargs.get("chip_size", default_mask_parameters[self.face_id]["chip_size"])
        if isinstance(self.chip_size, Sequence):
            self.chip_width, self.chip_height = self.chip_size
        else:
            self.chip_width, self.chip_height = self.chip_size, self.chip_size
        self.edge_clearance = kwargs.get("edge_clearance", (self.chip_width + self.chip_height) / 4)
        self.remove_chips = kwargs.get("remove_chips", True)
        self.chip_box_offset = kwargs.get("chip_box_offset", default_mask_parameters[self.face_id]["chip_box_offset"])
        self.chip_trans = kwargs.get("chip_trans", default_mask_parameters[self.face_id]["chip_trans"])
        self.mask_name_offset = kwargs.get("mask_name_offset", pya.DPoint(0, 0))  # DEPRECATED
        self.mask_name_scale = kwargs.get("mask_name_scale", 1)
        self.mask_name_box_margin = kwargs.get("mask_name_box_margin", 1000)
        self.mask_text_scale = kwargs.get("mask_text_scale", default_mask_parameters[self.face_id]["mask_text_scale"])
        self.mask_markers_dict = kwargs.get("mask_markers_dict", {Marker: {}, MaskMarkerFc: {}})
        self.mask_markers_type = kwargs.get("mask_markers_type", "all")
        self.mask_marker_offset = kwargs.get(
            "mask_marker_offset", default_mask_parameters[self.face_id]["mask_marker_offset"]
        )
        self.mask_export_layers = kwargs.get("mask_export_layers", default_mask_export_layers)
        self.mask_export_density_layers = kwargs.get("mask_export_density_layers", [])
        self.submasks = kwargs.get("submasks", [])
        self.extra_id = kwargs.get("extra_id", "")
        self.extra_chips = kwargs.get("extra_chips", [])
        self.chips_placed_by_position_label = kwargs.get("chips_placed_by_position_label", {})
        self.mirror_labels = kwargs.get("mirror_labels", False)
        self.bbox_face_ids = kwargs.get("bbox_face_ids", [self.face_id])

        self.top_cell = self.layout.create_cell(f"{self.name} {self.face_id}")
        self.added_chips = []
        self.graphical_representation_inputs = []

        self.align_to = kwargs.get("align_to", None)
        self.chip_counts = {}
        self.extra_chips_maps = kwargs.get("extra_chips_maps", [])
        self.chip_array_to_export = []
        self.chip_copies = {}
        # For mask name the letter I stats at x=750
        self._mask_name_letter_I_offset = 750

        self._mask_name_box_bottom_y = 35000
        self._max_x = 0
        self._max_y = 0
        self._min_x = 0
        self._min_y = 0

    def add_chips_map(self, chips_map, align=None, align_to=None, chip_size=None, chip_trans=None):
        """Add additional chip maps to the main chip map.
        Only used when the main chip map is not a dictionary.

        The specified extra chip map, a.k.a. sub-grid, will be attached to the main grid. It may use
        different chip size than the main grid. For convenience left and rigtht sub-grids will be
        rotated 90 degrees clockwise.

        Args:
            chips_map: List of lists (2D-array) of strings, each string is a chip name (or --- for no chip)
            align: to what side of the main grid this sub-grid attaches. Allowed values: top, left, right and bottom.
            align_to: optional exact point of placement. (x,  y) coordinate tuple
            chip_size: a different chip size may be used in each sub-grid
            chip_trans: chip transformation to use for chips in this sub-grid, defaults to self.chip_trans.
        """
        chip_size = self.chip_size if not chip_size else chip_size
        self.extra_chips_maps.append((chips_map, chip_size, align, align_to, chip_trans))

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
        self.chip_bounding_boxes = {}

        for name, cell in tqdm(chips_map_legend.items(), desc="Building cell hierarchy", bar_format=default_bar_format):
            self.chip_counts[name] = 0
            # create copies of the chips, so that modifying these only affects the ones in this MaskLayout
            new_cell = self.layout.create_cell(name)
            new_cell.copy_tree(cell)

            # Find the bounding box encompassing base metal gap shapes in all in bbox_face_ids
            bboxes = [
                new_cell.dbbox_per_layer(self.layout.layer(default_faces[face_id]["base_metal_gap_wo_grid"]))
                for face_id in self.bbox_face_ids
            ]
            if not all(b.empty() for b in bboxes):
                p1_xs, p1_ys, p2_xs, p2_ys = zip(*[(b.p1.x, b.p1.y, b.p2.x, b.p2.y) for b in bboxes if not b.empty()])
                self.chip_bounding_boxes[name] = pya.DBox(min(p1_xs), min(p1_ys), max(p2_xs), max(p2_ys))
            else:
                self.chip_bounding_boxes[name] = pya.DBox()

            # remove layers belonging to another face
            for face_id, face_dictionary in default_faces.items():
                if face_id != self.face_id:
                    for layer_info in face_dictionary.values():
                        new_cell.flatten(True).clear(self.layout.layer(layer_info))

            self.chips_map_legend[name] = new_cell

        self.region_covered = self._mask_create_geometry()
        if len(self.submasks) > 0:
            self.region_covered = pya.Region()  # don't fill with metal gap layer if using submasks
            for submask_layout, submask_pos in self.submasks:
                self.top_cell.insert(
                    pya.DCellInstArray(
                        submask_layout.top_cell.cell_index(),
                        pya.DTrans(submask_pos - submask_layout.wafer_center + self.wafer_center),
                    )
                )

        maskextra_cell: pya.Cell = self.layout.create_cell("MaskExtra")
        marker_region = self._add_all_markers_to_mask(maskextra_cell)

        self._insert_mask_name_label(self.top_cell, default_layers["mask_graphical_rep"], "G")
        # add chips from chips_map
        if isinstance(self.chips_map, dict):
            self._add_chips_map_dict(self.chip_size, marker_region)
        else:
            self._add_chips_from_map(self.chips_map, self.chip_size, None, self.align_to, marker_region)
            for chips_map, chip_size, align, align_to, chip_trans in self.extra_chips_maps:
                self._add_chips_from_map(chips_map, chip_size, align, align_to, marker_region, chip_trans)

        # add chips outside chips_map
        for name, pos, *optional in self.extra_chips:
            trans, position_label = None, None
            if optional and isinstance(optional[0], pya.DTrans):
                trans = optional[0]
                if len(optional) > 1 and isinstance(optional[1], str):
                    position_label = optional[1]
            else:
                trans = self.chip_trans
                if optional and isinstance(optional[0], str):
                    position_label = optional[0]
            if name in chips_map_legend:
                self.region_covered -= self._add_chip(name, pos, trans, position_label)[1]
                self.chip_counts[name] += 1

        self.region_covered -= marker_region
        self._mask_create_covered_region(maskextra_cell, self.region_covered, self.layers_to_mask)
        convert_child_instances_to_static(self.layout, maskextra_cell, only_elements=True, prune=True)
        merge_layout_layers_on_face(self.layout, maskextra_cell, self.face())

    def insert_chips(self):
        """Insert chips after resolving their position labels"""
        for _, chip_cell, _, _, dtrans, _ in self.added_chips:
            self.top_cell.insert(pya.DCellInstArray(chip_cell.cell_index(), dtrans))
        for params in self.graphical_representation_inputs:
            self._add_chip_graphical_representation_layer(*params)

    @staticmethod
    def generate_position_label(chip_placement_list, unit_x, unit_y):
        """Generate a position label based on the coordinate of each chip.

        Args:
            chip_placement_list: list of lists [[chip_size, chip_coordinate, chip_name, position_label]]
            unit_x: minimum chip x dimension
            unit_y: minimum chip y dimension

        Returns: Dictionary with the global coordinates of each chip of the sub array. It has the form
            {(coord_x, coord_y): {'chip_name': name, 'position_label': xxx}}
        """
        xvals = set()
        yvals = set()
        assigned_coord_map = {}
        # To not pollute the space of chip positions, rather than assigning a new row letter and column number
        # for each unique x- and y-coordinate, round the coordinates to the smallest chip dimensions.
        # This still guarantees that each chip gets unique chip position label, but rows that are closer
        # together than the smallest chip height will be assigned the same letter.
        for chip_size, coord, _, position_label in chip_placement_list:
            if isinstance(chip_size, tuple):
                chip_size_x = chip_size[0]
                chip_size_y = chip_size[1]
            else:
                chip_size_x = chip_size
                chip_size_y = chip_size
            # coord is bottom left corner of the chip
            center_point = (coord.x + chip_size_x / 2, coord.y + chip_size_y / 2)
            pos_x = math.floor(round(center_point[0]) / unit_x) * unit_x
            pos_y = math.floor(round(center_point[1]) / unit_y) * unit_y
            if not position_label:
                xvals.add(pos_x)
                yvals.add(pos_y)
            assigned_coord_map.update({coord: pya.DPoint(pos_x, pos_y)})
        _chip_placement_dict = {}
        for _, coord, chip_name, _ in chip_placement_list:
            row = sorted(yvals, reverse=True).index(assigned_coord_map[coord].y)
            column = sorted(xvals).index(assigned_coord_map[coord].x)
            position_label = MaskLayout.two_coordinates_to_position_label(row, column)
            _chip_placement_dict[coord] = {"chip_name": chip_name, "position_label": position_label}
        return _chip_placement_dict

    def generate_and_insert_chip_copy_labels(self, labels_cell, layers, mask_name_for_chip=None):
        """Inserts chip copy labels to all chips in this mask layout and its submasks

        Args:
            labels_cell: Cell to which the labels are inserted
            layers: list of layer names (without face_ids) where the labels are produced
            mask_name_for_chip: mask name to place on each chip, or None (default) to not add mask names to the chip.
        """

        # find labels_cell for this mask and each submask
        labels_cells = {self: labels_cell}
        for submask_layout, _ in self.submasks:
            for inst in submask_layout.top_cell.each_inst():
                # workaround for getting the cell due to KLayout bug, see
                # https://www.klayout.de/forum/discussion/1191
                # TODO: replace by `inst_cell = inst.cell` once KLayout bug is fixed
                inst_cell = submask_layout.layout.cell(inst.cell_index)
                if inst_cell.name.startswith("ChipLabels"):
                    labels_cells[submask_layout] = inst_cell
                    break
        # find all unique x and y coords of center points of chip bboxes and place them in the corresponding keys
        # in chips_dict. These x and y coords are not used for anything else but to determine the content of labels
        chips_dict = {}  # {(pos_x, pos_y): chip_name, chip_pos (in submask coordinates), chip_inst, mask_layout}
        unit_x = round(min(bbox.p2.x - bbox.p1.x for _, _, _, bbox, _, _ in self.added_chips))
        unit_y = round(min(bbox.p2.y - bbox.p1.y for _, _, _, bbox, _, _ in self.added_chips))

        def get_chip_size_and_coordinate(boundingbox, dtrans):
            _h = boundingbox.height()
            _w = boundingbox.width()
            center_point = dtrans * boundingbox.center()
            coord = center_point * pya.DTrans(pya.DVector(-_w / 2, _h / 2))
            return (_w, _h), coord

        chip_placement_list = [
            [*get_chip_size_and_coordinate(bbox, dtrans), chip_name, position_label]
            for chip_name, _, pos, bbox, dtrans, position_label in self.added_chips
        ]
        chips_dict = self.generate_position_label(chip_placement_list, unit_x, unit_y)
        for i, chip_sub_list in enumerate(self.added_chips):
            bbox = chip_sub_list[3]
            dtrans = chip_sub_list[4]
            chip_sub_list = chip_sub_list[:-1] + (
                chips_dict[get_chip_size_and_coordinate(bbox, dtrans)[1]]["position_label"],
            )
            self.added_chips[i] = chip_sub_list
        self.insert_chip_copy_labels(labels_cell, layers, mask_name_for_chip=mask_name_for_chip)

    def insert_chip_copy_labels(self, labels_cell, layers, mask_name_for_chip=None):
        """Inserts position labels and mask name into chip frames, and then updates self.chip_copies dictionary

        Args:
            labels_cell: Cell to which the labels are inserted
            layers: list of layer names (without face_ids) where the labels are produced
            mask_name_for_chip: mask name to place on each chip, or None (default) to not add mask names to the chip.
        """
        labels_cells = {self: labels_cell}
        for chip_name, _, _, bbox, dtrans, position_label in self.added_chips:
            labels_cell_2 = labels_cells[self]
            total_mirror_label = bool(dtrans.is_mirror()) ^ bool(self.mirror_labels)
            bbox_x1, bbox_x2 = (bbox.left, bbox.right) if total_mirror_label else (bbox.right, bbox.left)
            produce_label(
                labels_cell_2,
                position_label,
                dtrans * (pya.DPoint(bbox_x1, bbox.bottom)),
                LabelOrigin.BOTTOMRIGHT,
                self.dice_width,
                self.text_margin,
                [self.face()[layer] for layer in layers],
                self.face()["ground_grid_avoidance"],
                mirror=self.mirror_labels,
            )
            if mask_name_for_chip is not None:
                produce_label(
                    labels_cell_2,
                    mask_name_for_chip,
                    dtrans * (pya.DPoint(bbox_x2, bbox.top)),
                    LabelOrigin.TOPLEFT,
                    self.dice_width,
                    self.text_margin,
                    [self.face()[layer] for layer in layers],
                    self.face()["ground_grid_avoidance"],
                    mirror=self.mirror_labels,
                )
            bbox_xr = bbox.right if dtrans.is_mirror() else bbox.left
            self.graphical_representation_inputs.append(
                (chip_name, dtrans * (pya.DPoint(bbox_xr, bbox.bottom)), position_label, bbox.width(), labels_cell_2)
            )
            i, j = self.position_label_to_two_coordinates(position_label)
            chip_box = pya.DBox(dtrans * bbox)
            self.chip_copies[position_label] = {
                "name_chip": chip_name,
                "i": i,
                "j": j,
                "x": chip_box.left,
                "y": chip_box.bottom,
                "width": chip_box.width(),
                "height": chip_box.height(),
            }

    def face(self):
        """Returns the face dictionary for this mask layout"""
        return default_faces[self.face_id]

    @staticmethod
    def two_coordinates_to_position_label(row: int, column: int) -> str:
        """Converts two integers to chip position label, e.g. (2,3) -> 'C03'"""
        if row < 0 or ord("A") + row > ord("Z"):
            raise ValueError(f"Row coordinate {row} out of bounds")
        if column < 0 or column > 99:
            raise ValueError(f"Column coordinate {column} out of bounds")
        return chr(ord("A") + row) + (f"{column:02d}")

    @staticmethod
    def position_label_to_two_coordinates(position_label: str) -> Tuple[int, int]:
        """Converts chip position label to two integer coordinate, e.g. 'C03' -> (2,3)"""
        row, col = ord(position_label[0]) - ord("A"), int(position_label[1:])
        if row < 0 or ord("A") + row > ord("Z"):
            raise ValueError(f"Letter part in {position_label} out of bounds")
        if col < 0 or col > 99:
            raise ValueError(f"Number part in {position_label} out of bounds")
        return row, col

    def _mask_create_geometry(self):
        y_clip = -14.5e4

        points = []
        for a in range(0, 256 + 1):
            x = math.cos(a / 128 * math.pi) * self.wafer_rad
            y = max(math.sin(a / 128 * math.pi) * self.wafer_rad, y_clip)
            if (y > 0 and (x > self.wafer_top_flat_length / 2 or x < -self.wafer_top_flat_length / 2)) or (
                y < 0 and (x > self.wafer_bottom_flat_length / 2 or x < -self.wafer_bottom_flat_length / 2)
            ):
                points.append(pya.DPoint(self.wafer_center.x + x, self.wafer_center.y + y))

        region_covered = pya.Region(pya.DPolygon(points).to_itype(self.layout.dbu))
        return region_covered

    def _add_chips_map_dict(self, chip_size, marker_region):
        if isinstance(chip_size, Sequence):
            chip_width, _ = chip_size
        else:
            chip_width = chip_size

        region_used = pya.Region()
        allowed_region = (
            pya.Region(circle_polygon(self.wafer_rad - self.edge_clearance).to_itype(self.layout.dbu))
            - marker_region
            - pya.Region(
                pya.DBox(-self.wafer_rad, self._mask_name_box_bottom_y, self.wafer_rad, self.wafer_rad).to_itype(
                    self.layout.dbu
                )
            )
        )
        for position, chip_dict in self.chips_map.items():
            if set(chip_dict["chip_name"]) != set("-"):
                chip_trans = chip_dict.get("local_chip_trans", self.chip_trans)
                added_chip, region_chip = self._add_chip(
                    chip_dict["chip_name"],
                    position,
                    chip_trans,
                    position_label=chip_dict["position_label"],
                    allowed_region=allowed_region,
                    chip_width=chip_width,
                    adjust_trans=False,
                )
                region_used += region_chip
                if added_chip:
                    self.chip_counts[chip_dict["chip_name"]] += 1

        self.region_covered -= region_used

    def _add_chips_from_map(self, chips_map, chip_size, align, align_to, marker_region, chip_trans=None):
        if chip_trans is None:
            chip_trans = self.chip_trans
        if isinstance(chip_size, Sequence):
            chip_width, chip_height = chip_size
        else:
            chip_width, chip_height = chip_size, chip_size
        orig = pya.DVector(-self.wafer_rad, self.wafer_rad) - self.chips_map_offset
        if align_to:
            orig = pya.DVector(*align_to)
        elif align:  # autoalign to the specified side of the existing layout
            w = len(chips_map[0]) * chip_width / 2
            h = len(chips_map) * chip_height
            if align == "top":
                orig = pya.DVector(-w, h + self._max_y * self.layout.dbu)
            elif align == "bottom":
                orig = pya.DVector(-w, self._min_y * self.layout.dbu)
            elif align == "left":
                orig = pya.DVector(-h + self._min_x * self.layout.dbu, w)
            elif align == "right":
                orig = pya.DVector(self._max_x * self.layout.dbu, w)
        if align in ("left", "right"):  # rotate clockwise
            chips_map = zip(*reversed(chips_map))

        region_used = pya.Region()
        allowed_region = (
            pya.Region(circle_polygon(self.wafer_rad - self.edge_clearance).to_itype(self.layout.dbu))
            - marker_region
            - pya.Region(
                pya.DBox(-self.wafer_rad, self._mask_name_box_bottom_y, self.wafer_rad, self.wafer_rad).to_itype(
                    self.layout.dbu
                )
            )
        )
        for i, row in enumerate(tqdm(chips_map, desc="Adding chips to mask", bar_format=default_bar_format)):
            for j, name in enumerate(row):
                if set(name) == set("-"):
                    continue
                position = pya.DPoint(chip_width * j, -chip_height * (i + 1)) + orig
                added_chip, region_chip = self._add_chip(
                    name, position, chip_trans, allowed_region=allowed_region, chip_width=chip_width
                )
                region_used += region_chip
                if added_chip:
                    self.chip_counts[name] += 1
        self.region_covered -= region_used
        box = region_used.bbox()
        self._min_x = min(box.p1.x, self._min_x)
        self._min_y = min(box.p1.y, self._min_y)
        self._max_x = max(box.p2.x, self._max_x)
        self._max_y = max(box.p2.y, self._max_y)

    def _add_chip(
        self, name, position, trans, position_label=None, allowed_region=None, chip_width=None, adjust_trans=True
    ):
        """Returns a tuple (Boolean telling if the chip was added, Region which the chip covers)."""
        if chip_width is None:
            chip_width = self.chip_width
        chip_region = pya.Region()
        if name in self.chips_map_legend:
            chip_cell = self.chips_map_legend[name]
            bounding_box = self.chip_bounding_boxes[name]
            bbox_offset = chip_width - bounding_box.width()
            if adjust_trans:
                trans = pya.DTrans(position + pya.DVector(bbox_offset, 0) - self.chip_box_offset) * trans
            else:
                trans = pya.DTrans(position) * trans
            chip_region = pya.Region(pya.Box(trans * bounding_box * (1 / self.layout.dbu)))
            if self.remove_chips and allowed_region is not None and chip_region.inside(allowed_region).is_empty():
                return False, pya.Region()
            self.added_chips.append((name, chip_cell, position, bounding_box, trans, position_label))
            return True, chip_region
        return False, chip_region

    def _add_all_markers_to_mask(self, maskextra_cell):
        marker_region = pya.Region()
        for marker, m_kwargs in self.mask_markers_dict.items():
            # load values into kwargs
            m_kwargs["window"] = m_kwargs.get("window", True)
            m_kwargs["face_ids"] = m_kwargs.get("face_ids", [self.face_id])
            m_kwargs["wafer_rad"] = m_kwargs.get("wafer_rad", self.wafer_rad)
            m_kwargs["edge_clearance"] = m_kwargs.get("edge_clearance", self.edge_clearance)
            cell_marker = marker.create(self.layout, **m_kwargs)

            # Name of the mask marker might in some cases conflict with the names
            # of the chip markers, after PCells in mask are converted to static
            # using convert_child_instances_to_static. This makes the exported mask layout OAS file
            # to not be able to open using KLayout. If we make the name distinct, this no
            # longer becomes an issue.
            cell_marker.name = f"Mask {cell_marker.name}"

            marker_transes = marker.get_marker_locations(cell_marker, **m_kwargs)
            for trans in marker_transes:
                inst = maskextra_cell.insert(pya.DCellInstArray(cell_marker.cell_index(), trans))
                marker_region += marker.get_marker_region(inst, **m_kwargs)
        return marker_region

    def _mask_create_covered_region(self, maskextra_cell, region_covered, layers_dict):
        dbu = self.layout.dbu

        leftmost_label_x = 1e10
        labels = []
        for layer, postfix in layers_dict.items():
            label_cell, label_trans = self._create_mask_name_label(self.face()[layer], postfix)
            leftmost_label_x = min(label_trans.disp.x, leftmost_label_x)
            labels.append((label_cell, label_trans))
        # align left edges of mask name labels in different layers
        for label_cell, label_trans in labels:
            label_trans = pya.DTrans(label_trans.rot, label_trans.is_mirror(), leftmost_label_x, label_trans.disp.y)
            inst = maskextra_cell.insert(pya.DCellInstArray(label_cell.cell_index(), label_trans))
            region_covered -= pya.Region(inst.bbox()).extents(self.mask_name_box_margin / dbu)

        circle = pya.DTrans(self.wafer_center) * pya.DPath(
            [
                pya.DPoint(math.cos(a / 32 * math.pi) * self.wafer_rad, math.sin(a / 32 * math.pi) * self.wafer_rad)
                for a in range(0, 64 + 1)
            ],
            100,
        )
        maskextra_cell.shapes(self.layout.layer(default_layers["mask_graphical_rep"])).insert(circle)

        maskextra_cell.shapes(self.layout.layer(default_layers["mask_graphical_rep"])).insert(region_covered)
        # remove unwanted circle boundary and filling from `layers_to_mask` which have been excluded in
        # `covered_region_excluded_layers`
        for layer_name in layers_dict.keys():
            if layer_name not in self.covered_region_excluded_layers:
                maskextra_cell.shapes(self.layout.layer(self.face()[layer_name])).insert(region_covered)

        self.top_cell.insert(pya.DCellInstArray(maskextra_cell.cell_index(), pya.DTrans()))

    def _get_chip_name(self, search_cell):
        for chip_name, cell in self.chips_map_legend.items():
            if search_cell == cell:
                return chip_name
        return ""

    def _add_chip_graphical_representation_layer(self, chip_name, position, pos_index_name, chip_width, cell):
        layout = cell.layout()
        chip_name_text = get_text_polygon(chip_name, 15000 * self.mask_text_scale / len(chip_name))
        chip_name_width = chip_name_text.bbox().to_dtype(layout.dbu).width()
        pos_index_name_text = get_text_polygon(pos_index_name, 4000 * self.mask_text_scale)
        pos_index_name_width = pos_index_name_text.bbox().to_dtype(cell.layout().dbu).width()
        chip_name_trans = pya.DTrans(
            position + pya.DVector((chip_width - chip_name_width) / 2, self.mask_text_scale * 750)
        )
        cell.shapes(cell.layout().layer(default_layers["mask_graphical_rep"])).insert(chip_name_text, chip_name_trans)
        pos_index_trans = pya.DTrans(
            position + pya.DVector((chip_width - pos_index_name_width) / 2, self.mask_text_scale * 6000)
        )
        cell.shapes(cell.layout().layer(default_layers["mask_graphical_rep"])).insert(
            pos_index_name_text, pos_index_trans
        )

    def _insert_mask_name_label(self, cell, layer, postfix=""):
        cell_mask_name, trans = self._create_mask_name_label(layer, postfix)
        inst = cell.insert(pya.DCellInstArray(cell_mask_name.cell_index(), trans))
        return inst

    def _create_mask_name_label(self, layer, postfix=""):
        if postfix != "":
            postfix = "-" + postfix
        cell_mask_name = self.layout.create_cell(
            "TEXT",
            "Basic",
            {
                "layer": layer,
                "text": default_brand + "-" + self.name + "v" + str(self.version) + postfix,
                "mag": self.mask_name_scale * 5000.0,
            },
        )
        cell_mask_name_h = cell_mask_name.dbbox().height()
        cell_mask_name_w = cell_mask_name.dbbox().width()
        # height of top left corner
        cell_mask_name_y = math.sqrt(
            (self.wafer_rad - self.edge_clearance) ** 2 - (cell_mask_name_w / 2 + self.mask_name_box_margin) ** 2
        )
        self._mask_name_box_bottom_y = cell_mask_name_y - cell_mask_name_h - 2 * self.mask_name_box_margin
        trans = pya.DTrans(
            -self._mask_name_letter_I_offset - cell_mask_name_w / 2,
            cell_mask_name_y - cell_mask_name_h - self.mask_name_box_margin,
        )
        if self.mirror_labels:
            trans *= pya.DTrans(2, True, -2 * trans.disp.x, 0)
        return cell_mask_name, trans
