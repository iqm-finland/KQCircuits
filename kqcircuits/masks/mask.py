# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import os
import abc
import math
from autologging import logged, traced

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.marker import Marker
from kqcircuits.elements.chip_frame import produce_label
from kqcircuits.klayout_view import KLayoutView
from kqcircuits.defaults import default_layers, lay_id_set, default_brand
from kqcircuits.util.export_helper import export_cell
from kqcircuits.util import merge


@logged
@traced
class Mask:
    """Abstract base class for masks.

    To create a new mask, create a class that derives from this class. Call super().__init__() with the correct
    parameters in __init__, and define self.mask_layout and self.mask_map_legend in the build method of your mask class.

    Attributes:
        name: Name of the mask
        version: Mask version
        with_grid: Boolean determining if ground grid is generated
        mask_map_legend: Dictionary where keys are chip names, values are chip cells
        mask_layout: List of lists (2D-array) of strings, each string is a chip name (or --- for no chip)
        wafer_rad_um: Wafer radius in micrometers
        wafer_center: Wafer center as a pya.DVector (um)
        dice_width: Dicing width for the mask (um)
        mask_extra_name: Name of the mask extra cell
        layout: pya.Layout for this mask
        top_cell: Top cell of the layout
        text_margin: Text margin for the mask

    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, layout, name="Mask", version=1, with_grid=False):
        super().__init__()
        if layout is None or not isinstance(layout, pya.Layout):
            error = ValueError("Cannot create mask with invalid or nil layout.")
            self.__log.exception(exc_info=error)
            raise error
        else:
            self.layout = layout

        self.name = name
        self.version = version
        self.with_grid = with_grid
        self.top_cell = self.layout.create_cell("Mask {}".format(self.name))  # A new cell into the layout
        self.mask_map_legend = None
        self.mask_layout = []
        self.wafer_rad_um = 6 / 2. * 25400.
        self.wafer_center = pya.DVector(76200 - 1200, -76200 + 1200)
        self.dice_width = 200
        self.mask_extra_name = "MaskExtra"

        self.build()

        self.text_margin = self.__get_text_margin()
        self.__generate()

    @abc.abstractmethod
    def build(self):
        """
        Build mask.

        Override this in the derived class for a specific mask and set the instance variables there.
        At least self.mask_layout and self.mask_map_legend should be set there. Other instance variables
        can be overridden as needed.
        """
        return

    @staticmethod
    def mask_layout_from_box_map(box_map, mask_map):
        """Returns the mask_layout created from box_map and mask_map.

        Given NxN box map and MxM mask map, creates mask layout of size MNxMN. So each element of mask map is "replaced"
        by a box in the box map. Assumes that box_map and mask_map are square.

        Args:
            box_map: dictionary where keys are strings identifying the box type, and values are 2D arrays (lists of
                lists) where each element is a string identifying the pixel type

            mask_map: 2D array (list of lists), where each element is a string identifying the box type
        """
        num_box_map_rows = len(list(box_map.values())[0])
        num_mask_map_rows = len(mask_map)
        num_pixel_rows = num_box_map_rows*num_mask_map_rows

        mask_layout = [["" for _ in range(num_pixel_rows)] for _ in range(num_pixel_rows)]
        for (k, box_row) in enumerate(mask_map):
            for (l, box) in enumerate(box_row):
                if box in box_map:
                    for (i, row) in enumerate(box_map[box]):
                        for (j, slot) in enumerate(row):
                            mask_layout[k*num_box_map_rows + i][l*num_box_map_rows + j] = slot

        return mask_layout

    def export(self, path, view):
        """Exports the designs, bitmap and documentation for this mask."""
        folder_dir = self.export_bitmap(path, view)
        self.export_designs(path)
        self.export_docs(folder_dir)

    def export_designs(self, path):
        """Exports .oas files of the mask."""
        folder_dir = path / str("{}_v{}".format(self.name, self.version))
        if not os.path.exists(str(folder_dir)):
            os.mkdir(str(folder_dir))
        export_cell(folder_dir, self.top_cell, cell_name=self.name, cell_version=self.version)
        pixel_dir = folder_dir / "Pixels"
        if not os.path.exists(str(pixel_dir)):
            os.mkdir(str(pixel_dir))
        for name, cell in self.mask_map_legend.items():
            filename = name
            export_cell(pixel_dir, cell, cell_name=filename, cell_version=self.version,
                        layers_to_export="no_sing_layer")

    def export_docs(self, export_dir, filename="Mask_Documentation.md"):
        """Exports mask documentation containing mask layout and parameters of all the pixels."""
        file_location = str(os.path.join(str(export_dir), filename))

        with open(file_location, "w+") as f:
            f.write("# Mask Name : {} \n\n".format(self.name))
            f.write("## Version : {} \n\n".format(self.version))
            f.write("### Image : \n\n")
            f.write("![alt text]({}) \n\n".format(
                str(export_dir) + "/" + "Mask_" + self.name + "_layer_13_v" + str(self.version) + ".png"))
            f.write("___ \n\n")
            f.write("### Amount Of Each Pixel In The Mask : \n\n")

            counts = {}
            for row in range(0, len(self.mask_layout)):
                for element in range(0, len(self.mask_layout[row])):
                    curr_name = self.mask_layout[row][element]
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
            for name, cell in self.mask_map_legend.items():
                parameters = []
                parameters = cell.pcell_parameters_by_name()
                pcells[name] = parameters

            for c_name, params in pcells.items():
                f.write(" + #### Pixel {} : \n\n".format(c_name))
                for p_name, value in params.items():
                    f.write("\t + **{}** : {} \n\n".format(p_name, value))

            f.write("___ \n\n")

            f.write("### Images and Links : \n\n")

            pix_image_loc = str(export_dir) + "/" + "Pixels"
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
            for filename in os.listdir(str(export_dir)):
                if filename.endswith(".oas"):
                    mask_os_path = str(os.path.join(str(export_dir), filename))
                    f.write("\t + ##### [{}]({}) \n\n".format(filename, mask_os_path))
                    continue
            f.write(" + ##### Mask Images : \n\n")
            for filename in os.listdir(str(export_dir)):
                if filename.endswith(".png"):
                    mask_des_path = str(os.path.join(str(export_dir), filename))
                    f.write("\t + ##### [{}]({}) \n\n".format(filename, mask_des_path))

            f.close()

    def export_bitmap(self, path, view, spec_layers=lay_id_set):
        """Exports all layers of the mask as a bitmap"""
        if view is None or not isinstance(view, KLayoutView):
            error = ValueError("Cannot export bitmap of mask with invalid or nil view.")
            self.__log.exception(exc_info=error)
            raise error
        # ensure export root folder
        if not os.path.exists(str(path)):
            os.mkdir(str(path))

        # ensure mask folder
        folder_dir = path / str("{}_v{}".format(self.name, self.version))
        if not os.path.exists(str(folder_dir)):
            os.mkdir(str(folder_dir))

        view.focus(self.top_cell)
        view.export_all_layers_bitmap(folder_dir, self.top_cell, cell_name=self.name, cell_version=self.version)
        view.export_layers_bitmaps(folder_dir, self.top_cell, cell_version=self.version, layers_set=spec_layers)
        pixel_dir = folder_dir / "Pixels"
        if not os.path.exists(str(pixel_dir)):
            os.mkdir(str(pixel_dir))
        for name, cell in self.mask_map_legend.items():
            view.export_all_layers_bitmap(pixel_dir, cell, cell_name=name, cell_version=self.version)
        view.focus(self.top_cell)

        return folder_dir

    # ********************************************************************************
    # PRIVATE METHODS
    # ********************************************************************************

    def __generate(self):
        step_ver = pya.DVector(0, -1e4)
        step_hor = pya.DVector(1e4, 0)

        label_cell, region_covered = self.__mask_create_geometry()
        self.top_cell.insert(pya.DCellInstArray(label_cell.cell_index(), pya.DTrans(pya.DVector(0, 0))))

        for (i, row) in enumerate(self.mask_layout):
            for (j, slot) in enumerate(row):
                position = step_ver * (i + 1) + step_hor * j
                pos_index_name = chr(ord("A") + i) + ("{:02d}".format(j))
                added_pixel = self.__add_pixel(label_cell, region_covered, step_ver, step_hor, position,
                                               pos_index_name, slot)
                if not added_pixel:
                    self.mask_layout[i][j] = "---"

        maskextra_cell = self.layout.create_cell(self.mask_extra_name)  # A new cell into the layout

        self.__mask_create_covered_region(maskextra_cell, region_covered)

        self.layout.convert_cell_to_static(self.top_cell.cell_index())
        for name, cell in self.mask_map_legend.items():
            self.layout.convert_cell_to_static(cell.cell_index())

        merge.merge_layers(self.layout, list(self.mask_map_legend.values()) + [maskextra_cell, label_cell])

        return maskextra_cell, label_cell

    def __mask_create_geometry(self):
        label_cell = self.layout.create_cell("ChipLabels")  # A new cell into the layout
        clip = -14.5e4
        region_covered = pya.Region(
            (pya.DPolygon([
                pya.DPoint(
                    self.wafer_center.x + math.cos(a / 32 * math.pi) * self.wafer_rad_um,
                    self.wafer_center.y + max(math.sin(a / 32 * math.pi) * self.wafer_rad_um, clip)
                )
                for a in range(0, 64 + 1)
            ])).to_itype(self.layout.dbu))

        return label_cell, region_covered

    def __add_pixel(self, label_cell, region_covered, step_ver, step_hor, position, pos_index_name, slot):
        """Returns true if a pixel was added, false otherwise"""
        # center of the pixel 1 cm from the mask edge
        if (position - step_ver * 0.5 + step_hor * 0.5 - self.wafer_center).length() - self.wafer_rad_um < -1e4:
            if slot in self.mask_map_legend.keys():
                v0 = -pya.DVector(self.mask_map_legend[slot].dbbox().p1)
                inst = self.top_cell.insert(
                    pya.DCellInstArray(self.mask_map_legend[slot].cell_index(), pya.DTrans(position + v0)))
                if inst.is_pcell():
                    self.__produce_label_wrap(pos_index_name, position, label_cell)
                else:
                    self.__produce_label_wrap(pos_index_name, position, label_cell,
                                              chip_type_name=self.mask_map_legend[slot].basic_name(),
                                              brand_name=default_brand)
                region_covered -= pya.Region(inst.bbox())
                # add graphical representation
                pixel_name = self.__get_pixel_name(self.mask_map_legend[slot])
                self.__add_graphical_representation_layer(pixel_name, position, v0)
                return True
        return False

    def __mask_create_covered_region(self, maskextra_cell, region_covered):
        dbu = self.layout.dbu
        layers_dict = {
            "b base metal gap wo grid": "-1.",
            "b airbridge pads": "-2.",
            "b airbridge flyover": "-3."
        }
        for layer, postfix in layers_dict.items():
            cell_mask_name = self.layout.create_cell("TEXT", "Basic", {
                "layer": default_layers[layer],
                "text": default_brand + "-" + self.name + "v" + str(self.version) + postfix,
                "mag": 5000.0
            })
            cell_mask_name_h = cell_mask_name.dbbox().height()
            cell_mask_name_w = cell_mask_name.dbbox().width()
            inst = maskextra_cell.insert(pya.DCellInstArray(cell_mask_name.cell_index(),
                                                            pya.DTrans(self.wafer_center.x - cell_mask_name_w / 2,
                                                                       -0.6e4 - cell_mask_name_h / 2)))
            region_covered -= pya.Region(inst.bbox()).extents(1e3 / dbu)

        cell_mask_outline = self.layout.create_cell("CIRCLE", "Basic", {
            "l": default_layers["b base metal gap wo grid"],
            "r": 1.e9,
            "n": 64
        })

        circle = pya.DTrans(self.wafer_center) * pya.DPath(
            [pya.DPoint(math.cos(a / 32 * math.pi) * self.wafer_rad_um, math.sin(a / 32 * math.pi) * self.wafer_rad_um)
             for a in range(0, 64 + 1)], 100)
        maskextra_cell.shapes(self.layout.layer(default_layers["annotations 2"])).insert(circle)

        cell_marker = Marker.create_cell(self.layout, {"window": True})
        x_min = 0
        y_min = -15e4
        x_max = 15e4
        y_max = 0

        marker_transes = [pya.DTrans(x_min + 25e3, y_min + 25e3) * pya.DTrans.R180,
                          pya.DTrans(x_max - 25e3, y_min + 25e3) * pya.DTrans.R270,
                          pya.DTrans(x_min + 25e3, y_max - 25e3) * pya.DTrans.R90,
                          pya.DTrans(x_max - 25e3, y_max - 25e3) * pya.DTrans.R0]

        for trans in marker_transes:
            inst = maskextra_cell.insert(pya.DCellInstArray(cell_marker.cell_index(), trans))
            region_covered -= pya.Region(inst.bbox()).extents(1e3 / dbu)

        maskextra_cell.shapes(self.layout.layer(default_layers["b base metal gap wo grid"])).insert(region_covered)
        maskextra_cell.shapes(self.layout.layer(default_layers["b airbridge pads"])).insert(region_covered)
        maskextra_cell.shapes(self.layout.layer(default_layers["b airbridge flyover"])).insert(region_covered)
        maskextra_cell.shapes(self.layout.layer(default_layers["mask graphical rep"])).insert(region_covered)

        self.top_cell.insert(pya.DCellInstArray(maskextra_cell.cell_index(), pya.DTrans()))

    def __get_pixel_name(self, search_cell):
        for pixel_name, cell in self.mask_map_legend.items():
            if search_cell == cell:
                return pixel_name

    def __add_graphical_representation_layer(self, pixel_name, v, v0):
        grp_text = self.layout.create_cell("TEXT", "Basic", {
            "layer": default_layers["mask graphical rep"],
            "text": pixel_name,
            "mag": 5000,
        })
        self.top_cell.insert(pya.DCellInstArray(grp_text.cell_index(), pya.DTrans(v + v0 + pya.DVector(750, 750))))

    def __produce_label_wrap(self, pos_index_name, loc, label_cell, chip_type_name=None, brand_name=None):

        produce_label(label_cell, pos_index_name, loc + pya.DVector(1e4, 0), "bottomright",
                      self.dice_width, self.text_margin, default_layers["b base metal gap wo grid"],
                      default_layers["b ground grid avoidance"])
        if chip_type_name is not None:
            produce_label(label_cell, chip_type_name, loc + pya.DVector(1e4, 1e4), "topright", self.dice_width,
                          self.text_margin, default_layers["b base metal gap wo grid"],
                          default_layers["b ground grid avoidance"])
        if brand_name is not None:
            produce_label(label_cell, brand_name, loc + pya.DVector(0, 0), "bottomleft", self.dice_width,
                          self.text_margin, default_layers["b base metal gap wo grid"],
                          default_layers["b ground grid avoidance"])

    def __get_text_margin(self):
        for value in self.mask_map_legend.values():
            if value.pcell_parameter("text_margin") is not None:
                return value.pcell_parameter("text_margin")