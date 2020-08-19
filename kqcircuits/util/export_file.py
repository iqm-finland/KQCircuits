import os
from pathlib import Path

from kqcircuits.pya_resolver import pya

from kqcircuits.defaults import default_layers, lay_id_set, default_output_format, default_output_ext, \
    default_png_dimensions, gzip


def export_mask_docs(mask_name, design_ver, mask_layout, mask_map_legend, folder_dir):
    filename = "Mask_Documentation.md"
    file_location = str(os.path.join(str(folder_dir), filename))

    with open(file_location, "w+") as f:
        f.write("# Mask Name : {} \n\n".format(mask_name))
        f.write("## Version : {} \n\n".format(design_ver))
        f.write("### Image : \n\n")
        f.write("![alt text]({}) \n\n".format(
            str(folder_dir) + "/" + "Mask_" + mask_name + "_layer_13_v" + str(design_ver) + ".png"))
        f.write("___ \n\n")
        f.write("### Amount Of Each Pixel In The Mask : \n\n")

        counts = {}
        for row in range(0, len(mask_layout)):
            for element in range(0, len(mask_layout[row])):
                curr_name = mask_layout[row][element]
                if curr_name in counts:
                    counts[curr_name] = counts[curr_name] + 1
                else:
                    counts[curr_name] = 1

        if "--" in counts:
            del counts["--"]

        f.write("| **Pixel Name** |")
        f.write(" **Amount** | \n")
        f.write("|:---:|:---:| \n")

        for pixel, amount in counts.items():
            f.write("| **{}** |".format(pixel))
            f.write(" **{}** | \n".format(amount))

        f.write("___ \n\n")
        f.write("### Parameters Used To Create Each Pixel : \n\n")

        pcells = {}
        for name, cell in mask_map_legend.items():
            parameters = []
            parameters = cell.pcell_parameters_by_name()
            pcells[name] = parameters

        for c_name, params in pcells.items():
            f.write(" + #### Pixel {} : \n\n".format(c_name))
            for p_name, value in params.items():
                f.write("\t + **{}** : {} \n\n".format(p_name, value))

        f.write("___ \n\n")

        f.write("### Images and Links : \n\n")

        pix_image_loc = str(folder_dir) + "/" + "Pixels"
        for filename in os.listdir(pix_image_loc):
            if filename.endswith(".png"):
                pix_image_path = str(os.path.join(pix_image_loc, filename))
                f.write("+ #### {} : \n\n".format(filename[:len(filename) - 7]))
                f.write("\t + ![alt text]({}) \n\n".format(pix_image_path))
                f.write("\t + ##### Link To The Pixel : [{}]({}) \n\n".format(filename[:len(filename) - 4] + ".oas",
                                                                              pix_image_path[
                                                                              :len(pix_image_path) - 4] + ".oas"))
                continue

        f.write("___ \n\n")

        f.write("### Mask Files : \n\n")
        f.write(" + ##### Mask Files : \n\n")
        for filename in os.listdir(str(folder_dir)):
            if filename.endswith(".oas"):
                mask_os_path = str(os.path.join(str(folder_dir), filename))
                f.write("\t + ##### [{}]({}) \n\n".format(filename, mask_os_path))
                continue
        f.write(" + ##### Mask Images : \n\n")
        for filename in os.listdir(str(folder_dir)):
            if filename.endswith(".png"):
                mask_des_path = str(os.path.join(str(folder_dir), filename))
                f.write("\t + ##### [{}]({}) \n\n".format(filename, mask_des_path))

        f.close()


def export_cell(path, layout, cell, cell_name='', layers_to_export='', cell_ver=1):
    if (layers_to_export == ''):
        layers_to_export = {
            "Merged b base metal gap wo grid": layout.layer(default_layers["b base metal gap"]),
            "Opt_lit_1": layout.layer(default_layers["b base metal gap wo grid"]),
            "Opt_lit_2": layout.layer(default_layers["b airbridge pads"]),
            "Opt_lit_3": layout.layer(default_layers["b airbridge flyover"])
        }

    elif (layers_to_export == 'no_sing_layer'):
        layers_to_export = {}

    if (cell_name == ''):
        cell_name = cell.name

    filename = "{}_v{}".format(cell_name, str(cell_ver))

    svopt = pya.SaveLayoutOptions()
    svopt.clear_cells()
    svopt.select_all_layers()
    svopt.add_cell(cell.cell_index())
    svopt.format = default_output_format
    file_ext = default_output_ext
    all_layers_file_name = path / "{}{}".format(filename, file_ext)

    layout.write(str(all_layers_file_name), gzip, svopt)

    layer_info = pya.LayerInfo()
    if bool(layers_to_export):
        items = layers_to_export.items()
        for layer_name, layer in items:
            svopt.deselect_all_layers()
            svopt.clear_cells()
            svopt.add_layer(layer, layer_info)
            svopt.add_cell(cell.cell_index())
            svopt.write_context_info = False
            spec_layer_file_name = path / "{}_{}{}".format(filename, layer_name, file_ext)
            layout.write(str(spec_layer_file_name), gzip, svopt)


