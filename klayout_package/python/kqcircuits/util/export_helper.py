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
import logging
import subprocess
import platform
from pathlib import Path

from autologging import logged, traced

from kqcircuits.elements.element import get_refpoints
from kqcircuits.defaults import default_layers, TMP_PATH, default_probe_types, default_probe_suffixes, \
    klayout_executable_command
from kqcircuits.klayout_view import KLayoutView, MissingUILibraryException
from kqcircuits.pya_resolver import pya


@traced
@logged
def generate_probepoints_json(cell, face='b'):
    # make autoprober json string for cell with reference points with magical names
    if cell is None or face not in ['b', 't']:
        error_text = f"Invalid face '{face}' or 'nil' cell ."
        error = ValueError(error_text)
        generate_probepoints_json._log.exception(error_text, exc_info=error)
        raise error

    layout = cell.layout()

    refpoints = get_refpoints(layout.layer(default_layers["refpoints"]), cell)

    # Check existence of standard markers important for us
    if f"{face}_marker_nw" in refpoints and f"{face}_marker_se" in refpoints:
        markers = {'NW': refpoints[f"{face}_marker_nw"], 'SE': refpoints[f"{face}_marker_se"]}
    else:
        generate_probepoints_json._log.error(f"There are no usable markers in {face}-face of the cell! Not a Chip?")
        return {}

    # flip top-markers back to top side
    if face == 't':
        origin = refpoints["b_marker_se"]
        markers = {k: flip(v, origin) for k, v in markers.items()}

    eu = 1e-3  # export unit

    # initialize dictionaries for each probe point group
    groups = {}
    for probe_name in default_probe_types.values():
        for marker_name, marker in markers.items():
            groups[f"{probe_name} {marker_name}"] = {
                "alignment": {"x": round(marker.x * eu, 3), "y": round(marker.y * eu, 3)},
                "pads": []
            }

    # divide probe points into groups by closest marker
    for probepoint_name, probepoint in refpoints.items():
        name_type = probepoint_name.split("_")[0]
        # if name_type starts with some probe_type, truncate name_type to be the probe_type
        for probe_type in default_probe_types:
            if name_type.startswith(probe_type):
                name_type = probe_type
                break
        # does the name correspond to a probepoint?
        if name_type in default_probe_types.keys() and probepoint_name.endswith(default_probe_suffixes):

            if face == 't':
                probepoint = flip(probepoint, origin)

            best_distance = 1e99
            closest_marker = None
            for marker, refpoint in markers.items():
                if refpoint.distance(probepoint) < best_distance:
                    best_distance = refpoint.distance(probepoint)
                    closest_marker = marker

            groups[f"{default_probe_types[name_type]} {closest_marker}"]["pads"].append({
                "id": probepoint_name,
                "x": round(probepoint.x * eu, 3),
                "y": round(probepoint.y * eu, 3),
            })

    # remove empty groups
    groups = {k: v for k, v in groups.items() if v["pads"]}

    # sort from left to right, bottom to top, for faster probing
    for group in groups.values():
        group["pads"] = sorted(group["pads"], key=lambda k: (k['x'], k['y']))

    # define JSON format
    comp_dict = {
        "groups": [{"id": name, **group} for name, group in groups.items()]
    }

    comp_json = json.dumps(comp_dict, indent=2, sort_keys=True)

    return comp_json

def flip(point, origin=pya.DPoint(0,0)):
    """Gets correct flip chip coordinates by setting a new origin and mirroring ``point`` by the y-axis."""
    return pya.DPoint(origin.x - point.x, point.y - origin.y)

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
    Writes file COMMIT_REFERENCE into given file path. The file includes current git revision number.
    If git repository is not found in given path, no file is written.
    """
    try:
        output = subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL, cwd=path)
    except subprocess.CalledProcessError:
        return
    with open(path.joinpath('COMMIT_REFERENCE'), 'w') as file:
        file.write("Git revision number: " + output.decode('ascii'))


def open_with_klayout_or_default_application(filepath):
    """
    Tries to open file with Klayout. If Klayout is not found, opens file with operating system's default application.
    Implementation supports Windows, macOS, and Linux.
    """
    try:
        subprocess.call((klayout_executable_command(), filepath))
        return
    except FileNotFoundError:
        logging.warning("Klayout executable not found.")

    try:
        if platform.system() == 'Windows':  # Windows
            subprocess.call(filepath, shell=True)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.call(('open', filepath))
        else:  # Linux
            subprocess.call(('xdg-open', filepath))
    except FileNotFoundError:
        logging.warning("Unable to open file %s.", filepath)
