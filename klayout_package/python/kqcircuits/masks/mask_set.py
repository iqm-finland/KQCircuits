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
import copy
import os
import string
import subprocess
import textwrap
from inspect import isclass
from multiprocessing.pool import ThreadPool
from pathlib import Path

from autologging import logged, traced
from tqdm import tqdm

from kqcircuits.pya_resolver import pya
from kqcircuits.defaults import default_bar_format, TMP_PATH, PY_PATH, klayout_executable_command
from kqcircuits.masks.mask_export import export_chip, export_mask_set
from kqcircuits.masks.mask_layout import MaskLayout


@traced
@logged
class MaskSet:
    """Class representing a set of masks for different chip faces.

    A mask set consists of one or more MaskLayouts, each of which is for a certain face.

    To create a mask, add mask layouts to the mask set using add_mask_layout() and add chips to these mask layouts using
    add_chips() or add_chip(). These functions also export some files for each chip. Then call build() to create the
    cell hierarchy of the entire mask, and finally export mask files by calling export().

    Example:
        mask = MaskSet(...)
        mask.add_mask_layout(...)
        mask.add_mask_layout(...)
        mask.add_chips(...)
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
        if ("mask_export_layers" not in kwargs) and self.mask_export_layers:
            kwargs["mask_export_layers"] = self.mask_export_layers

        mask_layout = mask_layout_type(self.layout, self.name, self.version, self.with_grid, chips_map, face_id,
                                       **kwargs)
        self.mask_layouts.append(mask_layout)
        return mask_layout

    def add_chips(self, chips, threads=None):
        """Adds a list of chips with parameters to self.chips_map_legend and exports the files for each chip.

        Args:
            chips: List of tuples that ``add_chip`` uses. Parameters are optional.
                For example, ``(QualityFactor, "QDG", parameters)``.
            threads: Number of parallel threads to use for generation. By default uses ``os.cpu_count()`` threads.
                Uses subprocesses and consequently a lot of memory.

        Warning:
            It is advised to lower the thread number if your system has a lot of CPU cores but not a lot of memory.
            The same applies for exporting large and complex geometry.
        """
        if threads is None:
            threads = os.cpu_count()
        if threads <= 1:
            for chip_class, variant_name, *params in tqdm(chips, desc='Building variants',
                                                          bar_format=default_bar_format):
                self.add_chip(chip_class, variant_name, **(params[0] if params else {}))
        else:
            print(f"Building chip variants in parallel using {threads} threads...")

            with open(PY_PATH / 'kqcircuits/util/create_chip_template.txt', 'r') as f:
                template = string.Template(f.read())

            def _subprocess_worker(args):
                with subprocess.Popen(args) as proc:
                    proc.wait()

            tp = ThreadPool(threads)
            file_names = []
            for chip_class, variant_name, *params in chips:
                # create the script for generating this chip with the correct parameters and exporting the chip files
                params = params[0] if params else {}
                create_element = textwrap.dedent(
                    f"""
                    from {chip_class.__module__} import {chip_class.__name__}
                    cell = {chip_class.__name__}.create(layout,
                        {('name_chip="' + variant_name + '",') if 'name_chip' not in params else ''}
                        {('name_mask="' + self.name + '",') if 'name_mask' not in params else ''}
                        {f'with_grid={self.with_grid},' if 'with_grid' not in params else ''}
                        **{str(params)})
                    """)
                chip_path = TMP_PATH/f"{self.name}_v{self.version}"/"Chips"/f"{variant_name}"
                chip_path.mkdir(parents=True, exist_ok=True)
                script_name = str(chip_path / f"{variant_name}.py")
                file_names.append((variant_name, str(chip_path / f"{variant_name}.oas"), script_name))

                result = template.substitute(name_mask=f"{self.name}_v{self.version}", variant_name=variant_name,
                                             create_element=create_element, chip_class_name=chip_class.__name__,
                                             chip_params=params, export_drc=self.export_drc)
                with open(script_name, "w") as f:
                    f.write(result)

                # launch klayout process that runs the created script
                try:  # pylint: disable=consider-using-with
                    tp.apply_async(_subprocess_worker,
                                   ([klayout_executable_command(), "-e", "-z", "-nc", "-rm", script_name],)
                                   )
                except subprocess.CalledProcessError as e:
                    self.__log.error(e.output)

            # wait for processes to end
            tp.close()
            tp.join()

            # import chip cells exported by the parallel processes into the mask
            for variant_name, file_name, script_name in tqdm(file_names, desc='Building variants (parallel)',
                                                             bar_format=default_bar_format):
                self._load_chip_into_mask(file_name, variant_name)
                # remove the script that was used to generate the chip
                if os.path.exists(script_name):
                    os.remove(script_name)

    def add_chip(self, chip, variant_name, **kwargs):
        """Adds a chip with the given name and parameters to self.chips_map_legend and exports chip files.

        Args:
            chip: the chip type class (for PCell chip), or a chip cell (for manually designed chip)
            variant_name: name for specific variant, the same as in the mask layout
            **kwargs: any parameters passed to the chip PCell
        """

        chip_path = Path(TMP_PATH/f"{self.name}_v{self.version}"/"Chips"/variant_name)
        chip_path.mkdir(parents=True, exist_ok=True)

        if isclass(chip):
            cell = self.variant_definition(chip, variant_name, **kwargs)[variant_name]
            export_chip(cell, variant_name, chip_path, self.layout, self.export_drc)
            self.layout.delete_cell_rec(cell.cell_index())
        else:
            export_chip(chip, variant_name, chip_path, self.layout, self.export_drc)

        self._load_chip_into_mask(str(chip_path / f"{variant_name}.oas"), variant_name)

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
        # build mask layouts (without chip copy labels)
        for mask_layout in self.mask_layouts:
            # include face_id in mask_layout.name only for multi-face masks
            if len(self.mask_layouts) > 1:
                mask_layout.name += mask_layout.face_id
            mask_layout.build(self.chips_map_legend)

        # Insert submask cells to different cell instances, so that these cells can have different chip labels even if
        # the original submask cells are identical. Also copy the MaskLayout objects of identical submasks into separate
        # MaskLayout objects with different `extra_id` so that mask export can use that information.
        mask_layouts_to_remove = set()
        submask_layouts = []
        for mask_layout in self.mask_layouts:
            for i, (sm_layout, sm_pos) in enumerate(mask_layout.submasks):
                new_sm_layout = copy.copy(sm_layout)
                new_sm_layout.extra_id = f" s{i+1}"
                old_top_cell = new_sm_layout.top_cell
                new_sm_layout.top_cell = self.layout.create_cell(f"{new_sm_layout.name}{new_sm_layout.extra_id}")
                new_sm_layout.top_cell.insert(pya.DCellInstArray(old_top_cell.cell_index(), pya.DTrans()))
                mask_layout.top_cell.insert(
                    pya.DCellInstArray(new_sm_layout.top_cell.cell_index(),
                                       pya.DTrans(sm_pos - sm_layout.wafer_center + mask_layout.wafer_center))
                )
                mask_layout.submasks[i] = (new_sm_layout, sm_pos)
                submask_layouts.append(new_sm_layout)
                mask_layouts_to_remove.add(sm_layout)
        self.mask_layouts = submask_layouts + [ml for ml in self.mask_layouts if ml not in mask_layouts_to_remove]

        # add chip copy labels for every mask layout
        for mask_layout in tqdm(self.mask_layouts, desc='Adding chip copy labels', bar_format=default_bar_format):

            labels_cell = mask_layout.layout.create_cell("ChipLabels")
            mask_layout.top_cell.insert(pya.DCellInstArray(labels_cell.cell_index(), pya.DTrans(pya.DVector(0, 0))))

            if mask_layout not in submask_layouts:
                mask_layout.insert_chip_copy_labels(labels_cell)
                # remove "$1" or similar unnecessary postfix from cell name
                mask_layout.top_cell.name = f"{mask_layout.name}"

        # populate used_chips with chips which exist in some mask_layout
        for chip_name, cell in self.chips_map_legend.items():
            for mask_layout in self.mask_layouts:
                # pylint: disable=use-a-generator
                if any([chip_name in row for row in mask_layout.chips_map]):
                # pylint: enable=use-a-generator
                    self.used_chips[chip_name] = cell
                    break

        # remove the guiding shapes, like chip boxes and waveguide paths
        if remove_guiding_shapes and self.layout.is_valid_layer(self.layout.guiding_shape_layer()):
            self.layout.delete_layer(self.layout.guiding_shape_layer())

        # remove any unnecessary top-level cells
        mask_layout_top_cells = [ml.top_cell for ml in self.mask_layouts]
        for cell in self.layout.top_cells():
            if cell not in mask_layout_top_cells + list(self.used_chips.values()):
                cell.prune_cell()

    def export(self, path, view):
        """Exports designs, bitmaps and documentation of this mask set.

        Assumes that self.build() has been called before.

        Args:
            path: path where the folder for this mask set is created
            view: KLayout view object

        """
        print("Exporting mask set...")
        export_mask_set(self, path, view)

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

    def _load_chip_into_mask(self, file_name, variant_name):
        """Loads a chip from file_name to self.layout and adds it into self.chips_map_legend["variant_name"]"""
        load_opts = pya.LoadLayoutOptions()
        load_opts.cell_conflict_resolution = pya.LoadLayoutOptions.CellConflictResolution.RenameCell
        self.layout.read(file_name, load_opts)
        self.chips_map_legend.update({variant_name: self.layout.top_cells()[-1]})
