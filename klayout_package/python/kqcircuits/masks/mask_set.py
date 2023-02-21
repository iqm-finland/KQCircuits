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
import subprocess
from time import perf_counter
from string import Template
from inspect import isclass
from multiprocessing.pool import ThreadPool
from pathlib import Path

from autologging import logged
from tqdm import tqdm

from kqcircuits.pya_resolver import pya, is_standalone_session, klayout_executable_command
from kqcircuits.defaults import default_bar_format, TMP_PATH, STARTUPINFO, default_face_id
from kqcircuits.masks.mask_export import export_chip, export_mask_set
from kqcircuits.masks.mask_layout import MaskLayout
from kqcircuits.klayout_view import KLayoutView


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
        self.template_imports = []
        self._thread_create_chip_parameters = {}
        self._mask_set_dir = Path(export_path)/f"{name}_v{version}"

        self._mask_set_dir.mkdir(parents=True, exist_ok=True)

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

    def load_cell_from_file(self, file_name):
        """Load GDS or OASIS cell from file.

        Load a cell (usually a chip) from the specified file.

        Args:
            file_name: name of the file (with path) to be loaded

        Returns:
            the loaded cell
        """
        load_opts = pya.LoadLayoutOptions()
        if hasattr(pya.LoadLayoutOptions, "CellConflictResolution"):
            load_opts.cell_conflict_resolution = pya.LoadLayoutOptions.CellConflictResolution.RenameCell
        self.layout.read(file_name, load_opts)
        return self.layout.top_cells()[-1]

    def add_chips(self, chips, threads=None):
        """Adds a list of chips with parameters to self.chips_map_legend and exports the files for each chip.

        Args:
            chips: List of tuples that ``add_chip`` uses. Parameters are optional.
                For example, ``(QualityFactor, "QDG", parameters)``.
            threads: Number of parallel threads to use for generation. By default uses ``os.cpu_count()`` threads.
                Uses subprocesses and consequently a lot of memory. In standalone python mode always uses 1 thread.

        Warning:
            It is advised to lower the thread number if your system has a lot of CPU cores but not a lot of memory.
            The same applies for exporting large and complex geometry.
        """
        self._time['ADD_CHIPS'] = perf_counter()

        if threads is None:
            threads = os.cpu_count()
        if threads is None or threads < 1 or is_standalone_session():
            threads = 1

        if threads == 1:
            for chip_class, variant_name, *params in tqdm(chips, desc='Building variants',
                                                          bar_format=default_bar_format):
                self.add_chip(chip_class, variant_name, **(params[0] if params else {}))
        else:
            print(f"Building chip variants in parallel using {threads} threads...")

            template = self._get_template()

            class ChipSubprocessException(Exception):
                def __init__(self, err, chip_variant):
                    super().__init__()
                    self.err = err
                    self.chip_variant = chip_variant
                def __str__(self):
                    return f'Building the {self.chip_variant} chip variant caused the following error:'\
                    f'{os.linesep}{self.err}'

            def _subprocess_worker(args):
                with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      startupinfo=STARTUPINFO) as proc:
                    _, errs = proc.communicate()
                    # Process has error return code, return error stream
                    if proc.returncode > 0:
                        return errs.decode('UTF-8')
                return None

            def _params_to_str(params):  # flatten a parameters dictionary to a string
                ps = ""
                for n, v in params.items():
                    if isinstance(v, str):
                        ps += f",{n}={repr(v)}"
                    elif isinstance(v, pya.DBox):
                        ps += f",{n}=pya.DBox({v.p1.x}, {v.p1.y}, {v.p2.x}, {v.p2.y})"
                    elif isinstance(v, pya.DVector):
                        ps += f",{n}=pya.DVector({v.x}, {v.y})"
                    elif isinstance(v, pya.DPoint):
                        ps += f",{n}=pya.DPoint({v.x}, {v.y})"
                    else:
                        ps += f",{n}={v}"
                return ps

            tp = ThreadPool(threads)
            file_names = []
            processes = {}
            for chip_class, variant_name, *param_list in chips:
                # create the script for generating this chip with the correct parameters and exporting the chip files
                params = {
                    'name_chip': variant_name,
                    'name_mask': self.name,
                    'with_grid': self.with_grid,
                    'merge_base_metal_gap': True,
                    }
                if param_list:
                    params.update(param_list[0])

                element_import = f'from {chip_class.__module__} import {chip_class.__name__}'
                create_element = f'cell = {chip_class.__name__}.create(layout {_params_to_str(params)})'
                chip_path = self._mask_set_dir/"Chips"/f"{variant_name}"
                chip_path.mkdir(parents=True, exist_ok=True)
                script_name = str(chip_path / f"{variant_name}.py")
                file_names.append((variant_name, str(chip_path / f"{variant_name}.oas"), script_name))

                substitution_parameters = {
                    'name_mask': self.name,
                    'chip_path': str(chip_path),
                    'variant_name': variant_name,
                    'chip_class': chip_class.__name__,
                    'element_import': element_import,
                    'create_element': create_element,
                    'export_drc': self.export_drc
                }
                substitution_parameters.update(self._thread_create_chip_parameters)
                result = template.substitute(**substitution_parameters)
                with open(script_name, "w") as f:
                    f.write(result)

                # launch klayout process that runs the created script
                try:  # pylint: disable=consider-using-with
                    processes[variant_name] = tp.apply_async(_subprocess_worker,
                                   ([klayout_executable_command(), "-e", "-z", "-nc", "-rm", script_name],)
                                   )
                except subprocess.CalledProcessError as e:
                    self.__log.error(e.output)

            # wait for processes to end
            tp.close()
            for variant_name, process in processes.items():
                process_error = process.get()
                if process_error is not None:
                    raise ChipSubprocessException(process_error, variant_name)
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

        chip_path = self._mask_set_dir/"Chips"/f"{variant_name}"
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
            "merge_base_metal_gap": True,
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
                # pylint: disable=use-a-generator
                if any([chip_name in row for row in mask_layout.chips_map]):
                # pylint: enable=use-a-generator
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
        export_mask_set(self)

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

    def _get_template(self):
        """Returns an updated template string."""

        temp = _CREATE_CHIP_TEMPLATE
        for i in self.template_imports:
            temp = temp.replace('#TEMPLATE_IMPORT#', i, 1)
        return Template(temp)


