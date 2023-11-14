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

"""Default layer configuration file for KQCircuits.

Defines default values related to layers and faces.

Layers have a name, ID and data type. For example ``"annotations": (220, 0)`` The data type indicates which chip they
belong to with 0 being reserved for layer that do not belong to a face or a chip. The IDs run from 0-127 for the bottom
of the chips and 128-255 for the top.

KQCircuit layers are grouped by faces and functionality. The face-numbering system works as follows.
Each face-id consists of a number, the letter "b" or "t", and another number, for example "2b1". In
a multi-chip stack, we can have more than one chip, bonded on top of each other, and the first
number denotes which of these chips it refers to. The letter "b" or "t" means that the layer is
located at either the "bottom" or "top" of that chip (in the final place after full manufacturing
process). The last number is an additional index that can be used if necessary, in case multiple
deposition layers and etching processes are needed.

The data type 0 is reserved for auxiliary layers. Annotations, refpoints and text fields are between 220-229.
Simulations use the data type 0 by creating custom layers starting from layer number 1000.

In Klayout GUI these layers are organised in view groups according to faces. Simulation and text
layer views are hidden by default. See https://www.klayout.de/doc-qt5/manual/layer_source.html

``default_layers`` is a flat dictionary mapping layer names to corresponding pya.LayerInfo objects.
While ``default_faces`` is a dictionary mapping '1t1', '2b1', '2t1' etc. to an other dictionary, a subset of
``default_layers`` in the given face. With a minor twist: in these "face-dictionaries" the keys do not
start with the face id, for example "1t1_base_metal_gap" becomes "base_metal_gap".

Layer names should not start with ``-``, this is reserved for marking exported layers to be inverted
in ``mask_export_layers``.
"""

from pathlib import Path

from kqcircuits.pya_resolver import pya
from kqcircuits.layer_cluster import LayerCluster

# These layers are present in all faces. Layer id will have +128 for top face and data type +1 between chips
_common_layers = {
    # Metal etching layers for front face (facing towards bottom chip)
    "base_metal_gap": (1, 1),

    # merged etching layer with grid  (layers 11 & 13) that defines microscopic structures such as waveguides, launchers
    "base_metal_gap_wo_grid": (2, 1),  # etching layer without grid
    "base_metal_addition": (3, 1),  # Features subtracted from layer 11 , only used during the design.
    "ground_grid": (4, 1),  # A subset of structures combined into layer 10 (e.g. ground plane perforations)

    # Occupy the area where there should be no grids, only used during the design.
    "ground_grid_avoidance": (5, 1),
}

# common layers in b and t
_common_b_t_layers = {
    **_common_layers,

    "base_metal_gap_for_EBL": (6, 1),  # Features of layer 41 that are needed for EBL
    "waveguide_path": (7, 1),  # Waveguide's metal part, used with waveguide length and DRC calculations

    # Junction layer
    "SIS_junction": (8, 1),  # Josephson junction evaporation opening
    "SIS_shadow": (9, 1),  # Josephson junction resist undercut
    "SIS_junction_2": (11, 1),

    # Airbridge layers -- potentially obsolete
    "airbridge_pads": (18, 1),  #
    "airbridge_flyover": (19, 1),  #

    "chip_dicing": (30, 1),

    # 3D integration layers
    "underbump_metallization": (20, 1),  # flip-chip bonding
    "indium_bump": (21, 1),  # flip-chip bonding
    "through_silicon_via": (22, 1),  # TSV
    "through_silicon_via_avoidance": (25, 1),  # TSV

    # Netlist
    "ports": (26, 1),  # Considered conductive in the netlist extraction
}

def _shift_layers(layers, shift_ID, shift_data_type):
    """Add a number to replicate a group of layers on a different face.

    This is a helper function so we don't have to copy-paste similar groups of layers to several
    faces. It returns a new layer group where every layer id is increased by the number ``shift``.
    """
    return {n: (v[0] + shift_ID, v[1] + shift_data_type) for n, v in layers.items()}

