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
import json
import os
from importlib import import_module
from math import pi

import logging

from kqcircuits.chips.chip import Chip
from kqcircuits.defaults import mask_bitmap_export_layers, chip_export_layer_clusters, default_layers, \
    default_mask_parameters
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_dc import FlipChipConnectorDc
from kqcircuits.klayout_view import resolve_default_layer_info
from kqcircuits.pya_resolver import pya
from kqcircuits.util.area import get_area_and_density
from kqcircuits.util.count_instances import count_instances_in_cell
from kqcircuits.util.geometry_helper import circle_polygon
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder
from kqcircuits.util.netlist_extraction import export_cell_netlist
from kqcircuits.util.export_helper import export_drc_report


def export_mask_set(mask_set, skip_extras=False):
    """Exports the designs, bitmap and documentation for the mask_set."""

    export_bitmaps(mask_set)
    export_designs(mask_set)
    if not skip_extras:
        export_docs(mask_set)


def export_designs(mask_set):
    """Exports .oas and .gds files of the mask_set."""
    # export mask layouts
    for mask_layout in mask_set.mask_layouts:
        export_masks_of_face(mask_set._mask_set_dir, mask_layout, mask_set)


def export_chip(chip_cell, chip_name, chip_dir, layout, export_drc, alt_netlists=None, skip_extras=False):
    """Exports a chip used in a maskset."""

    is_pcell = chip_cell.pcell_declaration() is not None

    # save data that is only available in pcell, not static cell
    if is_pcell:
        chip_class = type(chip_cell.pcell_declaration())
        chip_params = chip_cell.pcell_parameters_by_name()

    # export .oas file with pcells (requires exporting a cell one hierarchy level above chip pcell)
    dummy_cell = layout.create_cell(chip_name)
    dummy_cell.insert(pya.DCellInstArray(chip_cell.cell_index(), pya.DTrans()))
    _export_cell(chip_dir / f"{chip_name}_with_pcells.oas", dummy_cell, "all")
    dummy_cell.delete()
    static_cell = layout.cell(layout.convert_cell_to_static(chip_cell.cell_index()))

    # save the chip .oas file with all layers and only containing static cells
    save_opts = pya.SaveLayoutOptions()
    save_opts.format = "OASIS"
    save_opts.write_context_info = False  # to save all cells as static cells
    static_cell.write(str(chip_dir / f"{chip_name}.oas"), save_opts)

    if not skip_extras:
        # export netlist
        export_cell_netlist(static_cell, chip_dir / f"{chip_name}-netlist.json", chip_cell, alt_netlists)
        # calculate flip-chip bump count
        bump_count = count_instances_in_cell(chip_cell, FlipChipConnectorDc)
        # find layer areas and densities
        layer_areas_and_densities = {}
        for layer, area, density in zip(*get_area_and_density(static_cell)):
            if area != 0.0:
                layer_areas_and_densities[layer] = {"area": f"{area:.2f}", "density": f"{density * 100:.2f}"}

        # save auxiliary chip data into json-file
        chip_json = {
            "Chip class module": chip_class.__module__ if is_pcell else None,
            "Chip class name": chip_class.__name__ if is_pcell else None,
            "Chip parameters": chip_params if is_pcell else None,
            "Bump count": bump_count,
            "Layer areas and densities": layer_areas_and_densities
        }

        with open(chip_dir / (chip_name + ".json"), "w") as f:
            json.dump(chip_json, f, cls=GeometryJsonEncoder, sort_keys=True, indent=4)

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
                # an instance of the cell is inserted to a temporary cell with the correct transformation.
                # Was not able to get this working by just using static_cell.transform_into().
                temporary_cell = layout.create_cell(chip_name)
                temporary_cell.insert(pya.DCellInstArray(static_cell.cell_index(), default_mask_parameters[
                    layer_cluster.face_id]["chip_trans"]))
                layers_to_export = {name: layout.layer(default_layers[name]) for name in layer_cluster.all_layers()}
                path = chip_dir / f"{chip_name}-{cluster_name}.gds"
                _export_cell(path, temporary_cell, layers_to_export)
                temporary_cell.delete()

        # export drc report for the chip
        if export_drc:
            export_drc_report(chip_name, chip_dir)

    # delete the static cell which was only needed for export
    if static_cell.cell_index() != chip_cell.cell_index():
        layout.delete_cell_rec(static_cell.cell_index())


