# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


import json
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder, encode_python_obj_as_dict


def test_encodes_standard_python_types():
    assert json.dumps(42, cls=GeometryJsonEncoder) == "42", "Integer not encoded correctly"
    assert encode_python_obj_as_dict(42) == 42, "Integer not encoded correctly"
    assert json.dumps(1.23, cls=GeometryJsonEncoder) == "1.23", "Floating number not encoded correctly"
    assert encode_python_obj_as_dict(1.23) == 1.23, "Floating number not encoded correctly"
    assert json.dumps("test_string", cls=GeometryJsonEncoder) == '"test_string"', "String not encoded correctly"
    assert encode_python_obj_as_dict("test_string") == "test_string", "String not encoded correctly"
    assert json.dumps(True, cls=GeometryJsonEncoder) == "true", "Boolean true not encoded correctly"
    assert encode_python_obj_as_dict(True) is True, "Boolean true not encoded correctly"
    assert json.dumps(False, cls=GeometryJsonEncoder) == "false", "Boolean false not encoded correctly"
    assert encode_python_obj_as_dict(False) is False, "Boolean false not encoded correctly"
    assert json.dumps(None, cls=GeometryJsonEncoder) == "null", "Null not encoded correctly"
    assert encode_python_obj_as_dict(None) is None, "Null not encoded correctly"
    list_var = [42, 1.23, "test_string", True, False, None]
    assert (
        json.dumps(list_var, cls=GeometryJsonEncoder) == '[42, 1.23, "test_string", true, false, null]'
    ), "Array not encoded correctly"
    assert encode_python_obj_as_dict(list_var) == list_var, "Array not encoded correctly"
    tuple_var = (42, 1.23, "test_string", True, False, None)
    assert (
        json.dumps(tuple_var, cls=GeometryJsonEncoder) == '[42, 1.23, "test_string", true, false, null]'
    ), "Tuple not encoded correctly"
    assert encode_python_obj_as_dict(tuple_var) == list_var, "Tuple not encoded correctly"
    object_var = {
        "integer": 42,
        "number": 1.23,
        "string": "test_string",
        "bool_true": True,
        "bool_false": False,
        "null_field": None,
        "list": list_var,
        "object": {
            "inner_integer": 42,
            "inner_number": 1.23,
            "inner_string": "test_string",
            "inner_bool_true": True,
            "inner_bool_false": False,
            "inner_null_field": None,
            "inner_list": tuple_var,
        },
    }
    assert json.dumps(object_var, cls=GeometryJsonEncoder) == (
        "{"
        '"integer": 42, '
        '"number": 1.23, '
        '"string": "test_string", '
        '"bool_true": true, '
        '"bool_false": false, '
        '"null_field": null, '
        '"list": [42, 1.23, "test_string", true, false, null], '
        '"object": {'
        '"inner_integer": 42, '
        '"inner_number": 1.23, '
        '"inner_string": "test_string", '
        '"inner_bool_true": true, '
        '"inner_bool_false": false, '
        '"inner_null_field": null, '
        '"inner_list": [42, 1.23, "test_string", true, false, null]'
        "}"
        "}"
    ), "Object not encoded correctly"
    encoded_object_var = encode_python_obj_as_dict(object_var)
    assert "_pya_type" not in encoded_object_var.keys(), "Object not encoded correctly"
    assert set(encoded_object_var.keys()) == set(
        ["integer", "number", "string", "bool_true", "bool_false", "null_field", "list", "object"]
    ), "Object not encoded correctly"
    assert set(encoded_object_var["object"].keys()) == set(
        [
            "inner_integer",
            "inner_number",
            "inner_string",
            "inner_bool_true",
            "inner_bool_false",
            "inner_null_field",
            "inner_list",
        ]
    ), "Object not encoded correctly"
    assert encoded_object_var["integer"] == 42, "Object not encoded correctly"
    assert encoded_object_var["number"] == 1.23, "Object not encoded correctly"
    assert encoded_object_var["string"] == "test_string", "Object not encoded correctly"
    assert encoded_object_var["bool_true"] is True, "Object not encoded correctly"
    assert encoded_object_var["bool_false"] is False, "Object not encoded correctly"
    assert encoded_object_var["null_field"] is None, "Object not encoded correctly"
    assert encoded_object_var["list"] == list_var, "Object not encoded correctly"
    assert encoded_object_var["object"]["inner_integer"] == 42, "Object not encoded correctly"
    assert encoded_object_var["object"]["inner_number"] == 1.23, "Object not encoded correctly"
    assert encoded_object_var["object"]["inner_string"] == "test_string", "Object not encoded correctly"
    assert encoded_object_var["object"]["inner_bool_true"] is True, "Object not encoded correctly"
    assert encoded_object_var["object"]["inner_bool_false"] is False, "Object not encoded correctly"
    assert encoded_object_var["object"]["inner_null_field"] is None, "Object not encoded correctly"
    assert encoded_object_var["object"]["inner_list"] == list_var, "Object not encoded correctly"


