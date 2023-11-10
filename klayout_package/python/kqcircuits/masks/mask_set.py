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
import logging
from sys import argv
from time import perf_counter
from inspect import isclass
from multiprocessing import Pool
from pathlib import Path

from tqdm import tqdm

from kqcircuits.chips.chip import Chip
from kqcircuits.masks.multi_face_mask_layout import MultiFaceMaskLayout
from kqcircuits.util.log_router import route_log
from kqcircuits.pya_resolver import pya, is_standalone_session
from kqcircuits.defaults import default_bar_format, TMP_PATH, default_face_id
from kqcircuits.masks.mask_export import export_chip, export_mask_set
from kqcircuits.masks.mask_layout import MaskLayout
from kqcircuits.klayout_view import KLayoutView


class MaskSet:
    """Class representing a set of masks for different chip faces.

    A mask set consists of one or more MaskLayouts, each of which is for a certain face.

    To create a mask, add mask layouts to the mask set using add_mask_layout() and add chips to these mask layouts using
    add_chip(). These functions also export some files for each chip. Then call build() to create the
    cell hierarchy of the entire mask, and finally export mask files by calling export().

    Chips are created in parallel in separate processes but the user may choose to use a ``-d`` switch on
    the command line for debugging with a single process. It is also possible to manually limit the number of
    concurrently used CPUs for resource management purposes with the ``-c 4`` switch (to 4 in this example).

    Example:
        mask = MaskSet(...)
        mask.add_mask_layout(...)
        mask.add_mask_layout(...)
        mask.add_chip(...)
        mask.build()
        mask.export()

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
        export_path: The folder for mask files will be generated under this. TMP_PATH by default.
    """

    def __init__(self, view=None, name="MaskSet", version=1, with_grid=False, export_drc=False,
                 mask_export_layers=None, export_path=TMP_PATH):

        self._time = {"INIT": perf_counter(), "ADD_CHIPS": 0,  "BUILD": 0, 'EXPORT': 0, 'END': 0}

        if view is None:
            self.view = KLayoutView()
        self.layout = self.view.layout

        self.name = name
        self.version = version
        self.with_grid = with_grid
        self.export_drc = export_drc
        self.chips_map_legend = {}
        self.mask_layouts = []
        self.mask_export_layers = mask_export_layers if mask_export_layers is not None else []
        self.used_chips = {}
        self._extra_params = {}
        self._mask_set_dir = Path(export_path)/f"{name}_v{version}"

        self._mask_set_dir.mkdir(parents=True, exist_ok=True)

        self._extra_params["enable_debug"] = '-d' in argv
        self._single_process = self._extra_params["enable_debug"] or not is_standalone_session()

        self._extra_params["mock_chips"] = '-m' in argv
        self._extra_params["skip_extras"] = '-s' in argv

        self._cpu_override = 0
        if '-c' in argv and len(argv) > argv.index('-c') + 1:
            self._cpu_override = int(argv[argv.index('-c') + 1])

    def add_mask_layout(self, chips_map, face_id=default_face_id, mask_layout_type=MaskLayout, **kwargs):
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

    def add_multi_face_mask_layout(self, face_ids, chips_map=None, extra_face_params=None, mask_layout_type=MaskLayout,
                                   **kwargs):
        """Create a multi face mask layout, which can be used to make masks with matching chip maps on multiple faces.

        A ``MaskLayout`` is created of each face in ``face_ids``. By default, the individual mask layouts all have
        identical parameters, but parameters can be overwritten for a single face id through ``extra_face_params``.

        By default, ``bbox_face_ids`` is set to ``face_ids`` for all mask layouts.

        Args:
            face_ids: list of face ids to include
            chips_map: Chips map to use, or None to use an empty chips map.
            extra_face_params: a dictionary of ``{face_id: extra_kwargs}``, where ``extra_kwargs`` is a dictionary of
                 keyword arguments to apply only to the mask layout for ``face_id``.
            mask_layout_type: optional subclass of MaskLayout to use
            kwargs: any keyword arguments are passed to all containing mask layouts.

        Returns: a ``MultiFaceMaskLayout`` instance
        """
        if ("mask_export_layers" not in kwargs) and self.mask_export_layers:
            kwargs["mask_export_layers"] = self.mask_export_layers

        mfml = MultiFaceMaskLayout(self.layout, self.name, self.version, self.with_grid, face_ids,
                                   chips_map, extra_face_params, mask_layout_type, **kwargs)
        for face_id in mfml.face_ids:
            self.mask_layouts.append(mfml.mask_layouts[face_id])
        return mfml

    def add_chip(self, chips, variant_name=None, cpus=None, **parameters):
        """Adds a chip (or list of chips) with parameters to self.chips_map_legend and exports the files for each chip.

        Note the complex polymorphism used here: ``chips`` is either a single chip class or a list of ``(chip, variant,
        parameters)`` tuples. In the latter case the rest of the arguments (except ``cpus``) are ignored. Also,
        ``chips`` (or the individual chip part of tuples) may be a simple file name to load a static .oas file instead.

        The chip's parameters dictionary may also contain an ``alt_netlists`` dictionary to specify alternative ways of
        generating netlists. See ``export_cell_netlist()`` or the ``quick_demo.py`` mask for further information.

        Args:
            chip: A chip class. Or a list of tuples, like ``[(QualityFactor, "QDG", parameters),...]``,
                  parameters are optional.
            variant_name: Name for specific variant, the same as in the mask layout.
            cpus: Number of parallel processes to use for chip generation. By default uses ``os.cpu_count()``
                  or the number of chips, whichever is smaller.
            **parameters: Any parameters passed to the a single chip PCell.
        """
        self._time['ADD_CHIPS'] = perf_counter()

        if not isinstance(chips, list):  # only one chip
            cpus = 1
            chips = [(chips, variant_name, parameters)]

        if cpus is None:
            cpus = min(len(chips), os.cpu_count())
        if self._cpu_override > 0:
            cpus = self._cpu_override

        # Pool.map() needs all arguments packed into a single list
        xargs = (self.name, self.with_grid, self._mask_set_dir, self.export_drc, self._extra_params)
        chip_args = ((chip, xargs) for chip in chips)

        file_names = []
        if cpus == 1 or self._single_process:
            file_names += map(self._create_chip, chip_args)
        else:
            print(f"Building chip variants in parallel using {cpus} processes...")
            with Pool(cpus) as pool:
                file_names += pool.map(self._create_chip, chip_args)

        # import chip cells exported by the parallel processes into the mask
        for variant, file_name in tqdm(file_names, desc='Add chips into mask', bar_format=default_bar_format):
            self._load_chip_into_mask(file_name, variant)

    @staticmethod
    def _create_chip(chip_arg):
        """Create chip, possibly in a separate process."""

        chip, xargs = chip_arg
        name, with_grid, _mask_set_dir, export_drc, _extra_params = xargs
        chip_class, variant_name, *chip_params = chip
        chip_params = chip_params[0] if chip_params else {}
        alt_netlists = chip_params.pop("alt_netlists", None)

        chip_path = _mask_set_dir/"Chips"/f"{variant_name}"
        chip_path.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(level=logging.DEBUG, force=True)  # this level is NOT actually used
        route_log(filename=chip_path/f"{variant_name}.log", stdout=_extra_params["enable_debug"])

        mock_chips = _extra_params['mock_chips']
        skip_extras = _extra_params['skip_extras']

        view = KLayoutView()
        layout = view.layout

        if isclass(chip_class):
            params = {
                'name_chip': variant_name,
                'name_mask': name,
                'with_grid': with_grid,
                'merge_base_metal_gap': True,
                'display_name': variant_name,
                'name_copy': None,
            }
            if mock_chips:
                mock_params = chip_class().pcell_params_by_name(Chip, **params)
                if chip_params:
                    # Pass through parameters only if they exist in Chip
                    mock_params.update({k: v for k, v in chip_params.items() if k in mock_params})
                mock_params.update({
                    'with_grid': False,
                    'with_gnd_bumps': False,
                    'with_gnd_tsvs': False,
                })
                cell = Chip.create(layout, **mock_params)
            else:
                if chip_params:
                    params.update(chip_params)
                cell = chip_class.create(layout, **params)
        else:  # it's a file name, load it
            load_opts = pya.LoadLayoutOptions()
            if hasattr(pya.LoadLayoutOptions, "CellConflictResolution"):
                load_opts.cell_conflict_resolution = pya.LoadLayoutOptions.CellConflictResolution.RenameCell
            layout.read(chip_class, load_opts)
            cell = layout.top_cells()[-1]

        export_chip(cell, variant_name, chip_path, layout, export_drc, alt_netlists, skip_extras)
        view.close()

        return variant_name, str(chip_path / f"{variant_name}.oas")

    def build(self, remove_guiding_shapes=True):
        """Builds the mask set.

        Creates cells for the mask based on self.mask_layouts and self.chips_map_legend. Optionally removes
        guiding shapes from the layout. Populates self.used_chips with the chips used in the mask layouts.

        Args:
            remove_guiding_shapes (Boolean): determines if the guiding shapes are removed

        """
        self._time['BUILD'] = perf_counter()
        # build mask layouts (without chip copy labels)
        for mask_layout in self.mask_layouts:
            # include face_id in mask_layout.name only for multi-face masks
            if len(self.mask_layouts) > 1:
                mask_layout.name += "-" + mask_layout.face_id
            mask_layout.build(self.chips_map_legend)

        chip_copy_label_layers = [
            "base_metal_gap",
            "base_metal_gap_wo_grid",
            "base_metal_gap_for_EBL"
        ]

        # Insert submask cells to different cell instances, so that these cells can have different chip labels even if
        # the original submask cells are identical. Also copy the MaskLayout objects of identical submasks into separate
        # MaskLayout objects with different `extra_id` so that mask export can use that information.
        mask_layouts_to_remove = set()
        submask_layouts_with_exported_layers = set()
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
                # Make sure that layers are only exported once if there are multiple identical submasks
                if sm_layout in submask_layouts_with_exported_layers:
                    # only export layers where chip copy labels are since they are different even for identical submasks
                    new_sm_layout.mask_export_layers = \
                        [layer for layer in chip_copy_label_layers if layer in new_sm_layout.mask_export_layers]
                else:
                    submask_layouts_with_exported_layers.add(sm_layout)
        self.mask_layouts = submask_layouts + [ml for ml in self.mask_layouts if ml not in mask_layouts_to_remove]

        # add chip copy labels for every mask layout
        for mask_layout in tqdm(self.mask_layouts, desc='Adding chip copy labels', bar_format=default_bar_format):

            labels_cell = mask_layout.layout.create_cell("ChipLabels")
            mask_layout.top_cell.insert(pya.DCellInstArray(labels_cell.cell_index(), pya.DTrans(pya.DVector(0, 0))))

            if mask_layout not in submask_layouts:
                mask_layout.insert_chip_copy_labels(labels_cell, chip_copy_label_layers)
                # remove "$1" or similar unnecessary postfix from cell name
                mask_layout.top_cell.name = f"{mask_layout.name}"

        # populate used_chips with chips which exist in some mask_layout
        for chip_name, cell in self.chips_map_legend.items():
            for mask_layout in self.mask_layouts:
                if mask_layout.chip_counts[chip_name]:
                    self.used_chips[chip_name] = cell
                    break

        # remove the guiding shapes, like chip boxes and waveguide paths
        if remove_guiding_shapes and self.layout.is_valid_layer(self.layout.guiding_shape_layer()):
            self.layout.delete_layer(self.layout.guiding_shape_layer())

    def export(self):
        """Exports designs, bitmaps and documentation of this mask set.

        Assumes that self.build() has been called before.
        """
        self._time['EXPORT'] = perf_counter()

        print("Exporting mask set...")
        export_mask_set(self, self._extra_params["skip_extras"])

        self._time['END'] = perf_counter()

        def tdiff(a, b):  # get elapsed time from "a" to "b"
            return f'{self._time[b] - self._time[a]:.1f}s' if self._time[a] and self._time[b] else 'n/a'

        print(f"Runtime: {tdiff('INIT', 'END')} (add chips: {tdiff('ADD_CHIPS', 'BUILD')}, "
              f"build: {tdiff('BUILD', 'EXPORT')}, export: {tdiff('EXPORT', 'END')})")

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
