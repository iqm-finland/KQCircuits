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
import importlib.metadata
import json
import logging
import subprocess
import platform
import sys
import os
import argparse
from sys import argv
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from kqcircuits.elements.element import get_refpoints
from kqcircuits.defaults import default_layers, TMP_PATH, STARTUPINFO, default_probe_types, default_probe_suffixes, \
    recommended_probe_suffix_mapping, VERSION_PATHS, default_drc_runset, DRC_PATH
from kqcircuits.klayout_view import KLayoutView, MissingUILibraryException
from kqcircuits.pya_resolver import pya, is_standalone_session, klayout_executable_command


def _probe_point_coordinate(pos, eu=1e-3, sd=4):
    return {"x": round(pos.x * eu, sd), "y": round(pos.y * eu, sd)}

def _probe_point_to_dpoint(pos, eu=1e-3):
    # this doesn't need to be super precise since we currently only use this to compare distances
    return pya.DPoint(pos["x"] / eu, pos["y"] / eu)

# pylint: disable=dangerous-default-value
def generate_probepoints_json(cell: pya.Cell,
                              face: str = '1t1',
                              flip_face: Optional[bool] = None,
                              references: List[str] = ['nw'],
                              contact: Optional[Union[
                                  Tuple[pya.DPoint, pya.DPoint],
                                  List[Tuple[pya.DPoint, pya.DPoint]]]] = None) -> Dict:
    """For given cell, collects probepoints from cell's refpoints into a json Dict.

    A refpoint is a probepoint if it

        * contains some string from ``default_probe_types`` and
        * has a suffix from ``default_probe_suffixes``

    Json format consists of {'x': x, 'y': y} type 2d points, in millimeter units.
    The returned json object consists of:

        * an 'alignment' point, which tells the position of the reference marker defined in references marker and
        * 'sites' list. Each entry of the list has a 'west' and 'east' point, and also a unique 'id' as string

    Args:
        * cell: cell from which to collect probepoints
        * face: name of the face from where to collect probepoints
        * flip_face: explicitly specifies if the points should be flipped around the y-axis.
            Can be set to None, in which case will infer whether to flip points from the ``face`` arg
        * references: a list of markers to use as alignment references. String values are one of
            "nw", "ne", "sw", "se". If multiple values supplied, the resulting json will have
            "groups" key on top level, with each group containing the marker string as 'id'
            and its own 'alignment' and 'sites' values, grouping each site to its closest marker.
        * contact: a manually defined contact probe, a tuple of two DPoints.
            Can be None so no "contact" site is added, or can be a list if a different "contact"
            site is needed for each reference
    """
    validations = [
        (cell is None, "Cell is null"),
        (not references, "Can't use empty list of references"),
        (isinstance(contact, tuple) and len(contact) < 2, "Singular contact must be tuple of two DPoints"),
        (isinstance(contact, list) and (len(contact) != len(references) or any(len(c) < 2 for c in contact)),
            "List of contacts should define a tuple of two DPoints for each reference")
    ]
    for check, error_text in validations:
        if check:
            error = ValueError(error_text)
            logging.exception(error_text, exc_info=error)
            raise error

    layout = cell.layout()

    refpoints = get_refpoints(layout.layer(default_layers["refpoints"]), cell)

    # check existence of reference markers
    markers = {}
    for reference in references:
        marker_refpoint = f"{face}_marker_{reference.lower()}"
        if marker_refpoint not in refpoints:
            to_legacy_face_name = {face: '', '1t1': 'b', '2b1': 't'}
            legacy_marker_refpoint = f"{to_legacy_face_name[face]}_marker_{reference.lower()}"
            if legacy_marker_refpoint in refpoints:
                marker_refpoint = legacy_marker_refpoint
            else:
                logging.warning((f"The marker or at least its refpoint {marker_refpoint} "
                                f"is missing in the cell {cell.name}!"))
                if pya.DPoint(1500, 8500) not in markers.values():
                    logging.warning(f"Setting marker {marker_refpoint} to DPoint(1500, 8500)")
                    markers[reference.upper()] = pya.DPoint(1500, 8500)
                continue
        markers[reference.upper()] = refpoints[marker_refpoint]

    # if not explicitely stated to flip the face, deduce from face string
    if flip_face is None:
        if len(face) < 2:   # legacy face name
            flip_face = face == "t"
        else:               # current face name
            flip_face = face[1] == "b"
    # get boundaries of the chip dimensions
    matching_layer = [l for l in layout.layer_infos()
                      if l.name in [f"{face}_base_metal_gap_wo_grid", f"{face}*base*metal*gap*wo*grid"]]
    if matching_layer:
        bbox_for_face = cell.dbbox_per_layer(layout.layer(matching_layer[0]))
    else:
        logging.warning(f"No geometry found at layer {face}_base_metal_gap_wo_grid!")
        bbox_for_face = pya.DBox(1500, 1500, 8500, 8500) if flip_face else pya.DBox(0, 0, 10000, 10000)
        logging.warning(f"Assuming chip dimensions are at {bbox_for_face}")
    # define transformation function to apply to each DPoint object
    transform = lambda point: pya.DPoint(point - bbox_for_face.p1)
    # flip top-markers back to top side
    if flip_face:
        flip_origin = pya.DPoint(bbox_for_face.p2.x, bbox_for_face.p1.y)
        transform = lambda point: pya.DPoint(flip_origin.x - point.x, point.y - flip_origin.y)
    markers = {k: transform(v) for k, v in markers.items()}

    # initialize dictionaries for each probe point group
    groups = {}
    for marker_name, marker in markers.items():
        groups[marker_name] = {
            "alignment": _probe_point_coordinate(marker),
            "sites": []
        }

    # first collect sites before grouping them
    sites = []
    for probepoint_name, probepoint in refpoints.items():
        probepoint = transform(probepoint)
        name_type = probepoint_name.split("_")[0]
        # if name_type starts with some probe_type, truncate name_type to be the probe_type
        for probe_type in default_probe_types:
            if name_type.lower().startswith(probe_type.lower()):
                name_type = probe_type.lower()
                break
        # extract suffix if probepoint_name uses one from default_probe_suffixes
        suffixes = [s for s in default_probe_suffixes if probepoint_name.endswith(s)]
        if name_type in default_probe_types and suffixes:
            remove_suffix_tokens = max(len(suffixes[0].split('_')) - 2, 1)
            probe_name = '_'.join(probepoint_name.split('_')[:-remove_suffix_tokens])
            # find site with id value as this probepoint prefix
            probepoint_sites = [s for s in sites if s["id"] == probe_name]
            probepoint_entry = _probe_point_coordinate(probepoint)
            # create a new site if none found
            if not probepoint_sites:
                sites.append({"id": probe_name, "west": probepoint_entry})
            else:
                site = probepoint_sites[0]
                if "east" not in site:
                    if probepoint_entry["x"] < site["west"]["x"]:
                        site["east"] = site["west"]
                        direction = "west"
                    else:
                        direction = "east"
                    site[direction] = probepoint_entry
                    expected_direction = recommended_probe_suffix_mapping.get(suffixes[0])
                    if expected_direction is not None and expected_direction != direction:
                        logging.warning((f"Probepoint {probepoint_name} was mapped to {direction}, "
                                        f"but recommended direction for {suffixes[0]} is {expected_direction}"))
                else:
                    # limited support for more than two point probing
                    for key in site:
                        if key == "id":
                            continue
                        sites.append({
                            "east": site[key] if site[key]["x"] > probepoint_entry["x"] else probepoint_entry,
                            "id": f"{probe_name}{suffixes[0]}_{key}",
                            "west": probepoint_entry if site[key]["x"] > probepoint_entry["x"] else site[key],
                        })

    # sanity check that each site has exactly east and west probe
    for site in sites:
        if set(site.keys()) != {"west", "east", "id"}:
            logging.warning(f"Malformed site object detected: {site}")
            if "east" in site and "west" not in site:
                site["west"] = site["east"]
            elif "west" in site and "east" not in site:
                site["east"] = site["west"]
            elif "east" not in site and "west" not in site:
                site["east"] = {"x": 0.0, "y": 0.0}
                site["west"] = {"x": 0.0, "y": 0.0}

    # reason for sorting is to make the exported json more deterministic
    sites.sort(key=lambda site: site["id"])
    for idx,_ in enumerate(sites):
        sites[idx] = dict(sorted(sites[idx].items()))

    # divide probe points into groups by closest marker (multireference only)
    for site in sites:
        midpoint = {"x": (site["west"]["x"] + site["east"]["x"]) / 2.,
                    "y": (site["west"]["y"] + site["east"]["y"]) / 2.}
        midpoint = _probe_point_to_dpoint(midpoint)
        _, closest_marker = sorted(
            [(refpoint.distance(midpoint), marker) for marker, refpoint in markers.items()],
            key=lambda x: x[0])[0]   # sort by distance, get closest tuple, get marker
        groups[closest_marker]["sites"].append(site)

    # add manual "contact" entries
    if contact is not None:
        if isinstance(contact, tuple):
            contact = [contact] * len(references)
        for idx, group in enumerate(groups.values()):
            contact1, contact2 = contact[idx]
            contact1 = _probe_point_coordinate(transform(contact1))
            contact2 = _probe_point_coordinate(transform(contact2))
            west_is_1 = contact1["x"] < contact2["x"]
            group["sites"].append({
                "east": contact2 if west_is_1 else contact1,
                "id": "contact",
                "west": contact1 if west_is_1 else contact2,
            })

    # find probepoint duplicates (within tolerance) and only keep the one with longer id name
    for group_key, group in groups.items():
        for i, site1 in enumerate(group["sites"]):
            if site1 == {}:
                continue
            for j, site2 in enumerate(group["sites"][i+1:]):
                if site2 == {}:
                    continue
                too_close = True
                for side in ["west", "east"]:
                    x1 = site1[side]["x"]
                    x2 = site2[side]["x"]
                    y1 = site1[side]["y"]
                    y2 = site2[side]["y"]
                    if ((x1 - x2) ** 2) + ((y1 - y2) ** 2) > (0.001) ** 2:
                        too_close = False
                if too_close:
                    logging.warning(
                        f"Found two sites '{site1['id']}' and '{site2['id']}' with similar coordinates (respectively)")
                    logging.warning(
                        f"  west {site1['west']['x']},{site1['west']['y']} = {site2['west']['x']},{site2['west']['y']}")
                    logging.warning(
                        f"  east {site1['east']['x']},{site1['east']['y']} = {site2['east']['x']},{site2['east']['y']}")
                    logging.warning(("  will only keep the site "
                                    f"'{site1['id'] if len(site1['id']) > len(site2['id']) else site2['id']}'"))
                    group["sites"][i+j+1 if len(site1["id"]) > len(site2["id"]) else i].clear()
                if site1 == {}:
                    break
        # pylint: disable=unnecessary-dict-index-lookup
        groups[group_key]["sites"] = [site for site in group["sites"] if site != {}]

    # remove empty groups
    groups = {k: v for k, v in groups.items() if v["sites"]}

    # leave out groups key if only one group
    if len(groups) == 1:
        return list(groups.values())[0]
    return {"groups": [{"id": name, **group} for name, group in groups.items()]}


