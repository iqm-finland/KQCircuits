# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import os
from autologging import logged, traced

from kqcircuits.pya_resolver import pya
from kqcircuits.klayout_view import KLayoutView, resolve_default_layer_info
from kqcircuits.chips.chip import Chip
from kqcircuits.defaults import mask_bitmap_export_layers, chip_export_layer_clusters, default_layers, \
    default_mask_export_layers, default_mask_parameters

"""Functions for exporting mask sets."""


@traced
@logged
def export(mask_set, path, view):
    """Exports the designs, bitmap and documentation for the mask_set."""

    mask_set_dir = _get_directory(path/str("{}_v{}".format(mask_set.name, mask_set.version)))
    export_bitmaps(mask_set, mask_set_dir, view)
    export_designs(mask_set, mask_set_dir)
    export_docs(mask_set, mask_set_dir)


@traced
@logged
def export_designs(mask_set, export_dir):
    """Exports .oas and .gds files of the mask_set."""
    layout = mask_set.layout

    if mask_set.mask_export_layers:
        mask_export_layers = mask_set.mask_export_layers
    else:
        mask_export_layers = default_mask_export_layers

    # export mask layouts
    for mask_layout in mask_set.mask_layouts:
        mask_layout_dir_name = "{}_v{} {}".format(mask_set.name, mask_set.version, mask_layout.face_id)
        mask_layout_dir = _get_directory(export_dir / str(mask_layout_dir_name))
        # export .oas file with all layers
        path = mask_layout_dir / "{}_v{} {}.oas".format(mask_set.name, mask_set.version,
                                                        mask_layout.face_id)
        _export_cell(path, mask_layout.top_cell, "all")
        # export .oas files for individual optical lithography layers
        for name in mask_export_layers:
            layer_info = resolve_default_layer_info(name, mask_layout.face_id)
            layers_to_export = {layer_info.name: layout.layer(layer_info)}
            path = mask_layout_dir/"{}_v{} {}.oas".format(mask_set.name, mask_set.version,
                                                          layer_info.name)
            _export_cell(path, mask_layout.top_cell, layers_to_export)
    # export chips
    for chip_name, cell in mask_set.used_chips.items():
        chip_dir = _get_directory(export_dir/"Chips"/chip_name)
        # it seems like the full hierarchy of the chip is exported only if it is converted to static
        static_cell = layout.cell(layout.convert_cell_to_static(cell.cell_index()))
        # export .oas file with all layers
        path = chip_dir/"{}.oas".format(chip_name)
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
                path = chip_dir/"{} {}.gds".format(chip_name, cluster_name)
                _export_cell(path, temporary_cell, layers_to_export)
                temporary_cell.delete()
        mask_set.layout.prune_cell(static_cell.cell_index(), -1)


@traced
@logged
def export_docs(mask_set, export_dir, filename="Mask_Documentation.md"):
    """Exports mask documentation containing mask layouts and parameters of all chips in the mask_set."""

    file_location = str(os.path.join(str(export_dir), filename))

    with open(file_location, "w+", encoding="utf-8") as f:
        f.write("# Mask Set Name: {}\n".format(mask_set.name))
        f.write("Version: {}\n".format(mask_set.version))

        for mask_layout in mask_set.mask_layouts:

            f.write("## Mask Layout {}:\n".format(mask_layout.face_id))
            mask_layout_str = mask_set.name + "_v" + str(mask_set.version)
            f.write("![alt text]({})\n".format(mask_layout_str + "%20" + mask_layout.face_id + "/" +
                                               mask_layout_str + "%20mask%20graphical%20rep" + ".png"))

            f.write("### Number of Chips in Mask Layout {}\n".format(mask_layout.face_id))

            counts = {}

            for row in range(0, len(mask_layout.chips_map)):
                for element in range(0, len(mask_layout.chips_map[row])):
                    curr_name = mask_layout.chips_map[row][element]
                    if curr_name == "---":
                        continue
                    if curr_name in counts:
                        counts[curr_name] += 1
                    else:
                        counts[curr_name] = 1

            f.write("| **Chip Name** | **Amount** |\n")
            f.write("| :--- | :--- |\n")
            for chip, amount in counts.items():
                f.write("| **{}** | **{}** |\n".format(chip, amount))
            f.write("\n")

        f.write("___\n")

        f.write("## Chips\n")

        for name, cell in mask_set.used_chips.items():
            f.write("### {} Chip\n".format(name))

            path = os.path.join("Chips", name, name)
            f.write("[{}.oas]({}.oas)\n\n".format(path, path))
            f.write("![{} Chip Image]({}.png)\n".format(name, path))
            f.write("\n")

            f.write("### Chip Parameters\n")
            f.write("| **Parameter** | **Value** |\n")
            f.write("| :--- | :--- |\n")
            params = cell.pcell_parameters_by_name()
            params_schema = cell.pcell_declaration().__class__.get_schema()
            for param_name, param_declaration in params_schema.items():
                f.write("| **{}** | {} |\n".format(
                        param_declaration["description"].replace("|", "&#124;"),
                        str(params[param_name])))
            launcher_assignments = Chip.get_launcher_assignments(cell)
            if len(launcher_assignments) > 0:
                f.write("| **Launcher assignments** |")
                for key, value in launcher_assignments.items():
                    f.write("{} = {}, ".format(key, value))
                f.write("|\n")
            f.write("\n")

            f.write("___\n")

        f.write("## Links\n")
        for mask_layout in mask_set.mask_layouts:
            mask_layout_str = mask_set.name + "_v" + str(mask_set.version) + " " + mask_layout.face_id
            mask_layout_path = os.path.join(str(export_dir), mask_layout_str)

            f.write("### Mask Files:\n")
            for filename in os.listdir(mask_layout_path):
                if filename.endswith(".oas"):
                    # the spaces are replaced by "%20" to make links to filenames with spaces work
                    f.write(" + [{}]({})\n".format(filename,
                                                   os.path.join(mask_layout_str, filename).replace(" ", "%20")))
            f.write("\n")

            f.write("### Mask Images:\n")
            for filename in os.listdir(mask_layout_path):
                if filename.endswith(".png"):
                    # the spaces are replaced by "%20" to make links to filenames with spaces work
                    f.write("+ [{}]({})\n".format(filename,
                                                  os.path.join(mask_layout_str, filename).replace(" ", "%20")))

        f.close()


@traced
@logged
def export_bitmaps(mask_set, export_dir, view, spec_layers=mask_bitmap_export_layers):
    """Exports bitmaps for the mask_set."""
    if view is None or not isinstance(view, KLayoutView):
        error_text = "Cannot export bitmap of mask with invalid or nil view."
        error = ValueError(error_text)
        export_bitmaps.__log.exception(error_text, exc_info=error)
        raise error
    # export bitmaps for mask layouts
    for mask_layout in mask_set.mask_layouts:
        mask_layout_dir_name = "{}_v{} {}".format(mask_set.name, mask_set.version, mask_layout.face_id)
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


def _export_cell(path, cell=None, layers_to_export={}):
    if cell is None:
        error_text = "Cannot export nil cell."
        error = ValueError(error_text)
        _export_cell._log.exception(error_text, exc_info=error)
        raise error
    layout = cell.layout()
    if layers_to_export == "":
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
        for layer_name, layer in items:
            layer_info = cell.layout().layer_infos()[layer]
            svopt.add_layer(layer, layer_info)
        svopt.write_context_info = False
        layout.write(str(path), svopt)


def _get_directory(directory):
    if not os.path.exists(str(directory)):
        os.mkdir(str(directory))
    return directory
