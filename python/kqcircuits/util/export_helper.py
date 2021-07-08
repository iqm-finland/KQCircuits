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


import json
import subprocess
from pathlib import Path

import pya
from autologging import logged, traced

from kqcircuits.elements.element import get_refpoints
from kqcircuits.defaults import default_layers, TMP_PATH
from kqcircuits.klayout_view import KLayoutView, MissingUILibraryException


@traced
@logged
def generate_probepoints_json(cell):
    # make autoprober json string for cell with reference points with magical names
    if cell is None:
        error_text = "Cannot export probe points corresponding to nil cell."
        error = ValueError(error_text)
        generate_probepoints_json._log.exception(error_text, exc_info=error)
        raise error

    layout = cell.layout()

    refpoints = get_refpoints(layout.layer(default_layers["refpoints"]), cell)

    # Assumes existence of standard markers
    probe_types = {
        "testarray": {
            "testarrays NW": refpoints["b_marker_nw"],
            "testarrays SE": refpoints["b_marker_se"]
        },
        "qb": {
            "qubits NW": refpoints["b_marker_nw"],
            "qubits SE": refpoints["b_marker_se"]
        }
    }

    eu = 1e-3  # export unit

    # initialize dictionaries for each probe point group
    groups = {}
    for markers in probe_types.values():
        for marker_name, marker in markers.items():
            groups[marker_name] = {
                "alignment": {"x": marker.x * eu, "y": marker.y * eu},
                "pads": []
            }

    # divide probe points into groups by closest marker
    for probepoint_name, probepoint in refpoints.items():
        name_parts = probepoint_name.split("_")
        # does the name correspond to a probepoint?
        if name_parts[0] in probe_types.keys() and (probepoint_name.endswith("_l") or probepoint_name.endswith("_c")):
            best_distance = 1e99
            best_refpoint_name = None
            for name, refpoint in probe_types[name_parts[0]].items():
                if refpoint.distance(probepoint) < best_distance:
                    best_distance = refpoint.distance(probepoint)
                    best_refpoint_name = name
            groups[best_refpoint_name]["pads"].append({
                "id": probepoint_name,
                "x": probepoint.x * eu,
                "y": probepoint.y * eu,
                "side": "left"
            })

    # sort from left to right, bottom to top, for faster probing
    for group in groups.values():
        group["pads"] = sorted(group["pads"], key=lambda k: (k['x'], k['y']))

    # define JSON format
    comp_dict = {
        "groups": [{"id": name, **group} for name, group in groups.items()]
    }

    comp_json = json.dumps(comp_dict, indent=2, sort_keys=True)

    return comp_json


def create_or_empty_tmp_directory(dir_name):
    """Creates directory into TMP_PATH or removes its content if it exists.
    Returns directory path.
    """
    def remove_content(path):
        """ Removes content of the directory path without removing directory itself."""
        for child in path.iterdir():
            if child.is_dir():
                remove_content(child)
                child.rmdir()
            else:
                child.unlink()

    dir_path = TMP_PATH.joinpath(dir_name)
    if dir_path.exists() and dir_path.is_dir():
        remove_content(dir_path)
    else:
        dir_path.mkdir()
    return dir_path


def get_active_or_new_layout():
    """Tries to return active layout in GUI or returns new layout when running standalone."""
    try:
        klayoutview = KLayoutView(current=True)
        klayoutview.add_default_layers()
        return klayoutview.get_active_layout()
    except MissingUILibraryException:
        return pya.Layout()


def write_commit_reference_file(path: Path):
    """
    Writes file COMMIT_REFERENCE into given file path. The file includes current git revision number of KQCircuits.
    """
    with open(path.joinpath('COMMIT_REFERENCE'), 'w') as file:
        file.write("KQCircuits revision number: " +
                   subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii'))