# method that will export a file with the layers given
def export_bitmap(path, cell, layout, layout_view, cell_view, cell_name='', z_box=pya.DBox(0, 0, 0, 0),
                  layers_set=lay_id_set, cell_ver=1):
    cell_view.active().cell = layout.cell(cell.cell_index())
    layout_view.zoom_fit()  # Has to be done also before zoom_box

    if (cell_name == ''):
        cell_name = cell.name

    if z_box != pya.DBox(0, 0, 0, 0):
        layout_view.zoom_box(z_box)

        # custom_png_name = path / "{}.png".format(cell_name)
        # layout_view.save_image(str(custom_png_name), default_png_dimensions[0], default_png_dimensions[1])

    filename = "{}_v{}".format(cell_name, str(cell_ver))
    cell_png_name = path / "{}.png".format(filename)

    # first make all layers visible, then take a screenshot
    if (layers_set == 'all'):

        layers_to_hide = [
            default_layers["annotations"],
            default_layers["annotations 2"],
            default_layers["mask graphical rep"],
        ]

        for layer in layout_view.each_layer():
            layer.visible = True

            # hide unwanted annotations layers from the bitmap files
        for layer in layout_view.each_layer():
            for layer_to_hide in layers_to_hide:
                if layer.source_layer == layer_to_hide.layer and layer.source_datatype == layer_to_hide.datatype:
                    layer.visible = False
                    break

        layout_view.save_image(str(cell_png_name), default_png_dimensions[0], default_png_dimensions[1])
    # take screenshots of only specific layers
    else:
        # get the current visibility condition of the layers
        current_layer_visibility = []
        for layer in layout_view.each_layer():
            current_layer_visibility.append(layer.visible)

        # only show the wanted layers
        for layer in layout_view.each_layer():
            layer.visible = False
            for layer_to_show in layers_set:
                if layer.source_layer == layer_to_show.layer and layer.source_datatype == layer_to_show.datatype:
                    layer.visible = True
                    break

        layout_view.save_image(str(cell_png_name), default_png_dimensions[0], default_png_dimensions[1])

        # return the layer visibility to before screenshot state
        for i, layer in enumerate(layout_view.each_layer()):
            layer.visible = current_layer_visibility[i]


def export_layers_bitmaps(path, cell, layout, layout_view, cell_view, cell_name='', layers_set=lay_id_set, cell_ver=1):
    if (cell_name == ''):
        cell_name = cell.name
    for lay_id in range(len(layers_set)):
        layer_png_name = "{}_layer_{}".format(cell_name, layers_set[lay_id].layer)
        export_bitmap(path, cell, layout, layout_view, cell_view, cell_name=layer_png_name,
                      layers_set=[layers_set[lay_id]], cell_ver=cell_ver)


def export_all_layers_bitmap(path, cell, layout, layout_view, cell_view, cell_name='', cell_ver=1):
    if (cell_name == ''):
        cell_name = cell.name
    export_bitmap(path, cell, layout, layout_view, cell_view, cell_name=cell_name, layers_set='all', cell_ver=cell_ver)


def export_mask(path, top_cell, layout, layout_view, cell_view, mask_map_legend, mask_layout=None,
                mask_export_name='', mask_ver=1):
    if mask_layout is None:
        mask_layout = []
    folder_dir = export_mask_bitmap(path, top_cell, layout, layout_view, cell_view, mask_map_legend,
                                    mask_name=mask_export_name, mask_ver=mask_ver)
    export_mask_designs(path, top_cell, layout, mask_map_legend, mask_name=mask_export_name, mask_ver=mask_ver)

    export_mask_docs(mask_export_name, mask_ver, mask_layout, mask_map_legend, folder_dir)


def export_mask_designs(path, top_cell, layout, mask_map_legend, mask_name='', mask_ver=1):
    if (mask_name == ''):
        mask_name = top_cell.name
    folder_dir = path / str("{}_v{}".format(mask_name, mask_ver))
    if not os.path.exists(str(folder_dir)):
        os.mkdir(str(folder_dir))
    export_cell(folder_dir, layout, top_cell, cell_name=mask_name, cell_ver=mask_ver)
    file_dir = Path()
    pixel_dir = folder_dir / "Pixels"
    if not os.path.exists(str(pixel_dir)):
        os.mkdir(str(pixel_dir))
    for name, cell in mask_map_legend.items():
        filename = name
        export_cell(pixel_dir, layout, cell, cell_name=filename, layers_to_export="no_sing_layer", cell_ver=mask_ver)


def export_mask_bitmap(path, top_cell, layout, layout_view, cell_view, mask_map_legend, mask_name='',
                       spec_layers=lay_id_set, mask_ver=1):
    # ensure export root folder
    if not os.path.exists(str(path)):
        os.mkdir(str(path))

    # ensure mask folder
    if (mask_name == ''):
        mask_name = top_cell.name
    folder_dir = path / str("{}_v{}".format(mask_name, mask_ver))
    if not os.path.exists(str(folder_dir)):
        os.mkdir(str(folder_dir))

    export_all_layers_bitmap(folder_dir, top_cell, layout, layout_view, cell_view, cell_name=mask_name,
                             cell_ver=mask_ver)

    export_layers_bitmaps(folder_dir, top_cell, layout, layout_view, cell_view, layers_set=spec_layers,
                          cell_ver=mask_ver)
    file_dir = Path()
    pixel_dir = folder_dir / "Pixels"
    if not os.path.exists(str(pixel_dir)):
        os.mkdir(str(pixel_dir))
    for name, cell in mask_map_legend.items():
        export_all_layers_bitmap(pixel_dir, cell, layout, layout_view, cell_view, cell_name=name, cell_ver=mask_ver)

    return folder_dir
