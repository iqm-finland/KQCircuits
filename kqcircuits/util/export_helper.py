import json
from autologging import logged, traced

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.element import get_refpoints
from kqcircuits.defaults import default_layers, default_output_ext, default_output_format, gzip


@logged
@traced
def export_cell(path, cell=None, cell_name="", cell_version=1, layers_to_export=""):
    if cell is None:
        error = ValueError("Cannot export nil cell.")
        export_cell._log.exception(exc_info=error)
        raise error
    layout = cell.layout()
    if (layers_to_export == ""):
        exported_layer_names = [
            "b base metal gap",
            "b base metal gap wo grid",
            "b airbridge pads",
            "b airbridge flyover",
        ]
        layers_to_export = {name: layout.layer(default_layers[name]) for name in exported_layer_names}

    elif (layers_to_export == 'no_sing_layer'):
        layers_to_export = {}

    if (cell_name == ""):
        cell_name = cell.name

    filename = "{}_v{}".format(cell_name, str(cell_version))

    svopt = pya.SaveLayoutOptions()
    svopt.clear_cells()
    svopt.select_all_layers()
    svopt.add_cell(cell.cell_index())
    svopt.format = default_output_format
    file_ext = default_output_ext
    all_layers_file_name = path / "{}{}".format(filename, file_ext)

    layout.write(str(all_layers_file_name), gzip, svopt)

    layer_info = pya.LayerInfo()
    if bool(layers_to_export):
        items = layers_to_export.items()
        for layer_name, layer in items:
            svopt.deselect_all_layers()
            svopt.clear_cells()
            svopt.add_layer(layer, layer_info)
            svopt.add_cell(cell.cell_index())
            svopt.write_context_info = False
            spec_layer_file_name = path / "{} {}{}".format(filename, layer_name, file_ext)
            layout.write(str(spec_layer_file_name), gzip, svopt)


@logged
@traced
def generate_probepoints_json(cell):
    # make autoprober json string for cell with reference points with magical names
    if cell is None:
        error = ValueError("Cannot export probe points corresponding to nil cell.")
        generate_probepoints_json._log.exception(exc_info=error)
        raise error

    layout = cell.layout()

    refpoints = get_refpoints(layout.layer(default_layers["annotations"]), cell)

    # Assumes existence of standard markers
    probe_types = {
        "testarray": {
            "testarrays NW": refpoints["marker_nw"],
            "testarrays SE": refpoints["marker_se"]
        },
        "qb": {
            "qubits NW": refpoints["marker_nw"],
            "qubits SE": refpoints["marker_se"]
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
