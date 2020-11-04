# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

"""Configuration file for KQCircuits.

Defines values for things such as default layers, paths, and layers used for different exports.
"""

import os
from pathlib import Path

from kqcircuits.pya_resolver import pya
from kqcircuits.layer_cluster import LayerCluster

# project paths
SRC_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
ROOT_PATH = SRC_PATH.parent
TMP_PATH = ROOT_PATH.joinpath("tmp")
TMP_PATH.mkdir(exist_ok=True)

# printed to corners of all chips and top of all masks
# could be for example "IQM" or "A!"
default_brand = "IQM"

# human readable dictionary
# layer name as key, tuple of layer and tech as value
default_layers_dict = {
   ###############################
    # Bottom-chip related layers [Layer 10-39]
    ###############################

    # Metal etching layers
    "b base metal gap": (10, 1),  # merged etching layer with grid (layers 11 & 13) that defines microscopic structures such as waveguides, lauchers
    "b base metal gap wo grid": (11, 1),  # etching layer without grid
    "b base metal addition": (12, 0),  # Features subtracted from layer 11, only used during design
    "b ground grid": (13, 0),  # A subset of structures combined into layer 10 (e.g. ground plane perforations)
    "b ground grid avoidance": (14, 0),  # Occupy the area where there should be no grids, only used during the design.
    "b base metal gap for EBL": (15, 0),  # Features of layer 11 that are needed for EBL

    # SQUID layer
    "b SIS junction": (17, 2),  # Josephson junction
    "b SIS shadow": (18, 2),  # Ghost layer required for Josephson junction

    # Airbridges
    "b airbridge pads": (28, 3),  #
    "b airbridge flyover": (29, 3),  #

    # 3D integration layers
    "b underbump metallization": (32, 4),  # flip-chip bonding
    "b indium bump": (33, 4),  # flip-chip bonding
    "b through silicon via": (34, 4),  # TSV

    # netlist
    "b ports": (39, 0),  # Considered conductive in the netlist extraction

    ###############################
    # Top-chip related layers [Layer 40-90]
    ###############################
    # Metal etching (Nb or TiN) layers for front face (facing towards bottom chip)
    "t base metal gap": (40, 1),
    # merged etching layer with grid (layers 41 & 43) that defines microscopic structures such as waveguides, launchers
    "t base metal gap wo grid": (41, 1),  # etching layer without grid
    "t base metal addition": (42, 0),  # Features subtracted from layer 41, only used during design
    "t ground grid": (43, 0),  # A subset of structures combined into layer 40 (e.g. ground plane perforations)
    "t ground grid avoidance": (44, 0),  # Occupy the area where there should be no grids, only used during the design.
    "t base metal gap for EBL": (45, 0),  # Features of layer 41 that are needed for EBL

    # SQUID layer
    "t SIS junction": (47, 2),  # Josephson junction
    "t SIS shadow": (48, 2),  # Ghost layer required for Josephson junction

    # Airbridge layers -- potentially obsolete
    "t airbridge pads": (58, 3),  #
    "t airbridge flyover": (59, 3),  #

    # 3D integration layers
    "t underbump metallization": (62, 4),  # flip-chip bonding
    "t indium bump": (63, 4),  # flip-chip bonding
    "t through silicon via": (64, 4),  # TSV

    # netlist
    "t ports": (69, 0),  # Considered conductive in the netlist extraction

    # Metal etching (Nb or TiN) layers for back face (facing towards the sample holder lid)
    "c metal gap": (70, 1),
    # merged etching layer with grid  (layers 71 & 73) that defines microscopic structures such as waveguides, launchers
    "c base metal gap wo grid": (71, 1),  # etching layer without grid
    "c base metal addition": (72, 0),  # Features subtracted from layer 71 , only used during the design.
    "c ground grid": (73, 0),  # A subset of structures combined into layer 70 (e.g. ground plane perforations)
    "c ground grid avoidance": (74, 0),
    # Occupy the area where there should be no grids, only used during the design.

    ###############################
    # Aux layers [Layer 85-99]
    ###############################
    "annotations": (85, 0),
    "annotations 2": (86, 0),
    "instance names": (87, 0),

    "mask graphical rep": (89, 0),
    "b simulation signal": (90, 0),
    "b simulation ground": (91, 0),
    "t simulation signal": (92, 0),
    "t simulation ground": (93, 0),
    "b simulation airbridge flyover": (94, 0),
    "b simulation airbridge pads": (95, 0),

}