def _check_dpoint_dict(encoded_dpoint, expected_x, expected_y, error_msg):
    assert set(encoded_dpoint.keys()) == set(["_pya_type", "x", "y"]), error_msg
    assert encoded_dpoint["_pya_type"] == "DPoint", error_msg
    assert encoded_dpoint["x"] == expected_x, error_msg
    assert encoded_dpoint["y"] == expected_y, error_msg


def test_encodes_dpoint():
    assert (
        json.dumps(pya.DPoint(-1000, 5.67), cls=GeometryJsonEncoder)
        == '{"_pya_type": "DPoint", "x": -1000.0, "y": 5.67}'
    ), "DPoint not encoded correctly"
    encoded_dpoint = encode_python_obj_as_dict(pya.DPoint(-1000, 5.67))
    _check_dpoint_dict(encoded_dpoint, -1000, 5.67, "DPoint not encoded correctly")


def test_encodes_dvector():
    assert (
        json.dumps(pya.DVector(-1000, 5.67), cls=GeometryJsonEncoder)
        == '{"_pya_type": "DVector", "x": -1000.0, "y": 5.67}'
    ), "DVector not encoded correctly"
    encoded_dvector = encode_python_obj_as_dict(pya.DVector(-1000, 5.67))
    assert set(encoded_dvector.keys()) == set(["_pya_type", "x", "y"]), "DVector not encoded correctly"
    assert encoded_dvector["_pya_type"] == "DVector", "DVector not encoded correctly"
    assert encoded_dvector["x"] == -1000, "DVector not encoded correctly"
    assert encoded_dvector["y"] == 5.67, "DVector not encoded correctly"


def test_encodes_dbox():
    dbox_var = pya.DBox(-1000, 5.67, 0, 1234.56)
    assert json.dumps(dbox_var, cls=GeometryJsonEncoder) == (
        "{"
        '"_pya_type": "DBox", '
        '"p1": {"_pya_type": "DPoint", "x": -1000.0, "y": 5.67}, '
        '"p2": {"_pya_type": "DPoint", "x": 0.0, "y": 1234.56}'
        "}"
    ), "DBox not encoded correctly"
    encoded_dbox = encode_python_obj_as_dict(dbox_var)
    assert set(encoded_dbox.keys()) == set(["_pya_type", "p1", "p2"]), "DBox not encoded correctly"
    assert encoded_dbox["_pya_type"] == "DBox", "DBox not encoded correctly"
    _check_dpoint_dict(encoded_dbox["p1"], -1000, 5.67, "DBox not encoded correctly")
    _check_dpoint_dict(encoded_dbox["p2"], 0, 1234.56, "DBox not encoded correctly")


def test_encodes_layerinfo():
    assert (
        json.dumps(pya.LayerInfo(1001, 2), cls=GeometryJsonEncoder)
        == '{"_pya_type": "LayerInfo", "layer": 1001, "datatype": 2}'
    ), "LayerInfo not encoded correctly"
    encoded_layerinfo = encode_python_obj_as_dict(pya.LayerInfo(1001, 2))
    assert set(encoded_layerinfo.keys()) == set(["_pya_type", "layer", "datatype"]), "LayerInfo not encoded correctly"
    assert encoded_layerinfo["_pya_type"] == "LayerInfo", "LayerInfo not encoded correctly"
    assert encoded_layerinfo["layer"] == 1001, "LayerInfo not encoded correctly"
    assert encoded_layerinfo["datatype"] == 2, "LayerInfo not encoded correctly"


