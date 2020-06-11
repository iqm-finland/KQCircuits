# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import os
from pathlib import Path

from kqcircuits.pya_resolver import pya

# project paths
SRC_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
ROOT_PATH = SRC_PATH.parent
TMP_PATH = ROOT_PATH.joinpath("tmp")
TMP_PATH.mkdir(exist_ok=True)

# printed to corners of all chips and top of all masks
# could be for example "IQM" or "A!"
default_brand = "NOBRAND"

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

    # SQUID layer
    "b SIS junction": (17, 2),  # Josephson junction
    "b SIS shadow": (18, 2),  # Ghost layer required for Josephson junction

    # Low-pass filters for QCR
    "b filter dielectric": (22, 1),  # patterning dielectric filter (typically AlOx)
    "b filter metal": (23, 1),  # filter metal (typically Pd)

    # NIS junctions for QCR
    "b NIS junction": (24, 2),  # NIS junction
    "b NIS shadow": (25, 2),  # Ghost layer required for NIS junction

    # Airbridges
    "b airbridge pads": (28, 3),  #
    "b airbridge flyover": (29, 3),  #

    # 3D integration layers
    "b underbump metallization": (32, 4),  # flip-chip bonding
    "b indium bump": (33, 4),  # flip-chip bonding
    "b through silicon via": (34, 4),  # TSV

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

    # SQUID layer
    "t SIS junction": (47, 2),  # Josephson junction
    "t SIS shadow": (48, 2),  # Ghost layer required for Josephson junction

    # Low-pass filters for QCR
    "t filter dielectric": (52, 1),  # etching of dielectric layer
    "t filter metal": (53, 1),  # filter metal (typically Pd)

    # NIS junctions for QCR
    "t NIS junction": (54, 2),  # NIS junction
    "t NIS shadow": (55, 2),  # Ghost layer required for NIS junction

    # Airbridge layers -- potentially obsolete
    "t airbridge pads": (58, 3),  #
    "t airbridge flyover": (59, 3),  #

    # 3D integration layers
    "t underbump metallization": (62, 4),  # flip-chip bonding
    "t indium bump": (63, 4),  # flip-chip bonding
    "t through silicon via": (64, 4),  # TSV

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

    "mask graphical rep": (89, 0),
    "simulation signal": (90, 0),
    "simulation ground": (91, 0)

}

# pya layer information
default_layers = {}
for name, index in default_layers_dict.items():
    default_layers[name] = pya.LayerInfo(index[0], index[1], name)

default_circuit_params = {
    "a": 10,  # Width of center conductor (um)
    "b": 6,  # Width of gap (um)
    "r": 100,  # Turn radius (um)
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

# id's for the layers which needs to be exported as bitmap files.
lay_id_set = [
    default_layers["b base metal gap"],  # Legacy: Optical lit. 1 Merged
    default_layers["b base metal gap wo grid"],  # Legacy: Optical lit. 1
    default_layers["b airbridge pads"],  # legacy: Optical lit. 2
    default_layers["b airbridge flyover"],  # legacy: Optical lit. 3
    default_layers["mask graphical rep"]  # legacy: "mask graphical rep"
]

default_face_b = {
    "id": "b",
    # Metal etching layers
    "base metal gap": default_layers["b base metal gap"],
    "base metal gap wo grid": default_layers["b base metal gap wo grid"],
    "base metal addition": default_layers["b base metal addition"],
    "ground grid": default_layers["b ground grid"],
    "ground grid avoidance": default_layers["b ground grid avoidance"],

    # SQUID layer
    "SIS junction": default_layers["b SIS junction"],
    "SIS shadow": default_layers["b SIS shadow"],

    # Low-pass filters for QCR
    "filter dielectric": default_layers["b filter dielectric"],
    "filter metal": default_layers["b filter metal"],

    # NIS junctions for QCR
    "NIS junction": default_layers["b NIS junction"],
    "NIS shadow": default_layers["b NIS shadow"],

    # Airbridges
    "airbridge pads": default_layers["b airbridge pads"],
    "airbridge flyover": default_layers["b airbridge flyover"],

    # 3D integration layers
    "underbump metallization": default_layers["b underbump metallization"],
    "indium bump": default_layers["b indium bump"],
    "through silicon via": default_layers["b through silicon via"],
}

default_face_t = {
    "id": "t",
    # Metal etching layers
    "base metal gap": default_layers["t base metal gap"],
    "base metal gap wo grid": default_layers["t base metal gap wo grid"],
    "base metal addition": default_layers["t base metal addition"],
    "ground grid": default_layers["t ground grid"],
    "ground grid avoidance": default_layers["t ground grid avoidance"],

    # SQUID layer
    "SIS junction": default_layers["t SIS junction"],
    "SIS shadow": default_layers["t SIS shadow"],

    # Low-pass filters for QCR
    "filter dielectric": default_layers["t filter dielectric"],
    "filter metal": default_layers["t filter metal"],

    # NIS junctions for QCR
    "NIS junction": default_layers["t NIS junction"],
    "NIS shadow": default_layers["t NIS shadow"],

    # Airbridges
    "airbridge pads": default_layers["t airbridge pads"],
    "airbridge flyover": default_layers["t airbridge flyover"],

    # 3D integration layers
    "underbump metallization": default_layers["t underbump metallization"],
    "indium bump": default_layers["t indium bump"],
    "through silicon via": default_layers["t through silicon via"],
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