# pya layer information
default_layers = {}
for name, index in default_layers_dict.items():
    default_layers[name] = pya.LayerInfo(index[0], index[1], name)

default_circuit_params = {
    "a": 10,  # Width of center conductor [μm]
    "b": 6,  # Width of gap [μm]
    "r": 100,  # Turn radius [μm]
    "n": 64,  # Number of points on turns
}

gzip = False

output_formats_dict = {
    "OASIS": ".oas",
    "GDS2": ".gds",
}

# default output format and extension
default_output_format = "OASIS"
default_output_ext = output_formats_dict[default_output_format]

# default bitmap dimensions
default_png_dimensions = (1000, 1000)

# Layer names (without face prefix) for layers exported as individual .oas files during mask layout export.
default_mask_export_layers = [
    "base metal gap",
    "base metal gap wo grid",
    "airbridge pads",
    "airbridge flyover"
]

# Layer names (without face prefix) on which the covered region on wafer boundary, mask aligners,
# and mask IDs are exported. The indices appear in postfix in mask label
default_layers_to_mask = {
    "base metal gap wo grid": "1",
    "airbridge pads": "2",
    "airbridge flyover": "3"
}

# Layer names (without face prefix) for layers exported as bitmap files during full mask layout export (does not
# apply to individual pixels).
mask_bitmap_export_layers = [
    # "base metal gap wo grid",
    "mask graphical rep",
]

# Layers to hide when exporting a bitmap with "all" layers.
all_layers_bitmap_hide_layers = [
    default_layers["annotations"],
    default_layers["annotations 2"],
    default_layers["instance names"],
    default_layers["mask graphical rep"],
    default_layers["b base metal gap"],
    default_layers["b ground grid"],
    default_layers["b ground grid avoidance"],
    default_layers["t base metal gap"],
    default_layers["t ground grid"],
    default_layers["t ground grid avoidance"],
    default_layers["c metal gap"],
    default_layers["c ground grid"],
    default_layers["c ground grid avoidance"],
]

# Layer clusters used for exporting only certain layers together in the same file, when exporting individual chips
# during mask layout export.
# Dictionary with items "cluster name: LayerCluster".
chip_export_layer_clusters = {
    # b-face
    "SIS b": LayerCluster(["b SIS junction", "b SIS shadow"], ["b base metal gap for EBL"], "b"),
    "airbridges b": LayerCluster(["b airbridge pads", "b airbridge flyover"], ["b base metal gap wo grid"], "b"),
    # t-face
    "SIS t": LayerCluster(["t SIS junction", "t SIS shadow"], ["t base metal gap for EBL"], "t"),
    "airbridges t": LayerCluster(["t airbridge pads", "t airbridge flyover"], ["t base metal gap wo grid"], "t"),
}

default_face_b = {
    "id": "b",
    # Metal etching layers
    "base metal gap": default_layers["b base metal gap"],
    "base metal gap wo grid": default_layers["b base metal gap wo grid"],
    "base metal addition": default_layers["b base metal addition"],
    "ground grid": default_layers["b ground grid"],
    "ground grid avoidance": default_layers["b ground grid avoidance"],
    "base metal gap for EBL": default_layers["b base metal gap for EBL"],

    # SQUID layer
    "SIS junction": default_layers["b SIS junction"],
    "SIS shadow": default_layers["b SIS shadow"],

    # Airbridges
    "airbridge pads": default_layers["b airbridge pads"],
    "airbridge flyover": default_layers["b airbridge flyover"],

    # 3D integration layers
    "underbump metallization": default_layers["b underbump metallization"],
    "indium bump": default_layers["b indium bump"],
    "through silicon via": default_layers["b through silicon via"],

    # Simulation faces
    "simulation signal": default_layers["b simulation signal"],
    "simulation ground": default_layers["b simulation ground"],
    "simulation airbridge flyover": default_layers["b simulation airbridge flyover"],
    "simulation airbridge pads": default_layers["b simulation airbridge pads"],

    # Netlist
    "ports": default_layers["b ports"],
}

