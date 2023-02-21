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

Defines values for things such as default layers, paths, and default sub-element types.
"""
import os
import subprocess
from pathlib import Path

from kqcircuits.pya_resolver import pya
from kqcircuits.util.import_helper import module_from_file


_kqcircuits_path = Path(os.path.dirname(os.path.realpath(__file__)))
# workaround for Windows because os.path.realpath doesn't work there before Python 3.8
if os.name == "nt" and os.path.islink(Path(__file__).parent):
    _kqcircuits_path = Path(os.readlink(str(Path(__file__).parent)))

# project paths
SRC_PATHS = [_kqcircuits_path]
ROOT_PATH = Path(os.getenv('KQC_ROOT_PATH', os.getcwd()))  # "current dir" or set by optional KQC_ROOT_PATH
if _kqcircuits_path.parts[-3] == "klayout_package":  # developer setup
    ROOT_PATH = _kqcircuits_path.parents[2]

TMP_PATH = Path(os.getenv('KQC_TMP_PATH', ROOT_PATH.joinpath("tmp")))  # specify alternative tmp directory
_py_path = ROOT_PATH.joinpath("klayout_package/python")

if _kqcircuits_path.parts[-4] == "salt":  # KQC Salt package
    ROOT_PATH = _kqcircuits_path.parents[1]
    _py_path = ROOT_PATH.joinpath("python")
    TMP_PATH = _kqcircuits_path.parents[3].joinpath("python/tmp")  # local tmp dir for salt package

SCRIPTS_PATH = _py_path.joinpath("scripts")
DRC_PATH = _py_path.joinpath("drc")

TMP_PATH.mkdir(parents=True, exist_ok=True)  # TODO move elsewhere?

ANSYS_SCRIPT_PATHS = [SCRIPTS_PATH.joinpath("simulations").joinpath("ansys")]
ELMER_SCRIPT_PATHS = [SCRIPTS_PATH.joinpath("simulations").joinpath("elmer")]
XSECTION_PROCESS_PATH = ROOT_PATH.joinpath("xsection/kqc_process.xs")

VERSION_PATHS = {}
VERSION_PATHS['KQC'] = ROOT_PATH
SIM_SCRIPT_PATH = ROOT_PATH / 'klayout_package' / 'python' / 'scripts' / 'simulations'

# Given to subprocess.Popen calls, hides terminals on Windows
STARTUPINFO = None
if os.name == "nt":
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW

# printed to corners of all chips and top of all masks
# could be for example "IQM" or "A!"
default_brand = "IQM"

# default output format and extension
default_output_format = "OASIS"

# default bitmap dimensions
default_png_dimensions = (1000, 1000)

default_junction_type = "Manhattan"
default_airbridge_type = "Airbridge Rectangular"
default_fluxline_type = "Fluxline Standard"
default_marker_type = "Marker Standard"
default_junction_test_pads_type = "Junction Test Pads Simple"
default_tsv_type = "Tsv Standard"

default_drc_runset = "example.lydrc"

# default elements to breakdown before netlist export
# list of strings
default_netlist_breakdown = [
    "Waveguide Composite",
    "Meander",
]

default_netlist_ignore_connections = [
    ("drive", "drive"), # Don't connect two overlapping qubit drive ports
]

# default progress bar formatting with tqdm
default_bar_format = '{l_bar}{bar}| {n_fmt}/{total_fmt} [Elapsed: {elapsed}, Left (eta): {remaining}, {rate_inv_fmt}' \
                     '{postfix}]'

# dictionary of probepoint types for probepoint export
# key is the refpoint name prefix for a type of probepoints, value is a text representation of the probepoint type
default_probe_types = {"testarray": "testarrays", "qb": "qubits"}
# tuple of refpoint name suffixes that are used (together with probe_types) to identify refpoints as probepoints
default_probe_suffixes = ("_c", "_l")

# Library names in dependency order. Every library should have its dependencies before its own entry.
kqc_library_names = (
    'Element Library',
    'Junction Library',
    'Test Structure Library',
    'Qubit Library',
    'Chip Library',
)

# The user may override KQC Element's default parameters
default_parameter_values = {
    "AirbridgeConnection": {"bridge_length": 60, "pad_length": 22},
    "TsvTest": {"tsv_elliptical_width": 10},
}

default_bump_parameters = {
    "bump_diameter": 25,
    "under_bump_diameter": 40,
    "bump_grid_spacing": 120,
    "bump_edge_to_bump_edge_separation": 95,
    "edge_from_bump": 550,
}


# Dictionary of sample holders to determine launcher parameters and chip sizes. Keys are sampleholder names, values are
# dictionaries containing the following items:
#
#            n: number of launcher pads or an array of pad numbers per side
#            launcher_type: type of the launchers, "RF" or "DC"
#            launcher_width: width of the launchers
#            launcher_gap: pad to ground gap of the launchers
#            launcher_indent: distance between the chip edge and pad port
#            pad_pitch: distance between pad centers
#            chip_box: chip size
#
default_sampleholders = {
    "SMA8": {
        "n": 8,
        "launcher_type": "RF",
        "launcher_width": 300,
        "launcher_gap": 260,
        "launcher_indent": 800,
        "launcher_frame_gap": 180,
        "pad_pitch": 4400,
        "chip_box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000))
    },
    "ARD24": {
        "n": 24,
        "launcher_type": "RF",
        "launcher_width": 240,
        "launcher_gap": 179,
        "launcher_indent": 680,
        "pad_pitch": 1200,
        "chip_box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000))
    },
    "DC24": {
        "n": 24,
        "launcher_type": "DC",
        "launcher_width": 500,
        "launcher_gap": 300,
        "launcher_indent": 680,
        "pad_pitch": 850,
        "chip_box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000))
    }
}

# Elements that are visible in the Node editor plugin dropdown box, specified by class name. A list of in principle
# valid elements can be generated with kqcircuits.util.gui_helper.get_valid_node_elements, but that function generates
# an instance of each PCell which is clumsy to run at startup.
# In the list below basic waveguide elements are omitted since they can be better generated by other node parameters
node_editor_valid_elements = [
    'Airbridge', 'AirbridgeConnection', 'AirbridgeMultiFace', 'AirbridgeRectangular', 'CircularCapacitor',
    'FingerCapacitorSquare', 'FingerCapacitorTaper', 'FlipChipConnectorRf', 'SmoothCapacitor',
    'WaveguideCoplanarSplitter']

# Path to the layer configuration file, which defines layer/face related defaults.
# The path can be either absolute or relative.
layer_config_path = Path(__file__).parent/"layer_config"/"default_layer_config.py"

# Load layer/face related defaults from the layer config file

layer_config_module = module_from_file(layer_config_path)
# pya layer information
default_layers = layer_config_module.default_layers
# default_faces[face_id] contains the face dictionary for the face determined by face_id.
#
# Each face dictionary should contain:
#   - key "id" with value face_id (string)
#   - for all the available layers in that face: key "Layer_name", value pya.LayerInfo object for that layer
default_faces = layer_config_module.default_faces
# face_id of the face that is used by default in some contexts
default_face_id = layer_config_module.default_face_id
# Layer names (without face prefix) for layers exported as individual .oas files during mask layout export
default_mask_export_layers = layer_config_module.default_mask_export_layers
# Layer names (without face prefix) with mask label postfix for mask label and mask covered region creation
default_layers_to_mask = layer_config_module.default_layers_to_mask
# Layer names (without face prefix) in `layers_to_mask` for which mask covered region is not created
default_covered_region_excluded_layers = layer_config_module.default_covered_region_excluded_layers
# Layer names (without face prefix) for layers exported as bitmap files during full mask layout export (does not
# apply to individual pixels)
mask_bitmap_export_layers = layer_config_module.mask_bitmap_export_layers
# Layers to hide when exporting a bitmap with "all" layers
all_layers_bitmap_hide_layers = layer_config_module.all_layers_bitmap_hide_layers
# Layer clusters used for exporting only certain layers together in the same file, when exporting individual chips
# during mask layout export (dict with items `cluster name: LayerCluster`)
chip_export_layer_clusters = layer_config_module.chip_export_layer_clusters
# Default layers to use for calculating cell path lengths with get_cell_path_length()
default_path_length_layers = layer_config_module.default_path_length_layers
# Default mask parameters for each face (dict with items `face_id: parameters`)
default_mask_parameters = layer_config_module.default_mask_parameters
# Path to layer properties file
default_layer_props = layer_config_module.default_layer_props
# Prefixes to use in chip name labels for different faces (dict with items `face_id: label_prefix`)
default_chip_label_face_prefixes = layer_config_module.default_chip_label_face_prefixes
# Update default_parameter_values based on layer config file
for k, v in layer_config_module.default_parameter_values.items():
    params = default_parameter_values[k] if k in default_parameter_values else {}
    for k2, v2 in v.items():
        params[k2] = v2
    default_parameter_values[k] = params