def test_encodes_dpath():
    dpath_var = pya.DPath([pya.DPoint(1.2, 3), pya.DPoint(-3.4, 5), pya.DPoint(6, -7.8), pya.DPoint(-1000, 1000)], 13)
    assert json.dumps(dpath_var, cls=GeometryJsonEncoder) == (
        "{"
        '"_pya_type": "DPath", '
        '"points": ['
        '{"_pya_type": "DPoint", "x": 1.2, "y": 3.0}, '
        '{"_pya_type": "DPoint", "x": -3.4, "y": 5.0}, '
        '{"_pya_type": "DPoint", "x": 6.0, "y": -7.8}, '
        '{"_pya_type": "DPoint", "x": -1000.0, "y": 1000.0}'
        '], "width": 13.0}'
    ), "DPath not encoded correctly"
    encoded_dpath = encode_python_obj_as_dict(dpath_var)
    assert set(encoded_dpath.keys()) == set(["_pya_type", "points", "width"]), "DPath not encoded correctly"
    assert encoded_dpath["_pya_type"] == "DPath", "DPath not encoded correctly"
    assert encoded_dpath["width"] == 13, "DPath not encoded correctly"
    assert len(encoded_dpath["points"]) == 4, "DPath not encoded correctly"
    _check_dpoint_dict(encoded_dpath["points"][0], 1.2, 3, "DPath not encoded correctly")
    _check_dpoint_dict(encoded_dpath["points"][1], -3.4, 5, "DPath not encoded correctly")
    _check_dpoint_dict(encoded_dpath["points"][2], 6, -7.8, "DPath not encoded correctly")
    _check_dpoint_dict(encoded_dpath["points"][3], -1000, 1000, "DPath not encoded correctly")


def test_encodes_dedge():
    dedge_var = pya.DEdge(-1000, 5.67, 0, 1234.56)
    assert json.dumps(dedge_var, cls=GeometryJsonEncoder) == (
        "{"
        '"_pya_type": "DEdge", '
        '"p1": {"_pya_type": "DPoint", "x": -1000.0, "y": 5.67}, '
        '"p2": {"_pya_type": "DPoint", "x": 0.0, "y": 1234.56}'
        "}"
    ), "DEdge not encoded correctly"
    encoded_dedge = encode_python_obj_as_dict(dedge_var)
    assert set(encoded_dedge.keys()) == set(["_pya_type", "p1", "p2"]), "DEdge not encoded correctly"
    assert encoded_dedge["_pya_type"] == "DEdge", "DEdge not encoded correctly"
    _check_dpoint_dict(encoded_dedge["p1"], -1000, 5.67, "DEdge not encoded correctly")
    _check_dpoint_dict(encoded_dedge["p2"], 0, 1234.56, "DEdge not encoded correctly")


def test_encodes_dpolygon():
    encoded_dpolygon = encode_python_obj_as_dict(
        pya.DPolygon([pya.DPoint(1.2, 3), pya.DPoint(-3.4, 5), pya.DPoint(6, -7.8), pya.DPoint(-1000, 1000)])
    )
    assert set(encoded_dpolygon.keys()) == set(["_pya_type", "hull", "holes"]), "DPolygon not encoded correctly"
    assert encoded_dpolygon["_pya_type"] == "DPolygon", "DPolygon not encoded correctly"
    assert len(encoded_dpolygon["hull"]) == 4, "DPolygon not encoded correctly"
    sorted_points = sorted(encoded_dpolygon["hull"], key=lambda p: p["x"])
    _check_dpoint_dict(sorted_points[0], -1000, 1000, "DPolygon not encoded correctly")
    _check_dpoint_dict(sorted_points[1], -3.4, 5, "DPolygon not encoded correctly")
    _check_dpoint_dict(sorted_points[2], 1.2, 3, "DPolygon not encoded correctly")
    _check_dpoint_dict(sorted_points[3], 6, -7.8, "DPolygon not encoded correctly")
    assert len(encoded_dpolygon["holes"]) == 0, "DPolygon not encoded correctly"


