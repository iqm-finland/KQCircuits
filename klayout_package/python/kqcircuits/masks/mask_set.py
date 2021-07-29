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

from autologging import logged, traced
from tqdm import tqdm

from kqcircuits.pya_resolver import pya
from kqcircuits.masks import mask_export
from kqcircuits.defaults import default_bar_format
from kqcircuits.masks.mask_layout import MaskLayout


@traced
@logged
class MaskSet:
    """Class representing a set of masks for different chip faces.

    A mask set consists of one or more MaskLayouts, each of which is for a certain face.

    To create a mask, add mask layouts to the mask set using add_mask_layout() and set the self.chips_map_legend (or add
    chips using add_chip()) to define the chips in these mask layouts. Then call build() to create the actual cells.

    Example:
        mask = MaskSet(...)
        mask.add_mask_layout(...)
        mask.add_mask_layout(...)
        mask.chips_map_legend = {...}
        mask.build()
        mask.export(...)

    Attributes:
        layout: pya.Layout of this mask set
        name: Name of the mask set
        version: Version of the mask set
        with_grid: Boolean determining if ground grid is generated
        export_drc: Boolean determining if DRC report is exported
        chips_map_legend: Dictionary where keys are chip names, values are chip cells
        mask_layouts: list of MaskLayout objects in this mask set
        mask_export_layers: list of names of the layers which are exported for each MaskLayout
        used_chips: similar to chips_map_legend, but only includes chips which are actually used in mask layouts

    """

    def __init__(self, layout, name="MaskSet", version=1, with_grid=False, export_drc=False, mask_export_layers=None):
        super().__init__()
        if layout is None or not isinstance(layout, pya.Layout):
            error_text = "Cannot create mask with invalid or nil layout."
            error = ValueError(error_text)
            self.__log.exception(error_text, exc_info=error)
            raise error

        self.layout = layout
        self.name = name
        self.version = version
        self.with_grid = with_grid
        self.export_drc = export_drc
        self.chips_map_legend = {}
        self.mask_layouts = []
        self.mask_export_layers = mask_export_layers if mask_export_layers is not None else []
        self.used_chips = {}
        self._mask_layouts_per_face = {}  # dict of {face_id: number of mask layouts}

    def add_mask_layout(self, chips_map, face_id="b", mask_layout_type=MaskLayout, **kwargs):
        """Creates a mask layout from chips_map and adds it to self.mask_layouts.

        Args:
            chips_map: List of lists (2D-array) of strings, each string is a chip name (or --- for no chip)
            face_id: face_id of the mask layout
            mask_layout_type: type of the mask layout (MaskLayout or a child class of it)
            kwargs: keyword arguments passed to the mask layout

        Returns:
            the created mask layout
        """

        # add extra_id to distinguish mask layouts in the same face
        if face_id in self._mask_layouts_per_face:
            self._mask_layouts_per_face[face_id] += 1
            kwargs["extra_id"] = str(self._mask_layouts_per_face[face_id])
        else:
            self._mask_layouts_per_face[face_id] = 1

        if ("mask_export_layers" not in kwargs) and self.mask_export_layers:
            kwargs["mask_export_layers"] = self.mask_export_layers

        mask_layout = mask_layout_type(self.layout, self.name, self.version, self.with_grid, chips_map, face_id,
                                       **kwargs)
        self.mask_layouts.append(mask_layout)
        return mask_layout

    def add_chips(self, chips):
        """Add list of chips with parameters to self.chips_map_legend

        Args:
            chips: List of tuples that ``add_chip`` uses.
                For example, ``(QualityFactor, "QDG", parameters)``.
        """
        for chip_class, variant_name, params in tqdm(chips, desc='Building variants', bar_format=default_bar_format):
            self.add_chip(chip_class, variant_name, **params)

    def add_chip(self, chip_class, variant_name, **kwargs):
        """Adds a chip with the given name and parameters to self.chips_map_legend.

        Args:
            chip_class: the chip type class
            variant_name: name for specific variant, the same as in the mask layout
            **kwargs: any parameters passed to the chip PCell
        """
        self.chips_map_legend.update(self.variant_definition(chip_class, variant_name, **kwargs))

    def variant_definition(self, chip_class, variant_name, **kwargs):
        """Returns chip variant definition with default mask specific parameters.

        Args:
            chip_class: the chip type class
            variant_name: name for specific variant, the same as in the mask layout
            **kwargs: any parameters passed to the chip PCell

        Returns:
            dictionary compatible with mask map structure
        """
        self.__log.info("Resolving %s", variant_name)

        chip_parameters = {
            "name_chip": variant_name,
            "display_name": variant_name,
            "name_mask": self.name,
            "name_copy": None,
            "with_grid": self.with_grid,
            **kwargs
        }

        return {variant_name: chip_class.create(self.layout, **chip_parameters)}

    def build(self, remove_guiding_shapes=True):
        """Builds the mask set.

        Creates cells for the mask based on self.mask_layouts and self.chips_map_legend. Optionally removes
        guiding shapes from the layout. Populates self.used_chips with the chips used in the mask layouts.

        Args:
            remove_guiding_shapes (Boolean): determines if the guiding shapes are removed

        """
        # populate used_chips with chips which exist in some mask_layout
        for chip_name, cell in self.chips_map_legend.items():
            for mask_layout in self.mask_layouts:
                if any(chip_name in row for row in mask_layout.chips_map):
                    self.used_chips[chip_name] = cell
                    break

        # build mask layouts
        for mask_layout in self.mask_layouts:
            # include face_id in mask_layout.name only for multi-face masks
            if len(self.mask_layouts) > 1:
                mask_layout.name += mask_layout.face_id
            mask_layout.build(self.chips_map_legend)

        # remove the guiding shapes, like chip boxes and waveguide paths
        if remove_guiding_shapes and self.layout.is_valid_layer(self.layout.guiding_shape_layer()):
            self.layout.delete_layer(self.layout.guiding_shape_layer())

    def export(self, path, view):
        """Exports designs, bitmaps and documentation of this mask set.

        Assumes that self.build() has been called before.

        Args:
            path: path where the folder for this mask set is created
            view: KLayout view object

        """
        mask_export.export(self, path, view, self.export_drc)

    @staticmethod
    def chips_map_from_box_map(box_map, mask_map):
        """Returns the chips_map created from box_map and mask_map.

        Given NxN box map and MxM mask_map, creates chips_map of size MNxMN. So each element of mask map is "replaced"
        by a box in the box map. Assumes that box_map and mask_map are square.

        Args:
            box_map: dictionary where keys are strings identifying the box type, and values are 2D arrays (lists of
                lists) where each element is a string identifying the chip type

            mask_map: 2D array (list of lists), where each element is a string identifying the box type

        """
        num_box_map_rows = len(list(box_map.values())[0])
        num_mask_map_rows = len(mask_map)
        num_chip_rows = num_box_map_rows*num_mask_map_rows

        chips_map = [["" for _ in range(num_chip_rows)] for _ in range(num_chip_rows)]
        for (k, box_row) in enumerate(mask_map):
            for (l, box) in enumerate(box_row):
                if box in box_map:
                    for (i, row) in enumerate(box_map[box]):
                        for (j, slot) in enumerate(row):
                            chips_map[k*num_box_map_rows + i][l*num_box_map_rows + j] = slot

        return chips_map
