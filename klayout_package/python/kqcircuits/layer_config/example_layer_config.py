# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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


# An example layer config file, compatible with most KQC chips.

from kqcircuits.pya_resolver import pya

default_layers = {}
# face 1 layers
default_layers["1_Nb_gap"] = pya.LayerInfo(0, 0, "1 Nb_gap")
default_layers["1_Nb_gap_avoidance"] = pya.LayerInfo(1, 0, "1 Nb_gap_avoidance")
default_layers["1_Nb_gap_addition"] = pya.LayerInfo(2, 0, "1 Nb_gap_addition")
default_layers["1_Al_1"] = pya.LayerInfo(3, 0, "1 Al_1")
default_layers["1_Al_2"] = pya.LayerInfo(4, 0, "1 Al_2")
default_layers["1_SIS_junction"] = pya.LayerInfo(5, 0, "1 SIS_junction")
default_layers["1_SIS_shadow"] = pya.LayerInfo(6, 0, "1 SIS_shadow")
default_layers["1_underbump"] = pya.LayerInfo(7, 0, "1 underbump")
default_layers["1_new_layer"] = pya.LayerInfo(9, 2, "1 new_layer")  # layer that is not used by KQC elements
default_layers["1_ports"] = pya.LayerInfo(10, 1, "1 ports")
default_layers["1_wg_path"] = pya.LayerInfo(11, 1, "1 wg_path")
# face 2 layers
default_layers["2_Nb_gap"] = pya.LayerInfo(30, 0, "2 Nb_gap")
default_layers["2_Nb_gap_avoidance"] = pya.LayerInfo(31, 0, "2 Nb_gap_avoidance")
default_layers["2_Nb_gap_addition"] = pya.LayerInfo(32, 0, "2 Nb_gap_addition")
default_layers["2_Al_1"] = pya.LayerInfo(33, 0, "2 Al_1")
default_layers["2_Al_2"] = pya.LayerInfo(34, 0, "2 Al_2")
default_layers["2_SIS_junction"] = pya.LayerInfo(35, 0, "2 SIS_junction")
default_layers["2_SIS_shadow"] = pya.LayerInfo(36, 0, "2 SIS_shadow")
default_layers["2_underbump"] = pya.LayerInfo(37, 0, "2 underbump")
default_layers["2_new_layer"] = pya.LayerInfo(39, 2, "2 new_layer")  # layer that is not used by KQC elements
default_layers["2_ports"] = pya.LayerInfo(40, 1, "2 ports")
default_layers["2_wg_path"] = pya.LayerInfo(41, 1, "2 wg_path")
# other layers
default_layers["refpoints"] = pya.LayerInfo(100, 1, "refpoints")
default_layers["waveguide_length"] = pya.LayerInfo(101, 1, "wg_length")
default_layers["annotations"] = pya.LayerInfo(102, 1, "annotations")
default_layers["instance_names"] = pya.LayerInfo(103, 1, "instance_names")


default_faces = {}
default_faces["1"] = {
    "id": "1",
    "base_metal_gap_wo_grid": default_layers["1_Nb_gap"],
    "base_metal_gap_for_EBL": default_layers["1_Nb_gap"],  # same layer can be used for different "face-layers"
    "ground_grid_avoidance": default_layers["1_Nb_gap_avoidance"],
    "base_metal_addition": default_layers["1_Nb_gap_addition"],
    "airbridge_pads": default_layers["1_Al_1"],
    "airbridge_flyover": default_layers["1_Al_2"],
    "SIS_junction": default_layers["1_SIS_junction"],
    "SIS_shadow": default_layers["1_SIS_shadow"],
    "underbump_metallization": default_layers["1_underbump"],
    "ports": default_layers["1_ports"],
    "waveguide_path": default_layers["1_wg_path"],
    "new_layer": default_layers["1_new_layer"],
}
default_faces["2"] = {
    "id": "2",
    "base_metal_gap_wo_grid": default_layers["2_Nb_gap"],
    "base_metal_gap_for_EBL": default_layers["2_Nb_gap"],
    "ground_grid_avoidance": default_layers["2_Nb_gap_avoidance"],
    "base_metal_addition": default_layers["2_Nb_gap_addition"],
    "airbridge_pads": default_layers["2_Al_1"],
    "airbridge_flyover": default_layers["2_Al_2"],
    "SIS_junction": default_layers["2_SIS_junction"],
    "SIS_shadow": default_layers["2_SIS_shadow"],
    "underbump_metallization": default_layers["2_underbump"],
    "ports": default_layers["2_ports"],
    "waveguide_path": default_layers["2_wg_path"],
    "new_layer": default_layers["2_new_layer"],
}

default_face_id = "1"
default_mask_export_layers = None
default_layers_to_mask = None
default_covered_region_excluded_layers = None
mask_bitmap_export_layers = None
all_layers_bitmap_hide_layers = None
chip_export_layer_clusters = None
default_path_length_layers = [
    "1_wg_path",
    "2_wg_path",
    "waveguide_length"
]
default_mask_parameters = {
    "1": {
        "dice_width": 200,
        "text_margin": 100,
    },
    "2": {
        "dice_width": 140,
        "text_margin": 100,
    },
}
default_layer_props = None
default_chip_label_face_prefixes = None
default_parameter_values = {
    "Element": {"face_ids": ["1", "2"]},
}