def test_encodes_dpolygon_with_holes():
    dpolygon = pya.DPolygon(
        [pya.DPoint(-1001, -1000), pya.DPoint(999, -1000), pya.DPoint(1001, 1000), pya.DPoint(-1000, 1000)]
    )
    dpolygon.insert_hole([pya.DPoint(-900, -900), pya.DPoint(-500, -500), pya.DPoint(-300, -900)])
    dpolygon.insert_hole([pya.DPoint(900, 900), pya.DPoint(500, 500), pya.DPoint(300, 900)])
    encoded_dpolygon = encode_python_obj_as_dict(dpolygon)
    assert set(encoded_dpolygon.keys()) == set(["_pya_type", "hull", "holes"]), "DPolygon not encoded correctly"
    assert encoded_dpolygon["_pya_type"] == "DPolygon", "DPolygon not encoded correctly"
    assert len(encoded_dpolygon["hull"]) == 4, "DPolygon not encoded correctly"
    sorted_points = sorted(encoded_dpolygon["hull"], key=lambda p: p["x"])
    _check_dpoint_dict(sorted_points[0], -1001, -1000, "DPolygon not encoded correctly")
    _check_dpoint_dict(sorted_points[1], -1000, 1000, "DPolygon not encoded correctly")
    _check_dpoint_dict(sorted_points[2], 999, -1000, "DPolygon not encoded correctly")
    _check_dpoint_dict(sorted_points[3], 1001, 1000, "DPolygon not encoded correctly")
    assert len(encoded_dpolygon["holes"]) == 2, "DPolygon not encoded correctly"
    assert len(encoded_dpolygon["holes"][0]) == 3, "DPolygon not encoded correctly"
    assert len(encoded_dpolygon["holes"][1]) == 3, "DPolygon not encoded correctly"
    sorted_hole1 = sorted(encoded_dpolygon["holes"][0], key=lambda p: p["x"])
    sorted_hole2 = sorted(encoded_dpolygon["holes"][1], key=lambda p: p["x"])
    _check_dpoint_dict(sorted_hole1[0], -900, -900, "DPolygon not encoded correctly")
    _check_dpoint_dict(sorted_hole1[1], -500, -500, "DPolygon not encoded correctly")
    _check_dpoint_dict(sorted_hole1[2], -300, -900, "DPolygon not encoded correctly")
    _check_dpoint_dict(sorted_hole2[0], 300, 900, "DPolygon not encoded correctly")
    _check_dpoint_dict(sorted_hole2[1], 500, 500, "DPolygon not encoded correctly")
    _check_dpoint_dict(sorted_hole2[2], 900, 900, "DPolygon not encoded correctly")