def generate_probepoints_from_file(cell_file: str,
                              face: str = '1t1',
                              flip_face: Optional[bool] = None,
                              references: List[str] = ['nw'],
                              contact: Optional[Union[
                                  Tuple[pya.DPoint, pya.DPoint],
                                  List[Tuple[pya.DPoint, pya.DPoint]]]] = None) -> Dict:
    """For an OAS and GDS file containing a chip at its top cell,
    collects probepoints from cell's refpoints into a json Dict.
    A refpoint is a probepoint if it

        * contains some string from ``default_probe_types`` and
        * has a suffix from ``default_probe_suffixes``

    Json format consists of {'x': x, 'y': y} type 2d points, in millimeter units.
    The returned json object consists of:

        * an 'alignment' point, which tells the position of the reference marker defined in references marker and
        * 'sites' list. Each entry of the list has a 'west' and 'east' point, and also a unique 'id' as string

    Args:
        * cell_file: file path to the OAS or GDS file containing a chip at its top cell
        * face: name of the face from where to collect probepoints
        * flip_face: explicitly specifies if the points should be flipped around the y-axis.
            Can be set to None, in which case will infer whether to flip points from the ``face`` arg
        * references: a list of markers to use as alignment references. String values are one of
            "nw", "ne", "sw", "se". If multiple values supplied, the resulting json will have
            "groups" key on top level, with each group containing the marker string as 'id'
            and its own 'alignment' and 'sites' values, grouping each site to its closest marker.
        * contact: a manually defined contact probe, a tuple of two DPoints.
            Can be None so no "contact" site is added, or can be a list if a different "contact"
            site is needed for each reference
    """
    load_opts = pya.LoadLayoutOptions()
    load_opts.cell_conflict_resolution = pya.LoadLayoutOptions.CellConflictResolution.RenameCell
    view = KLayoutView()
    layout = view.layout
    layout.read(cell_file, load_opts)
    cell = layout.top_cells()[-1]
    return generate_probepoints_json(cell, face, flip_face, references, contact)


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

    parser = argparse.ArgumentParser()

    parser.add_argument("--simulation-export-path", type=str, default=None)

    dir_path = get_simulation_directory(dir_name)

    if dir_path.exists() and dir_path.is_dir():
        remove_content(dir_path)
    else:
        dir_path.mkdir()

    return dir_path


