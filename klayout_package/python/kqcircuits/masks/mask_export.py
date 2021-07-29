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

"""Functions for exporting mask sets."""

import os
import subprocess

from autologging import logged, traced
from tqdm import tqdm

from kqcircuits.chips.chip import Chip
from kqcircuits.defaults import mask_bitmap_export_layers, chip_export_layer_clusters, default_layers, \
    default_mask_parameters, default_drc_runset, default_bar_format, SCRIPTS_PATH
from kqcircuits.elements.f2f_connectors.flip_chip_connectors.flip_chip_connector_dc import FlipChipConnectorDc
from kqcircuits.klayout_view import KLayoutView, resolve_default_layer_info
from kqcircuits.pya_resolver import pya
from kqcircuits.util.netlist_extraction import export_cell_netlist


@traced
@logged
def export(mask_set, path, view, export_drc):
    """Exports the designs, bitmap and documentation for the mask_set."""

    mask_set_dir = _get_directory(path/str("{}_v{}".format(mask_set.name, mask_set.version)))
    export_bitmaps(mask_set, mask_set_dir, view)
    export_designs(mask_set, mask_set_dir)
    export_docs(mask_set, mask_set_dir)
    if export_drc:
        export_drc_reports(mask_set, mask_set_dir)


@traced
@logged
def export_designs(mask_set, export_dir):
    """Exports .oas and .gds files of the mask_set."""
    layout = mask_set.layout

    # export mask layouts
    for mask_layout in mask_set.mask_layouts:
        export_masks_of_face(export_dir, mask_layout, mask_set)

    # export chips
    for chip_name, cell in tqdm(mask_set.used_chips.items(), desc='Exporting chips', bar_format=default_bar_format):
        export_chip(cell, chip_name, export_dir, layout, mask_set)


def export_chip(cell, chip_name, export_dir, layout, mask_set):
    """Exports a chip used in a maskset."""
    chip_dir = _get_directory(export_dir / "Chips" / chip_name)
    # it seems like the full hierarchy of the chip is exported only if it is converted to static
    # TODO this seems like a bug - check and report
    static_cell = layout.cell(layout.convert_cell_to_static(cell.cell_index()))
    # export .oas file with all layers
    path = chip_dir / "{}.oas".format(chip_name)
    _export_cell(path, static_cell, "all")
    # export .gds files for EBL or laser writer
    for cluster_name, layer_cluster in chip_export_layer_clusters.items():
        # If the chip has no shapes in the main layers of the layer cluster, should not export the chip with
        # that layer cluster.
        export_layer_cluster = False
        for layer_name in layer_cluster.main_layers:
            shapes_iter = static_cell.begin_shapes_rec(layout.layer(default_layers[layer_name]))
            if not shapes_iter.at_end():
                export_layer_cluster = True
                break
        if export_layer_cluster:
            # To transform the exported layer cluster chip correctly (e.g. mirroring for top chip),
            # an instance of the static_cell is inserted to a temporary cell with the correct transformation.
            # Was not able to get this working by just using static_cell.transform_into().
            temporary_cell = layout.create_cell(chip_name)
            temporary_cell.insert(pya.DCellInstArray(static_cell.cell_index(), default_mask_parameters[
                layer_cluster.face_id]["chip_trans"]))
            layers_to_export = {name: layout.layer(default_layers[name]) for name in layer_cluster.all_layers()}
            path = chip_dir / "{} {}.gds".format(chip_name, cluster_name)
            _export_cell(path, temporary_cell, layers_to_export)
            temporary_cell.delete()
    mask_set.layout.prune_cell(static_cell.cell_index(), -1)
    # export netlist
    path = chip_dir / "{}-netlist.json".format(chip_name)
    export_cell_netlist(cell, path)


def export_masks_of_face(export_dir, mask_layout, mask_set):
    """ Exports masks for layers of a single face of a mask_set.

    Args:
        export_dir: directory for the face specific subdirectories
        mask_layout: MaskLayout object for the cell and face reference
        mask_set: MaskSet object for the name and version attributes to be included in the filename
    """
    subdir_name_for_face = _get_mask_layout_full_name(mask_set, mask_layout)
    export_dir_for_face = _get_directory(export_dir / str(subdir_name_for_face))
    # export .oas file with all layers
    path = export_dir_for_face / f"{_get_mask_layout_full_name(mask_set, mask_layout)}.oas"
    _export_cell(path, mask_layout.top_cell, "all")
    # export .oas files for individual optical lithography layers
    for layer_name in mask_layout.mask_export_layers:
        export_mask(export_dir_for_face, layer_name, mask_layout, mask_set)