# organizer layers into faces
_face_layers = {}   # layer descriptions per every chip face

_face_layers['1b1'] = {
    **_common_b_t_layers,
}

_face_layers['1t1'] = {
    **_shift_layers(_common_b_t_layers, 128, 0),
}

# Top face layers
_face_layers['2b1'] = {
    **_shift_layers(_common_b_t_layers, 0, 1),    # common layers at the "top"
}

# Ceiling face layers
_face_layers['2t1'] = {
    **_shift_layers(_common_b_t_layers, 128, 1),     # same common layers at the "ceiling"
}

# Other auxiliary layers [Layer 220-229]
_aux_layers_dict = {
    "annotations": (220, 0),
    "annotations_2": (221, 0),
    "instance_names": (222, 0),
    "mask_graphical_rep": (223, 0),
    "waveguide_length": (224, 0),  # Length only, no DRC. When Waveguide leves its layer, e.g. Airbridge.
    "refpoints": (225, 0),
}

# default_faces[face_id] contains the face dictionary for the face determined by face_id.
#
# Each face dictionary should contain:
#   - key "id" with value face_id (string)
#   - for all the available layers in that face: key "Layer_name", value pya.LayerInfo object for that layer
#
default_faces = {}
for f in ('1t1', '2b1', '1b1', '2t1'):
    default_faces[f] = {n: pya.LayerInfo(i[0], i[1], f'{f}_{n}') for n, i in _face_layers[f].items()}

# pya layer information
default_layers = {n: pya.LayerInfo(i[0], i[1], n) for n, i in _aux_layers_dict.items()}
for face, layers in default_faces.items():
    default_layers.update({f'{face}_{name}': li for name, li in layers.items()})

for f in ('1t1', '2b1', '1b1', '2t1'):
    default_faces[f]['id'] = f

default_face_id = "1t1"  # face_id of the face that is used by default in some contexts

# Layer names (without face prefix) for layers exported as individual .oas files during mask layout export.
default_mask_export_layers = [
    "base_metal_gap",
    "base_metal_gap_wo_grid",
    "airbridge_pads",
    "airbridge_flyover",
]

# Layer names (without face prefix) with mask label postfix for mask label and mask covered region creation.
default_layers_to_mask = {
    "base_metal_gap_wo_grid": "1",
    "airbridge_pads": "2",
    "airbridge_flyover": "3"
}

# Layer names (without face prefix) in `layers_to_mask` for which mask covered region is not created.
default_covered_region_excluded_layers = [
    "indium_bump",
    "through_silicon_via",
]

# Layer names (without face prefix) for layers exported as bitmap files during full mask layout export (does not
# apply to individual pixels).
mask_bitmap_export_layers = [
    # "base_metal_gap_wo_grid",
    "mask_graphical_rep",
]

# Layers to hide when exporting a bitmap with "all" layers.
all_layers_bitmap_hide_layers = [default_layers[l] for l in _aux_layers_dict] + [
    default_layers["1b1_ports"],
    default_layers["1b1_base_metal_gap"],
    default_layers["1b1_ground_grid"],
    default_layers["1b1_ground_grid_avoidance"],
    default_layers["1b1_waveguide_path"],
    default_layers["1t1_ports"],
    default_layers["1t1_base_metal_gap"],
    default_layers["1t1_ground_grid"],
    default_layers["1t1_ground_grid_avoidance"],
    default_layers["1t1_waveguide_path"],
    default_layers["2b1_ports"],
    default_layers["2b1_base_metal_gap"],
    default_layers["2b1_ground_grid"],
    default_layers["2b1_ground_grid_avoidance"],
    default_layers["2b1_waveguide_path"],
    default_layers["2b1_base_metal_gap"],
    default_layers["2b1_ground_grid"],
    default_layers["2b1_ground_grid_avoidance"],
]