def export_masks_of_face(export_dir, mask_layout, mask_set):
    """ Exports masks for layers of a single face of a mask_set.

    Args:
        export_dir: directory for the face specific subdirectories
        mask_layout: MaskLayout object for the cell and face reference
        mask_set: MaskSet object for the name and version attributes to be included in the filename
    """
    subdir_name_for_face = get_mask_layout_full_name(mask_set, mask_layout)
    export_dir_for_face = _get_directory(export_dir / str(subdir_name_for_face))
    # export .oas file with all layers
    path = export_dir_for_face / f"{get_mask_layout_full_name(mask_set, mask_layout)}.oas"
    _export_cell(path, mask_layout.top_cell, "all")
    # export .oas files for individual optical lithography layers
    for layer_name in mask_layout.mask_export_layers:
        export_mask(export_dir_for_face, layer_name, mask_layout, mask_set)

    # Find area and density for the layers defined in mask_layout.mask_export_density_layers
    layer_infos = [resolve_default_layer_info(layer_name, mask_layout.face_id)
                   for layer_name in mask_layout.mask_export_density_layers]
    area_data = get_area_and_density(mask_layout.top_cell, layer_infos)

    wafer_area = pi * mask_layout.wafer_rad ** 2  # Use circular wafer area instead of rectangular bounding boxes
    layer_areas_and_densities = {name: {
        "area": round(area, 2),
        "density": round(area / wafer_area * 100, 2)
    } for name, area, _ in zip(*area_data)}

    mask_json = {
        "layer_areas_and_densities": layer_areas_and_densities,
    }
    with open(export_dir_for_face / (subdir_name_for_face + ".json"), "w") as f:
        json.dump(mask_json, f, cls=GeometryJsonEncoder, sort_keys=True, indent=4)


def export_mask(export_dir, layer_name, mask_layout, mask_set):
    """ Exports a mask from a single layer of a single face of a mask set.

    Args:
        export_dir: directory for the files
        layer_name: name of the layer exported as a mask. The following prefixes can be used to modify the export:
           * Prefix ``-``: invert the shapes on this layer
           * Prefix ``^``: mirror the layer (left-right)
        mask_layout: MaskLayout object for the cell and face reference
        mask_set: MaskSet object for the name and version attributes to be included in the filename
    """
    invert = False
    if layer_name.startswith('-'):
        layer_name = layer_name[1:]
        invert = True
    mirror = False
    if layer_name.startswith('^'):
        layer_name = layer_name[1:]
        mirror = True

    top_cell = mask_layout.top_cell
    layout = top_cell.layout()
    layer_info = resolve_default_layer_info(layer_name, mask_layout.face_id)
    layer = layout.layer(layer_info)
    tmp_layer = layout.layer()

    if invert:
        wafer = pya.Region(top_cell.begin_shapes_rec(layer)).merged()
        disc = pya.Region(circle_polygon(mask_layout.wafer_rad).to_itype(layout.dbu))
        layout.copy_layer(layer, tmp_layer)
        layout.clear_layer(layer)
        top_cell.shapes(layer).insert(wafer ^ disc)

    if mirror:
        wafer = pya.Region(top_cell.begin_shapes_rec(layer)).merged()
        layout.copy_layer(layer, tmp_layer)
        layout.clear_layer(layer)
        top_cell.shapes(layer).insert(wafer.transformed(pya.Trans(2, True, 0, 0)))

    layers_to_export = {layer_info.name: layer}
    path = export_dir / (get_mask_layout_full_name(mask_set, mask_layout) + f"-{layer_info.name}.oas")
    _export_cell(path, top_cell, layers_to_export)

    if invert:
        layout.clear_layer(layer)
        layout.copy_layer(tmp_layer, layer)
    layout.delete_layer(tmp_layer)