def export_mask(export_dir, layer_name, mask_layout, mask_set):
    """ Exports a mask from a single layer of a single face of a mask set.

    Args:
        export_dir: directory for the files
        layer_name: name of the layer exported as a mask
        mask_layout: MaskLayout object for the cell and face reference
        mask_set: MaskSet object for the name and version attributes to be included in the filename
    """
    layout = mask_layout.top_cell.layout()
    layer_info = resolve_default_layer_info(layer_name, mask_layout.face_id)
    layers_to_export = {layer_info.name: layout.layer(layer_info)}
    path = export_dir / "{}_v{} {}.oas".format(mask_set.name, mask_set.version, layer_info.name)
    _export_cell(path, mask_layout.top_cell, layers_to_export)


@traced
@logged
def export_docs(mask_set, export_dir, filename="Mask_Documentation.md"):
    """Exports mask documentation containing mask layouts and parameters of all chips in the mask_set."""

    file_location = str(os.path.join(str(export_dir), filename))

    with open(file_location, "w+", encoding="utf-8") as f:
        f.write("# Mask Set Name: {}\n".format(mask_set.name))
        f.write("Version: {}\n".format(mask_set.version))

        for mask_layout in mask_set.mask_layouts:

            f.write("## Mask Layout {}:\n".format(mask_layout.face_id + mask_layout.extra_id))
            mask_layout_str = mask_set.name + "_v" + str(mask_set.version)
            f.write("![alt text]({})\n".format(mask_layout_str + "%20" + mask_layout.face_id + mask_layout.extra_id
                                               + "/" + mask_layout_str + "%20mask_graphical_rep" + ".png"))

            f.write("### Number of Chips in Mask Layout {}\n".format(mask_layout.face_id + mask_layout.extra_id))

            chip_counts = {}

            def count_chips(mlayout, counts):

                for _, row_chips in enumerate(mlayout.chips_map):
                    for _, curr_name in enumerate(row_chips):
                        if curr_name == "---":
                            continue
                        if curr_name in counts:
                            counts[curr_name] += 1
                        else:
                            counts[curr_name] = 1

                for submask_layout, _ in mlayout.submasks:
                    count_chips(submask_layout, counts)

            count_chips(mask_layout, chip_counts)

            f.write("| **Chip Name** | **Amount** |\n")
            f.write("| :--- | :--- |\n")
            for chip, amount in chip_counts.items():
                f.write("| **{}** | **{}** |\n".format(chip, amount))
            f.write("\n")

        f.write("___\n")

        f.write("## Chips\n")

        for name, cell in mask_set.used_chips.items():
            f.write("### {} Chip\n".format(name))

            path = os.path.join("Chips", name, name)
            f.write(f"[{path}.oas]({path}.oas)\n\n")
            f.write(f"![{name} Chip Image]({path}.png)\n")
            f.write("\n")

            f.write("### Chip Parameters\n")
            f.write("| **Parameter** | **Value** |\n")
            f.write("| :--- | :--- |\n")
            params = cell.pcell_parameters_by_name()
            params_schema = type(cell.pcell_declaration()).get_schema()
            for param_name, param_declaration in params_schema.items():
                f.write("| **{}** | {} |\n".format(
                        param_declaration.description.replace("|", "&#124;"),
                        str(params[param_name])))
            f.write("\n")

            f.write("### Other Chip Information\n")
            f.write("| | |\n")
            f.write("| :--- | :--- |\n")
            # launcher assignments
            launcher_assignments = Chip.get_launcher_assignments(cell)
            if len(launcher_assignments) > 0:
                f.write("| **Launcher assignments** |")
                for key, value in launcher_assignments.items():
                    f.write("{} = {}, ".format(key, value))
                f.write("|\n")
            # flip-chip bump count
            bump_count = 0
            def count_bumps_in_inst(inst):
                nonlocal bump_count
                if isinstance(inst.pcell_declaration(), FlipChipConnectorDc):
                    bump_count += 1
                # cannot use just inst.cell due to klayout bug, see
                # https://www.klayout.de/forum/discussion/1191
                inst_cell = inst.layout().cell(inst.cell_index)
                for child_inst in inst_cell.each_inst():
                    count_bumps_in_inst(child_inst)
            for inst in cell.each_inst():
                count_bumps_in_inst(inst)
            if bump_count > 0:
                f.write(f"| **Total bump count** | {bump_count} |\n")

            f.write("\n")

            f.write("___\n")

        f.write("## Links\n")
        for mask_layout in mask_set.mask_layouts:
            mask_layout_str = _get_mask_layout_full_name(mask_set, mask_layout)
            mask_layout_path = os.path.join(str(export_dir), mask_layout_str)

            f.write("### Mask Files:\n")
            for file_name in os.listdir(mask_layout_path):
                if file_name.endswith(".oas"):
                    # the spaces are replaced by "%20" to make links to filenames with spaces work
                    f.write(" + [{}]({})\n".format(file_name,
                                                   os.path.join(mask_layout_str, file_name).replace(" ", "%20")))
            f.write("\n")

            f.write("### Mask Images:\n")
            for file_name in os.listdir(mask_layout_path):
                if file_name.endswith(".png"):
                    # the spaces are replaced by "%20" to make links to filenames with spaces work
                    f.write("+ [{}]({})\n".format(file_name,
                                                  os.path.join(mask_layout_str, file_name).replace(" ", "%20")))

        f.close()


