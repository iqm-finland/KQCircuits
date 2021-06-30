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


"""Configuration file for KQCircuits.

Defines values for things such as default layers, paths, and layers used for different exports.

Layers have a name, ID and data type. For example ``"annotations": (220, 1)``.

KQCircuit layers are grouped by faces and functionality. The main geometry containing layer groups
are: bottom 10-39, top 40-69 and ceiling 70-89. Simulation 90-99, layers are in either top or bottom
faces. Layer ID's 100-219 are reserved. Auxiliary layers 220-229 are not face dependent, they
contain annotations, refpoints and other text fields.

In Klayout GUI these layers are organised in view groups according to faces. Simulation and text
layer views are hidden by default. See https://www.klayout.de/doc-qt5/manual/layer_source.html

``default_layers`` is a flat dictionary mapping layer names to corresponding pya.LayerInfo objects.
While ``default_faces`` is a dictionary mapping 'b', 't' and 'c' to an other dictionary, a subset of
``default_layers`` in the given face. With a minor twist: in these "face-dictionaries" the keys do not
start with the face id, for example "b_base_metal_gap" becomes "base_metal_gap".
"""

import os
from pathlib import Path

from kqcircuits.pya_resolver import pya
from kqcircuits.layer_cluster import LayerCluster

_kqcircuits_path = Path(os.path.dirname(os.path.realpath(__file__)))
# workaround for Windows because os.path.realpath doesn't work there before Python 3.8
if os.name == "nt" and os.path.islink(Path(__file__).parent):
    _kqcircuits_path = Path(os.readlink(str(Path(__file__).parent)))

# project paths
ROOT_PATH = _kqcircuits_path.parent.parent
PY_PATH = ROOT_PATH.joinpath("python")
SRC_PATHS = [PY_PATH.joinpath("kqcircuits")]
TMP_PATH = ROOT_PATH.joinpath("tmp")
TMP_PATH.mkdir(exist_ok=True)
SCRIPTS_PATH = PY_PATH.joinpath("scripts")
ANSYS_SCRIPTS_PATH = SCRIPTS_PATH.joinpath("simulations").joinpath("ansys")

# printed to corners of all chips and top of all masks
# could be for example "IQM" or "A!"
default_brand = "IQM"

# These layers are present in all faces. Layer id will have +30 for 'b' and +60 for 'c'
_common_layers = {
    # Metal etching (Nb or TiN) layers for front face (facing towards bottom chip)
    "base_metal_gap": (10, 1),

    # merged etching layer with grid  (layers 11 & 13) that defines microscopic structures such as waveguides, launchers
    "base_metal_gap_wo_grid": (11, 1),  # etching layer without grid
    "base_metal_addition": (12, 0),  # Features subtracted from layer 11 , only used during the design.
    "ground_grid": (13, 0),  # A subset of structures combined into layer 10 (e.g. ground plane perforations)

    # Occupy the area where there should be no grids, only used during the design.
    "ground_grid_avoidance": (14, 0),
}

# common layers in b and t
_common_b_t_layers = {
    **_common_layers,

    "base_metal_gap_for_EBL": (15, 0),  # Features of layer 41 that are needed for EBL

    # SQUID layer
    "SIS_junction": (17, 2),  # Josephson junction
    "SIS_shadow": (18, 2),  # Ghost layer required for Josephson junction

    # Airbridge layers -- potentially obsolete
    "airbridge_pads": (28, 3),  #
    "airbridge_flyover": (29, 3),  #

    # 3D integration layers
    "underbump_metallization": (32, 4),  # flip-chip bonding
    "indium_bump": (33, 4),  # flip-chip bonding
    "through_silicon_via": (34, 4),  # TSV

    # Netlist
    "ports": (39, 0),  # Considered conductive in the netlist extraction
}

_face_layers = {}   # layer descriptions per every chip face

# Bottom face layers
_face_layers['b'] = {
    **_common_b_t_layers,

    # Simulation faces [Layer 90-99]
    "simulation_signal": (90, 0),
    "simulation_ground": (91, 0),
    "simulation_airbridge_flyover": (94, 0),
    "simulation_airbridge_pads": (95, 0),
}


def _shift_layers(layers, shift):
    """Add a constant 'shift' to all layer indexes and return the dictionary."""

    return {n: (v[0] + shift, v[1]) for n, v in layers.items()}