def export_docs(mask_set, filename="Mask_Documentation.md"):
    """Exports mask documentation containing mask layouts and parameters of all chips in the mask_set."""
    file_location = str(mask_set._mask_set_dir / filename)

    with open(file_location, "w+", encoding="utf-8") as f:
        f.write("# Mask Set Name: {}\n".format(mask_set.name))
        f.write("Version: {}\n".format(mask_set.version))

        for mask_layout in mask_set.mask_layouts:

            f.write("## Mask Layout {}:\n".format(mask_layout.face_id + mask_layout.extra_id))
            mask_layout_str = get_mask_layout_full_name(mask_set, mask_layout)
            f.write(f"![alt text]({mask_layout_str}/{mask_layout_str}-mask_graphical_rep.png)\n")

            f.write("### Number of Chips in Mask Layout {}\n".format(mask_layout.face_id + mask_layout.extra_id))

            f.write("| **Chip Name** | **Amount** |\n")
            f.write("| :--- | :--- |\n")
            for chip, amount in mask_layout.chip_counts.items():
                if amount > 0:
                    f.write("| **{}** | **{}** |\n".format(chip, amount))
            f.write("\n")

        f.write("___\n")

        f.write("## Chips\n")

        for name, cell in mask_set.used_chips.items():

            path = os.path.join("Chips", name, name)

            with open(mask_set._mask_set_dir / (path + ".json"), "r") as f2:
                chip_json = json.load(f2)

            f.write("### {} Chip\n".format(name))

            f.write(f"[{path}.oas]({path}.oas)\n\n")
            f.write(f"![{name} Chip Image]({path}.png)\n")
            f.write("\n")

            f.write("### Chip Parameters\n")
            f.write("| **Parameter** | **Value** |\n")
            f.write("| :--- | :--- |\n")

            cls_name = chip_json["Chip class name"]
            if cls_name is not None:  # otherwise it is a manually designed chip without class name or pcell parameters
                cls_mod = chip_json["Chip class module"]
                params_input = chip_json["Chip parameters"]
                cls = getattr(import_module(cls_mod), cls_name)
                # get defaults and update ones with input
                params = cls().pcell_params_by_name()
                params.update(params_input)
                params_schema = cls.get_schema()
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
            bump_count = chip_json["Bump count"]
            if bump_count > 0:
                f.write(f"| **Total bump count** | {bump_count} |\n")
            f.write("\n")

            # layer area and density
            f.write("#### Layer area and density\n")
            f.write("| **Layer** | **Total area (µm^2)** | **Density (%)** |\n")
            f.write("| :--- | :--- | :--- |\n")
            for layer, area_and_density in chip_json["Layer areas and densities"].items():
                f.write(f"| {layer} | {area_and_density['area']} | {area_and_density['density']} |\n")
            f.write("\n")

            f.write("___\n")

        f.write("## Links\n")
        for mask_layout in mask_set.mask_layouts:
            mask_layout_str = get_mask_layout_full_name(mask_set, mask_layout)
            mask_layout_path = mask_set._mask_set_dir / mask_layout_str

            f.write("### Mask Files:\n")
            for file_name in os.listdir(mask_layout_path):
                if file_name.endswith(".oas"):
                    f.write(" + [{}]({})\n".format(file_name, os.path.join(mask_layout_str, file_name)))
            f.write("\n")

            f.write("### Mask Images:\n")
            for file_name in os.listdir(mask_layout_path):
                if file_name.endswith(".png"):
                    f.write("+ [{}]({})\n".format(file_name, os.path.join(mask_layout_str, file_name)))

        f.close()


def export_bitmaps(mask_set, spec_layers=mask_bitmap_export_layers):
    """Exports bitmaps for the mask_set."""
    # pylint: disable=dangerous-default-value

    # export bitmaps for mask layouts
    for mask_layout in mask_set.mask_layouts:
        mask_layout_dir_name = get_mask_layout_full_name(mask_set, mask_layout)
        mask_layout_dir = _get_directory(mask_set._mask_set_dir / str(mask_layout_dir_name))
        filename = get_mask_layout_full_name(mask_set, mask_layout)
        view = mask_set.view
        if view:
            view.focus(mask_layout.top_cell)
            view.export_all_layers_bitmap(mask_layout_dir, mask_layout.top_cell, filename=filename)
            view.export_layers_bitmaps(mask_layout_dir, mask_layout.top_cell, filename=filename,
                                       layers_set=spec_layers, face_id=mask_layout.face_id)
    # export bitmaps for chips
    chips_dir = _get_directory(mask_set._mask_set_dir / "Chips")
    for name, cell in mask_set.used_chips.items():
        chip_dir = _get_directory(chips_dir / name)
        if view:
            view.export_all_layers_bitmap(chip_dir, cell, filename=name)
    if view:
        view.focus(mask_set.mask_layouts[0].top_cell)


def _export_cell(path, cell=None, layers_to_export=None):
    if cell is None:
        error_text = "Cannot export nil cell."
        error = ValueError(error_text)
        logging.exception(error_text, exc_info=error)
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
            layer_info = layout.layer_infos()[layer]
            svopt.add_layer(layer, layer_info)
        svopt.write_context_info = False
        layout.write(str(path), svopt)


def _get_directory(directory):
    if not os.path.exists(str(directory)):
        os.mkdir(str(directory))
    return directory


def get_mask_layout_full_name(mask_set, mask_layout):
    return f"{mask_set.name}_v{mask_set.version}-{mask_layout.face_id}{mask_layout.extra_id}"