def test_encode_composite_dict():
    dpolygon = pya.DPolygon(
        [pya.DPoint(-1001, -1000), pya.DPoint(999, -1000), pya.DPoint(1001, 1000), pya.DPoint(-1000, 1000)]
    )
    dpolygon.insert_hole([pya.DPoint(-900, -900), pya.DPoint(-500, -500), pya.DPoint(-300, -900)])
    dpolygon.insert_hole([pya.DPoint(900, 900), pya.DPoint(500, 500), pya.DPoint(300, 900)])
    test_dict = {
        "test_layer": pya.LayerInfo(1001, 2),
        "test_vectors": [pya.DVector(1.2, 3), pya.DVector(-3.4, 5), None, pya.DVector(-1000, 1000)],
        "test_point_sets": {
            "path": pya.DPath([pya.DPoint(0, -1), pya.DPoint(1, 0), pya.DPoint(0.33, 0.66)], 6.5),
            "polygon": dpolygon,
            "just_points": [pya.DPoint(-2, 2), pya.DPoint(1, -1), pya.DPoint(1.33, 2.66)],
        },
        "random_string": "I am a random string",
        "deep_hierarchy": {
            "very_deep_hierarchy": {"edge": pya.DEdge(-123.45, 54.321, 13.421, 45.231)},
            "box": pya.DBox(-98.765, -89.763, 67.876, 789.87),
        },
    }
    encoded_dict = encode_python_obj_as_dict(test_dict)
    assert "_pya_type" not in encoded_dict, "Dict with pya shapes not encoded correctly"
    assert set(encoded_dict.keys()) == set(
        ["test_layer", "test_vectors", "test_point_sets", "random_string", "deep_hierarchy"]
    ), "Dict with pya shapes not encoded correctly"

    assert set(encoded_dict["test_layer"].keys()) == set(
        ["_pya_type", "layer", "datatype"]
    ), "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_layer"]["_pya_type"] == "LayerInfo", "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_layer"]["layer"] == 1001, "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_layer"]["datatype"] == 2, "Dict with pya shapes not encoded correctly"

    assert len(encoded_dict["test_vectors"]) == 4, "Dict with pya shapes not encoded correctly"
    assert set(encoded_dict["test_vectors"][0].keys()) == set(
        ["_pya_type", "x", "y"]
    ), "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_vectors"][0]["_pya_type"] == "DVector", "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_vectors"][0]["x"] == 1.2, "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_vectors"][0]["y"] == 3, "Dict with pya shapes not encoded correctly"

    assert set(encoded_dict["test_vectors"][1].keys()) == set(
        ["_pya_type", "x", "y"]
    ), "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_vectors"][1]["_pya_type"] == "DVector", "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_vectors"][1]["x"] == -3.4, "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_vectors"][1]["y"] == 5, "Dict with pya shapes not encoded correctly"

    assert encoded_dict["test_vectors"][2] is None, "Dict with pya shapes not encoded correctly"

    assert set(encoded_dict["test_vectors"][3].keys()) == set(
        ["_pya_type", "x", "y"]
    ), "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_vectors"][3]["_pya_type"] == "DVector", "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_vectors"][3]["x"] == -1000, "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_vectors"][3]["y"] == 1000, "Dict with pya shapes not encoded correctly"

    assert "_pya_type" not in encoded_dict["test_point_sets"], "Dict with pya shapes not encoded correctly"
    assert set(encoded_dict["test_point_sets"].keys()) == set(
        ["path", "polygon", "just_points"]
    ), "Dict with pya shapes not encoded correctly"

    assert set(encoded_dict["test_point_sets"]["path"].keys()) == set(
        ["_pya_type", "points", "width"]
    ), "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_point_sets"]["path"]["_pya_type"] == "DPath", "Dict with pya shapes not encoded correctly"
    assert encoded_dict["test_point_sets"]["path"]["width"] == 6.5, "Dict with pya shapes not encoded correctly"
    assert len(encoded_dict["test_point_sets"]["path"]["points"]) == 3, "Dict with pya shapes not encoded correctly"
    _check_dpoint_dict(
        encoded_dict["test_point_sets"]["path"]["points"][0], 0, -1, "Dict with pya shapes not encoded correctly"
    )
    _check_dpoint_dict(
        encoded_dict["test_point_sets"]["path"]["points"][1], 1, 0, "Dict with pya shapes not encoded correctly"
    )
    _check_dpoint_dict(
        encoded_dict["test_point_sets"]["path"]["points"][2], 0.33, 0.66, "Dict with pya shapes not encoded correctly"
    )

    assert set(encoded_dict["test_point_sets"]["polygon"].keys()) == set(
        ["_pya_type", "hull", "holes"]
    ), "Dict with pya shapes not encoded correctly"
    assert (
        encoded_dict["test_point_sets"]["polygon"]["_pya_type"] == "DPolygon"
    ), "Dict with pya shapes not encoded correctly"
    sorted_points = sorted(encoded_dict["test_point_sets"]["polygon"]["hull"], key=lambda p: p["x"])
    assert len(sorted_points) == 4, "Dict with pya shapes not encoded correctly"
    _check_dpoint_dict(sorted_points[0], -1001, -1000, "Dict with pya shapes not encoded correctly")
    _check_dpoint_dict(sorted_points[1], -1000, 1000, "Dict with pya shapes not encoded correctly")
    _check_dpoint_dict(sorted_points[2], 999, -1000, "Dict with pya shapes not encoded correctly")
    _check_dpoint_dict(sorted_points[3], 1001, 1000, "Dict with pya shapes not encoded correctly")
    assert len(encoded_dict["test_point_sets"]["polygon"]["holes"]) == 2, "Dict with pya shapes not encoded correctly"
    assert (
        len(encoded_dict["test_point_sets"]["polygon"]["holes"][0]) == 3
    ), "Dict with pya shapes not encoded correctly"
    assert (
        len(encoded_dict["test_point_sets"]["polygon"]["holes"][1]) == 3
    ), "Dict with pya shapes not encoded correctly"
    sorted_hole1 = sorted(encoded_dict["test_point_sets"]["polygon"]["holes"][0], key=lambda p: p["x"])
    sorted_hole2 = sorted(encoded_dict["test_point_sets"]["polygon"]["holes"][1], key=lambda p: p["x"])
    _check_dpoint_dict(sorted_hole1[0], -900, -900, "Dict with pya shapes not encoded correctly")
    _check_dpoint_dict(sorted_hole1[1], -500, -500, "Dict with pya shapes not encoded correctly")
    _check_dpoint_dict(sorted_hole1[2], -300, -900, "Dict with pya shapes not encoded correctly")
    _check_dpoint_dict(sorted_hole2[0], 300, 900, "Dict with pya shapes not encoded correctly")
    _check_dpoint_dict(sorted_hole2[1], 500, 500, "Dict with pya shapes not encoded correctly")
    _check_dpoint_dict(sorted_hole2[2], 900, 900, "Dict with pya shapes not encoded correctly")

    assert len(encoded_dict["test_point_sets"]["just_points"]) == 3, "Dict with pya shapes not encoded correctly"
    _check_dpoint_dict(
        encoded_dict["test_point_sets"]["just_points"][0], -2, 2, "Dict with pya shapes not encoded correctly"
    )
    _check_dpoint_dict(
        encoded_dict["test_point_sets"]["just_points"][1], 1, -1, "Dict with pya shapes not encoded correctly"
    )
    _check_dpoint_dict(
        encoded_dict["test_point_sets"]["just_points"][2], 1.33, 2.66, "Dict with pya shapes not encoded correctly"
    )

    assert encoded_dict["random_string"] == "I am a random string", "Dict with pya shapes not encoded correctly"

    assert "_pya_type" not in encoded_dict["deep_hierarchy"], "Dict with pya shapes not encoded correctly"
    assert set(encoded_dict["deep_hierarchy"].keys()) == set(
        ["very_deep_hierarchy", "box"]
    ), "Dict with pya shapes not encoded correctly"
    assert (
        "_pya_type" not in encoded_dict["deep_hierarchy"]["very_deep_hierarchy"]
    ), "Dict with pya shapes not encoded correctly"
    assert set(encoded_dict["deep_hierarchy"]["very_deep_hierarchy"].keys()) == set(
        ["edge"]
    ), "Dict with pya shapes not encoded correctly"

    assert set(encoded_dict["deep_hierarchy"]["very_deep_hierarchy"]["edge"].keys()) == set(
        ["_pya_type", "p1", "p2"]
    ), "Dict with pya shapes not encoded correctly"
    assert (
        encoded_dict["deep_hierarchy"]["very_deep_hierarchy"]["edge"]["_pya_type"] == "DEdge"
    ), "Dict with pya shapes not encoded correctly"
    _check_dpoint_dict(
        encoded_dict["deep_hierarchy"]["very_deep_hierarchy"]["edge"]["p1"],
        -123.45,
        54.321,
        "Dict with pya shapes not encoded correctly",
    )
    _check_dpoint_dict(
        encoded_dict["deep_hierarchy"]["very_deep_hierarchy"]["edge"]["p2"],
        13.421,
        45.231,
        "Dict with pya shapes not encoded correctly",
    )

    assert set(encoded_dict["deep_hierarchy"]["box"].keys()) == set(
        ["_pya_type", "p1", "p2"]
    ), "Dict with pya shapes not encoded correctly"
    assert encoded_dict["deep_hierarchy"]["box"]["_pya_type"] == "DBox", "Dict with pya shapes not encoded correctly"
    _check_dpoint_dict(
        encoded_dict["deep_hierarchy"]["box"]["p1"], -98.765, -89.763, "Dict with pya shapes not encoded correctly"
    )
    _check_dpoint_dict(
        encoded_dict["deep_hierarchy"]["box"]["p2"], 67.876, 789.87, "Dict with pya shapes not encoded correctly"
    )
