# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import json
from autologging import logged, traced

from kqcircuits.elements.element import get_refpoints
from kqcircuits.defaults import default_layers


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

    refpoints = get_refpoints(layout.layer(default_layers["annotations"]), cell)

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
            best_refpoint = None
            best_refpoint_name = None
            for name, refpoint in probe_types[name_parts[0]].items():
                if refpoint.distance(probepoint) < best_distance:
                    best_distance = refpoint.distance(probepoint)
                    best_refpoint = refpoint
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