@traced
@logged
def export_bitmaps(mask_set, export_dir, view, spec_layers=mask_bitmap_export_layers):
    """Exports bitmaps for the mask_set."""
    # pylint: disable=dangerous-default-value
    if view is None or not isinstance(view, KLayoutView):
        error_text = "Cannot export bitmap of mask with invalid or nil view."
        error = ValueError(error_text)
        export_bitmaps.__log.exception(error_text, exc_info=error)
        raise error
    # export bitmaps for mask layouts
    for mask_layout in mask_set.mask_layouts:
        mask_layout_dir_name = _get_mask_layout_full_name(mask_set, mask_layout)
        mask_layout_dir = _get_directory(export_dir/str(mask_layout_dir_name))
        filename = "{}_v{}".format(mask_set.name, mask_set.version)
        view.focus(mask_layout.top_cell)
        view.export_all_layers_bitmap(mask_layout_dir, mask_layout.top_cell, filename=filename,
                                      face_id=mask_layout.face_id)
        view.export_layers_bitmaps(mask_layout_dir, mask_layout.top_cell, filename=filename,
                                   layers_set=spec_layers, face_id=mask_layout.face_id)
    # export bitmaps for chips
    chips_dir = _get_directory(export_dir/"Chips")
    for name, cell in mask_set.used_chips.items():
        chip_dir = _get_directory(chips_dir/name)
        view.export_all_layers_bitmap(chip_dir, cell, filename=name)
    view.focus(mask_set.mask_layouts[0].top_cell)


@traced
@logged
def export_drc_reports(mask_set, export_dir):
    """Exports KLayout DRC report files for the mask_set."""

    if os.name == "nt":
        klayout_executable = os.path.join(os.getenv("APPDATA"), "KLayout", "klayout_app.exe")
    else:
        klayout_executable = "klayout"

    drc_runset_path = os.path.join(SCRIPTS_PATH, "drc", default_drc_runset)

    def export_drc_report(name, subpath):
        input_file = os.path.join(export_dir, subpath, f"{name}.oas")
        output_file = os.path.join(export_dir, subpath, f"{name}_drc_report.lyrdb")
        export_drc_reports._log.info("Exporting DRC report to %s", output_file)
        try:
            subprocess.run([klayout_executable, "-b",
                            "-rm", drc_runset_path,
                            "-rd", f"input={input_file}",
                            "-rd", f"output={output_file}"
                            ], check=True)
        except subprocess.CalledProcessError as e:
            export_drc_reports._log.error(e.output)

    # drc report for each chip
    for name in tqdm(mask_set.used_chips, desc='Exporting DRC reports for chips', bar_format=default_bar_format):
        chip_path = os.path.join("Chips", name)
        export_drc_report(name, chip_path)

    # drc report for each mask_layout
    # for mask_layout in mask_set.mask_layouts:
    #     name = _get_mask_layout_full_name(mask_set, mask_layout)
    #     export_drc_report(name, name)


def _export_cell(path, cell=None, layers_to_export=None):
    if cell is None:
        error_text = "Cannot export nil cell."
        error = ValueError(error_text)
        _export_cell._log.exception(error_text, exc_info=error)
        raise error
    layout = cell.layout()
    if (layers_to_export is None) or (layers_to_export == ""):
        layers_to_export = {}

    svopt = pya.SaveLayoutOptions()
    svopt.set_format_from_filename(str(path))

    if layers_to_export == "all":
        svopt.clear_cells()
        svopt.select_all_layers()
        svopt.add_cell(cell.cell_index())
        layout.write(str(path), svopt)
    else:
        items = layers_to_export.items()
        svopt.deselect_all_layers()
        svopt.clear_cells()
        svopt.add_cell(cell.cell_index())
        for _, layer in items:
            layer_info = cell.layout().layer_infos()[layer]
            svopt.add_layer(layer, layer_info)
        svopt.write_context_info = False
        layout.write(str(path), svopt)


def _get_directory(directory):
    if not os.path.exists(str(directory)):
        os.mkdir(str(directory))
    return directory


def _get_mask_layout_full_name(mask_set, mask_layout):
    return f"{mask_set.name}_v{mask_set.version} {mask_layout.face_id}{mask_layout.extra_id}"