default_face_t = {
    "id": "t",
    # Metal etching layers
    "base metal gap": default_layers["t base metal gap"],
    "base metal gap wo grid": default_layers["t base metal gap wo grid"],
    "base metal addition": default_layers["t base metal addition"],
    "ground grid": default_layers["t ground grid"],
    "ground grid avoidance": default_layers["t ground grid avoidance"],
    "base metal gap for EBL": default_layers["t base metal gap for EBL"],

    # SQUID layer
    "SIS junction": default_layers["t SIS junction"],
    "SIS shadow": default_layers["t SIS shadow"],

    # Airbridges
    "airbridge pads": default_layers["t airbridge pads"],
    "airbridge flyover": default_layers["t airbridge flyover"],

    # 3D integration layers
    "underbump metallization": default_layers["t underbump metallization"],
    "indium bump": default_layers["t indium bump"],
    "through silicon via": default_layers["t through silicon via"],

    # Simulation faces
    "simulation signal": default_layers["t simulation signal"],
    "simulation ground": default_layers["t simulation ground"],

    # Netlist
    "ports": default_layers["t ports"],
}

default_face_c = {
    "id": "c",
    # Metal etching layers
    "base metal gap": default_layers["c metal gap"],
    "base metal gap wo grid": default_layers["c base metal gap wo grid"],
    "base metal addition": default_layers["c base metal addition"],
    "ground grid": default_layers["c ground grid"],
    "ground grid avoidance": default_layers["c ground grid avoidance"],
}

# default_faces[face_id] contains the face dictionary for the face determined by face_id.
#
# Each face dictionary should contain:
#   - key "id" with value face_id (string)
#   - for all the available layers in that face: key "Layer_name", value pya.LayerInfo object for that layer
#
default_faces = {
    "b": default_face_b,
    "t": default_face_t,
    "c": default_face_c,
}

# default mask parameters for each face
# dict of face_id: parameters
default_mask_parameters = {
    "b": {
        "wafer_rad": 76200,
        "wafer_center_offset": pya.DVector(-1200, 1200),
        "chip_size": 10000,
        "chip_box_offset": pya.DVector(0, 0),
        "chip_trans": pya.DTrans(),
        "dice_width": 200,
        "text_margin": 100,
        "mask_text_scale": 1.0,
        "mask_marker_offset": 50000,
        "mask_name_offset": 0.6e4,
    },
    "t": {
        "wafer_rad": 76200,
        "wafer_center_offset": pya.DVector(-2700, 2700),
        "chip_size": 7000,
        "chip_box_offset": pya.DVector(1500, 1500),
        "chip_trans": pya.DTrans(pya.DPoint(10000, 0)) * pya.DTrans().M90,
        "dice_width": 140,
        "text_margin": 100,
        "mask_text_scale": 0.7,
        "mask_marker_offset": 50000,
        "mask_name_offset": 0.38e4,
    },
    "c": {
        "wafer_rad": 76200,
        "wafer_center_offset": pya.DVector(-2700, 2700),
        "chip_size": 7000,
        "chip_box_offset": pya.DVector(1500, 1500),
        "chip_trans": pya.DTrans(pya.DPoint(10000, 0)) * pya.DTrans().M90,
        "dice_width": 140,
        "text_margin": 100,
        "mask_text_scale": 0.7,
        "mask_marker_offset": 50000,
        "mask_name_offset": 0.38e4,
    }
}