# Top face layers
_face_layers['t'] = {
    **_shift_layers(_common_b_t_layers, 30),    # same common layers shifted 30 levels down

    # Simulation faces
    "simulation_signal": (92, 0),
    "simulation_ground": (93, 0),
}

# Ceiling face layers
_face_layers['c'] = {
    **_shift_layers(_common_layers, 60),     # same common layers shifted 60 levels down
}

# Other auxiliary layers [Layer 220-229]
_aux_layers_dict = {
    "annotations": (220, 0),
    "annotations_2": (221, 0),
    "instance_names": (222, 0),
    "mask_graphical_rep": (223, 0),
    "waveguide_length": (224, 0),
    "refpoints": (225, 0),
}

# default_faces[face_id] contains the face dictionary for the face determined by face_id.
#
# Each face dictionary should contain:
#   - key "id" with value face_id (string)
#   - for all the available layers in that face: key "Layer_name", value pya.LayerInfo object for that layer
#
default_faces = {}
for f in ('b', 't', 'c'):
    default_faces[f] = {n: pya.LayerInfo(i[0], i[1], f'{f}_{n}') for n, i in _face_layers[f].items()}

# pya layer information
default_layers = {n: pya.LayerInfo(i[0], i[1], n) for n, i in _aux_layers_dict.items()}
for face, layers in default_faces.items():
    default_layers.update({f'{face}_{name}': li for name, li in layers.items()})

for f in ('b', 't', 'c'):
    default_faces[f]['id'] = f

# default output format and extension
default_output_format = "OASIS"

# default bitmap dimensions
default_png_dimensions = (1000, 1000)

# Layer names (without face prefix) for layers exported as individual .oas files during mask layout export.
default_mask_export_layers = [
    "base_metal_gap",
    "base_metal_gap_wo_grid",
    "airbridge_pads",
    "airbridge_flyover",
]

# Layer names (without face prefix) on which the covered region on wafer boundary, mask aligners,
# and mask IDs are exported. The indices appear in postfix in mask label
default_layers_to_mask = {
    "base_metal_gap_wo_grid": "1",
    "airbridge_pads": "2",
    "airbridge_flyover": "3"
}

# Layer names (without face prefix) for layers exported as bitmap files during full mask layout export (does not
# apply to individual pixels).
mask_bitmap_export_layers = [
    # "base_metal_gap_wo_grid",
    "mask_graphical_rep",
]

# Layers to hide when exporting a bitmap with "all" layers.
all_layers_bitmap_hide_layers = [default_layers[l] for l in _aux_layers_dict.keys()] + [
    default_layers["b_ports"],
    default_layers["b_base_metal_gap"],
    default_layers["b_ground_grid"],
    default_layers["b_ground_grid_avoidance"],
    default_layers["t_ports"],
    default_layers["t_base_metal_gap"],
    default_layers["t_ground_grid"],
    default_layers["t_ground_grid_avoidance"],
    default_layers["c_base_metal_gap"],
    default_layers["c_ground_grid"],
    default_layers["c_ground_grid_avoidance"],
]

# Layer clusters used for exporting only certain layers together in the same file, when exporting individual chips
# during mask layout export.
# Dictionary with items "cluster name: LayerCluster".
chip_export_layer_clusters = {
    # b-face
    "SIS b": LayerCluster(["b_SIS_junction", "b_SIS_shadow"], ["b_base_metal_gap_for_EBL"], "b"),
    "airbridges b": LayerCluster(["b_airbridge_pads", "b_airbridge_flyover"], ["b_base_metal_gap_wo_grid"], "b"),
    # t-face
    "SIS t": LayerCluster(["t_SIS_junction", "t_SIS_shadow"], ["t_base_metal_gap_for_EBL"], "t"),
    "airbridges t": LayerCluster(["t_airbridge_pads", "t_airbridge_flyover"], ["t_base_metal_gap_wo_grid"], "t"),
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

default_squid_type = "QCD1"
default_airbridge_type = "Airbridge Rectangular"
default_fluxline_type = "Fluxline Standard"
default_marker_type = "Marker Standard"
default_junction_test_pads_type = "Junction Test Pads Simple"

default_drc_runset = "example.drc"


# default elements to breakdown before netlist export
# list of strings
default_netlist_breakdown = [
    "Waveguide Composite",
    "Meander",
]

# default progress bar formatting with tqdm
default_bar_format = '{l_bar}{bar}| {n_fmt}/{total_fmt} [Elapsed: {elapsed}, Left (eta): {remaining}, {rate_inv_fmt}{postfix}]'