# Layer clusters used for exporting only certain layers together in the same file, when exporting individual chips
# during mask layout export.
# Dictionary with items "cluster name: LayerCluster".
chip_export_layer_clusters = {
    # 1b1-face
    "SIS-1b1": LayerCluster(["1b1_SIS_junction", "1b1_SIS_shadow", "1b1_SIS_junction_2"],
                            ["1b1_base_metal_gap_for_EBL"], "1b1"),
    "airbridges-1b1": LayerCluster(["1b1_airbridge_pads", "1b1_airbridge_flyover"],
                                   ["1b1_base_metal_gap_wo_grid"], "1b1"),
    # 1t1-face
    "SIS-1t1": LayerCluster(["1t1_SIS_junction", "1t1_SIS_shadow", "1t1_SIS_junction_2"],
                            ["1t1_base_metal_gap_for_EBL"], "1t1"),
    "airbridges-1t1": LayerCluster(["1t1_airbridge_pads", "1t1_airbridge_flyover"],
                                   ["1t1_base_metal_gap_wo_grid"], "1t1"),
    # 2b1-face
    "SIS-2b1": LayerCluster(["2b1_SIS_junction", "2b1_SIS_shadow", "2b1_SIS_junction_2"],
                            ["2b1_base_metal_gap_for_EBL"], "2b1"),
    "airbridges-2b1": LayerCluster(["2b1_airbridge_pads", "2b1_airbridge_flyover"],
                                   ["2b1_base_metal_gap_wo_grid"], "2b1"),
}

# default layers to use for calculating cell path lengths with get_cell_path_length()
default_path_length_layers = [
    "1b1_waveguide_path",
    "1t1_waveguide_path",
    "2b1_waveguide_path",
    "2t1_waveguide_path",
    "waveguide_length"  # AirbridgeConnection uses this
]

# default mask parameters for each face
# dict of face_id: parameters
default_mask_parameters = {
    "1b1": {
        "wafer_rad": 76200,
        "chips_map_offset": pya.DVector(-1200, 1200),
        "chip_size": 10000,
        "chip_box_offset": pya.DVector(0, 0),
        "chip_trans": pya.DTrans(),
        "dice_width": 200,
        "text_margin": 100,
        "mask_text_scale": 1.0,
        "mask_marker_offset": 50000,
    },
    "1t1": {
        "wafer_rad": 76200,
        "chips_map_offset": pya.DVector(-1200, 1200),
        "chip_size": 10000,
        "chip_box_offset": pya.DVector(0, 0),
        "chip_trans": pya.DTrans(),
        "dice_width": 200,
        "text_margin": 100,
        "mask_text_scale": 1.0,
        "mask_marker_offset": 50000,
    },
    "2b1": {
        "wafer_rad": 76200,
        "chips_map_offset": pya.DVector(-2700, 2700),
        "chip_size": 7000,
        "chip_box_offset": pya.DVector(1500, 1500),
        "chip_trans": pya.DTrans(pya.DVector(10000, 0)) * pya.DTrans().M90,
        "dice_width": 140,
        "text_margin": 100,
        "mask_text_scale": 0.7,
        "mask_marker_offset": 50000,
    },
    "2t1": {
        "wafer_rad": 76200,
        "chips_map_offset": pya.DVector(-2700, 2700),
        "chip_size": 7000,
        "chip_box_offset": pya.DVector(1500, 1500),
        "chip_trans": pya.DTrans(pya.DVector(10000, 0)) * pya.DTrans().M90,
        "dice_width": 140,
        "text_margin": 100,
        "mask_text_scale": 0.7,
        "mask_marker_offset": 50000,
    }
}

default_parameter_values = {}

default_layer_props = str(Path(__file__).resolve().parent.parent/"layer_config"/"default_layer_props.lyp")

default_chip_label_face_prefixes = {
    "1b1": "h",
    "1t1": "b",
    "2b1": "t",
    "2t1": "c",
}