def get_simulation_directory(dir_name):
    """
    Returns directory path consistent with `create_or_empty_tmp_directory`.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("--simulation-export-path", type=str, default=None)
    args, _ = parser.parse_known_args()

    if args.simulation_export_path is not None:
        dir_path=Path(args.simulation_export_path)
    else:
        dir_path = TMP_PATH.joinpath(dir_name)

    return dir_path


def get_active_or_new_layout():
    """Tries to return active layout in GUI or returns new layout when running standalone."""
    try:
        klayoutview = KLayoutView(current=True)
        klayoutview.add_default_layers()
        return klayoutview.layout
    except MissingUILibraryException:
        return pya.Layout()


def write_commit_reference_file(path: Path, write_versions_file=True):
    """
    Writes file COMMIT_REFERENCE into given file path. The file includes current git revision number.
    If git repository is not found in given path, no file is written.
    """
    try:
        with open(path.joinpath('COMMIT_REFERENCE'), 'w') as file:
            for item in VERSION_PATHS.items():
                output = subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL,
                                             cwd=item[1], startupinfo=STARTUPINFO)
                file.write("{} revision number: {}".format(item[0], output.decode('ascii')))

    except subprocess.CalledProcessError:
        return

    if write_versions_file:
        write_export_machine_versions_file(path)

def write_export_machine_versions_file(path: Path):
    """
    Writes file EXPORT_MACHINE_VERSIONS into given file path.
    """
    versions = {}
    versions['platform'] = platform.platform()
    versions['python'] = sys.version_info
    versions['klayout'] = get_klayout_version()

    with open(path.joinpath('EXPORT_MACHINE_VERSIONS.json'), 'w') as file:
        json.dump(versions, file)

def open_with_klayout_or_default_application(filepath):
    """
    Tries to open file with KLayout. If KLayout is not found, opens file with operating system's default application.
    Implementation supports Windows, macOS, and Linux.
    """
    if argv[-1] == "-q":  # quiet mode, do not run viewer
        return

    exe = klayout_executable_command()
    if not exe:
        logging.warning("KLayout executable not found.")
    else:
        subprocess.call((exe, filepath))

def get_klayout_version():
    if is_standalone_session():
        return f"KLayout {importlib.metadata.version('klayout')}"
    else:
        return pya.Application.instance().version()


def export_drc_report(name, path, drc_script=default_drc_runset):
    """Run a DRC script on ``path/name.oas`` and export results in ``path/name_drc_report.lyrdb``."""

    drc_runset_path = os.path.join(DRC_PATH, drc_script)
    input_file = os.path.join(path, f"{name}.oas")
    output_file = os.path.join(path, f"{name}_drc_report.lyrdb")
    logging.info("Exporting DRC report to %s", output_file)

    try:
        subprocess.run([klayout_executable_command(), "-b", "-i",
                        "-r", drc_runset_path,
                        "-rd", f"output={output_file}",
                        input_file
                        ], check=True, startupinfo=STARTUPINFO)
    except subprocess.CalledProcessError as e:
        logging.error(e.output)