# Template for creating and exporting a chip during mask generation.
#
# This is used in _get_template() to create a template used in add_chips() to create chips in
# parallel. The "#TEMPLATE_IMPORT#" strings in it will be replaced by "template_imports" elements
# to update the template itself.

_CREATE_CHIP_TEMPLATE = """

import logging
import sys
import traceback
#TEMPLATE_IMPORT#
from pathlib import Path
from kqcircuits.masks.mask_export import export_chip
from kqcircuits.pya_resolver import pya
from kqcircuits.klayout_view import KLayoutView
from kqcircuits.util.log_router import route_log
${element_import}

try:
    logging.basicConfig(level=logging.DEBUG)  # this level is NOT actually used
    chip_path = Path(r"${chip_path}")
    route_log(filename=chip_path/"${variant_name}.log")

    view = KLayoutView()
    layout, top_cell = view.layout, view.top_cell

    # cell definition and arbitrary code here
    ${create_element}

    top_cell.insert(pya.DCellInstArray(cell.cell_index(), pya.DTrans()))

    # export chip files
    export_chip(cell, "${variant_name}", chip_path, layout, ${export_drc})

#TEMPLATE_IMPORT#

except Exception as err:
    print(traceback.format_exc(), file=sys.stderr)
    pya.Application.instance().exit(1)
pya.Application.instance().exit(0)

"""
