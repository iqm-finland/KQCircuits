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
from kqcircuits.util.geometry_json_encoder import GeometryJsonDecoder, decode_dict_as_python_obj


def test_decodes_standard_python_types():
    assert json.loads("42", cls=GeometryJsonDecoder) == 42, "Integer not decoded correctly"
    assert decode_dict_as_python_obj(42) == 42, "Integer not decoded correctly"
    assert json.loads("1.23", cls=GeometryJsonDecoder) == 1.23, "Floating number not decoded correctly"
    assert decode_dict_as_python_obj(1.23) == 1.23, "Floating number not decoded correctly"
    assert json.loads('"test_string"', cls=GeometryJsonDecoder) == "test_string", "String not decoded correctly"
    assert decode_dict_as_python_obj("test_string") == "test_string", "String not decoded correctly"
    assert json.loads("true", cls=GeometryJsonDecoder) is True, "Boolean true not decoded correctly"
    assert decode_dict_as_python_obj(True) is True, "Boolean true not decoded correctly"
    assert json.loads("false", cls=GeometryJsonDecoder) is False, "Boolean false not decoded correctly"
    assert decode_dict_as_python_obj(False) is False, "Boolean false not decoded correctly"
    assert json.loads("null", cls=GeometryJsonDecoder) is None, "Null not decoded correctly"
    assert decode_dict_as_python_obj(None) is None, "Null not decoded correctly"
    list_var = [42, 1.23, "test_string", True, False, None]
    assert (
        json.loads('[42, 1.23, "test_string", true, false, null]', cls=GeometryJsonDecoder) == list_var
    ), "Array not decoded correctly"
    assert decode_dict_as_python_obj(list_var) == list_var, "Array not decoded correctly"


def test_dont_decode_dpoint_by_mistake():
    json_dpoint = json.loads('{"x": -1000, "y": 5.67}', cls=GeometryJsonDecoder)
    assert isinstance(json_dpoint, dict), "Object not decoded correctly"
    assert "_pya_type" not in json_dpoint, "Object not decoded correctly"
    assert set(json_dpoint.keys()) == set(["x", "y"]), "Object not decoded correctly"
    assert json_dpoint["x"] == -1000 and json_dpoint["y"] == 5.67, "Object not decoded correctly"
    decoded_dpoint = decode_dict_as_python_obj({"x": -1000, "y": 5.67})
    assert isinstance(decoded_dpoint, dict), "Object not decoded correctly"
    assert "_pya_type" not in decoded_dpoint, "Object not decoded correctly"
    assert set(decoded_dpoint.keys()) == set(["x", "y"]), "Object not decoded correctly"
    assert decoded_dpoint["x"] == -1000 and decoded_dpoint["y"] == 5.67, "Object not decoded correctly"


def test_decodes_standard_dicts():
    list_var = [42, 1.23, "test_string", True, False, None]
    json_var = json.loads(
        """
    {
        "integer": 42,
        "number": 1.23,
        "string": "test_string",
        "bool_true": true,
        "bool_false": false,
        "null_field": null,
        "list": [42, 1.23, "test_string", true, false, null],
        "object": {
            "inner_integer": 42,
            "inner_number": 1.23,
            "inner_string": "test_string",
            "inner_bool_true": true,
            "inner_bool_false": false,
            "inner_null_field": null,
            "inner_list": [42, 1.23, "test_string", true, false, null]
        }
    }
    """,
        cls=GeometryJsonDecoder,
    )
    assert "_pya_type" not in json_var.keys(), "Object not decoded correctly"
    assert set(json_var.keys()) == set(
        ["integer", "number", "string", "bool_true", "bool_false", "null_field", "list", "object"]
    ), "Object not decoded correctly"
    assert set(json_var["object"].keys()) == set(
        [
            "inner_integer",
            "inner_number",
            "inner_string",
            "inner_bool_true",
            "inner_bool_false",
            "inner_null_field",
            "inner_list",
        ]
    ), "Object not decoded correctly"
    assert json_var["integer"] == 42, "Object not decoded correctly"
    assert json_var["number"] == 1.23, "Object not decoded correctly"
    assert json_var["string"] == "test_string", "Object not decoded correctly"
    assert json_var["bool_true"] is True, "Object not decoded correctly"
    assert json_var["bool_false"] is False, "Object not decoded correctly"
    assert json_var["null_field"] is None, "Object not decoded correctly"
    assert json_var["list"] == list_var, "Object not decoded correctly"
    assert json_var["object"]["inner_integer"] == 42, "Object not decoded correctly"
    assert json_var["object"]["inner_number"] == 1.23, "Object not decoded correctly"
    assert json_var["object"]["inner_string"] == "test_string", "Object not decoded correctly"
    assert json_var["object"]["inner_bool_true"] is True, "Object not decoded correctly"
    assert json_var["object"]["inner_bool_false"] is False, "Object not decoded correctly"
    assert json_var["object"]["inner_null_field"] is None, "Object not decoded correctly"
    assert json_var["object"]["inner_list"] == list_var, "Object not decoded correctly"

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
            "inner_list": list_var,
        },
    }
    decoded_object_var = decode_dict_as_python_obj(object_var)
    assert "_pya_type" not in decoded_object_var.keys(), "Object not decoded correctly"
    assert set(decoded_object_var.keys()) == set(
        ["integer", "number", "string", "bool_true", "bool_false", "null_field", "list", "object"]
    ), "Object not decoded correctly"
    assert set(decoded_object_var["object"].keys()) == set(
        [
            "inner_integer",
            "inner_number",
            "inner_string",
            "inner_bool_true",
            "inner_bool_false",
            "inner_null_field",
            "inner_list",
        ]
    ), "Object not decoded correctly"
    assert decoded_object_var["integer"] == 42, "Object not decoded correctly"
    assert decoded_object_var["number"] == 1.23, "Object not decoded correctly"
    assert decoded_object_var["string"] == "test_string", "Object not decoded correctly"
    assert decoded_object_var["bool_true"] is True, "Object not decoded correctly"
    assert decoded_object_var["bool_false"] is False, "Object not decoded correctly"
    assert decoded_object_var["null_field"] is None, "Object not decoded correctly"
    assert decoded_object_var["list"] == list_var, "Object not decoded correctly"
    assert decoded_object_var["object"]["inner_integer"] == 42, "Object not decoded correctly"
    assert decoded_object_var["object"]["inner_number"] == 1.23, "Object not decoded correctly"
    assert decoded_object_var["object"]["inner_string"] == "test_string", "Object not decoded correctly"
    assert decoded_object_var["object"]["inner_bool_true"] is True, "Object not decoded correctly"
    assert decoded_object_var["object"]["inner_bool_false"] is False, "Object not decoded correctly"
    assert decoded_object_var["object"]["inner_null_field"] is None, "Object not decoded correctly"
    assert decoded_object_var["object"]["inner_list"] == list_var, "Object not decoded correctly"


def _check_dpoint_obj(decoded_dpoint, expected_x, expected_y, error_msg):
    assert isinstance(decoded_dpoint, pya.DPoint), error_msg
    assert decoded_dpoint.x == expected_x, error_msg
    assert decoded_dpoint.y == expected_y, error_msg


def test_decodes_dpoint():
    json_dpoint = json.loads('{"_pya_type": "DPoint", "x": -1000, "y": 5.67}', cls=GeometryJsonDecoder)
    _check_dpoint_obj(json_dpoint, -1000, 5.67, "DPoint not decoded correctly")
    decoded_dpoint = decode_dict_as_python_obj({"_pya_type": "DPoint", "x": -1000, "y": 5.67})
    _check_dpoint_obj(decoded_dpoint, -1000, 5.67, "DPoint not decoded correctly")


def test_decodes_dvector():
    json_dvector = json.loads('{"_pya_type": "DVector", "x": -1000, "y": 5.67}', cls=GeometryJsonDecoder)
    assert isinstance(json_dvector, pya.DVector), "DVector not decoded correctly"
    assert json_dvector.x == -1000, "DVector not decoded correctly"
    assert json_dvector.y == 5.67, "DVector not decoded correctly"
    decoded_dvector = decode_dict_as_python_obj({"_pya_type": "DVector", "x": -1000, "y": 5.67})
    assert isinstance(decoded_dvector, pya.DVector), "DVector not decoded correctly"
    assert decoded_dvector.x == -1000, "DVector not decoded correctly"
    assert decoded_dvector.y == 5.67, "DVector not decoded correctly"


def test_decodes_dbox():
    json_dbox = json.loads(
        """{
        "_pya_type": "DBox",
        "p1": {"_pya_type": "DPoint", "x": -1000.0, "y": 5.67},
        "p2": {"_pya_type": "DPoint", "x": 0.0, "y": 1234.56}
    }""",
        cls=GeometryJsonDecoder,
    )
    assert isinstance(json_dbox, pya.DBox), "DBox not decoded correctly"
    assert (
        json_dbox.left == -1000 and json_dbox.bottom == 5.67 and json_dbox.right == 0 and json_dbox.top == 1234.56
    ), "DBox not decoded correctly"
    decoded_dbox = decode_dict_as_python_obj(
        {
            "_pya_type": "DBox",
            "p1": {"_pya_type": "DPoint", "x": -1000, "y": 5.67},
            "p2": {"_pya_type": "DPoint", "x": 0, "y": 1234.56},
        }
    )
    assert isinstance(decoded_dbox, pya.DBox), "DBox not decoded correctly"
    assert (
        decoded_dbox.left == -1000
        and decoded_dbox.bottom == 5.67
        and decoded_dbox.right == 0
        and decoded_dbox.top == 1234.56
    ), "DBox not decoded correctly"


def test_decodes_layerinfo():
    json_layerinfo = json.loads('{"_pya_type": "LayerInfo", "layer": 1001, "datatype": 2}', cls=GeometryJsonDecoder)
    assert isinstance(json_layerinfo, pya.LayerInfo), "LayerInfo not decoded correctly"
    assert json_layerinfo.layer == 1001 and json_layerinfo.datatype == 2, "LayerInfo not decoded correctly"
    decoded_layerinfo = decode_dict_as_python_obj({"_pya_type": "LayerInfo", "layer": 1001, "datatype": 2})
    assert isinstance(decoded_layerinfo, pya.LayerInfo), "LayerInfo not decoded correctly"
    assert decoded_layerinfo.layer == 1001 and decoded_layerinfo.datatype == 2, "LayerInfo not decoded correctly"


def test_decodes_dpath():
    json_dpath = json.loads(
        """{
        "_pya_type": "DPath",
        "points": [
            {"_pya_type": "DPoint", "x": 1.2, "y": 3},
            {"_pya_type": "DPoint", "x": -3.4, "y": 5},
            {"_pya_type": "DPoint", "x": 6, "y": -7.8},
            {"_pya_type": "DPoint", "x": -1000, "y": 1000}
        ], "width": 13}""",
        cls=GeometryJsonDecoder,
    )
    assert isinstance(json_dpath, pya.DPath), "DPath not decoded correctly"
    assert json_dpath.width == 13, "DPath not decoded correctly"
    json_points = list(json_dpath.each_point())
    assert len(json_points) == 4, "DPath not decoded correctly"
    _check_dpoint_obj(json_points[0], 1.2, 3, "DPath not decoded correctly")
    _check_dpoint_obj(json_points[1], -3.4, 5, "DPath not decoded correctly")
    _check_dpoint_obj(json_points[2], 6, -7.8, "DPath not decoded correctly")
    _check_dpoint_obj(json_points[3], -1000, 1000, "DPath not decoded correctly")
    decoded_dpath = decode_dict_as_python_obj(
        {
            "_pya_type": "DPath",
            "width": 13,
            "points": [
                {"_pya_type": "DPoint", "x": 1.2, "y": 3},
                {"_pya_type": "DPoint", "x": -3.4, "y": 5},
                {"_pya_type": "DPoint", "x": 6, "y": -7.8},
                {"_pya_type": "DPoint", "x": -1000, "y": 1000},
            ],
        }
    )
    assert isinstance(decoded_dpath, pya.DPath), "DPath not decoded correctly"
    assert decoded_dpath.width == 13, "DPath not decoded correctly"
    decoded_points = list(decoded_dpath.each_point())
    assert len(decoded_points) == 4, "DPath not decoded correctly"
    _check_dpoint_obj(decoded_points[0], 1.2, 3, "DPath not decoded correctly")
    _check_dpoint_obj(decoded_points[1], -3.4, 5, "DPath not decoded correctly")
    _check_dpoint_obj(decoded_points[2], 6, -7.8, "DPath not decoded correctly")
    _check_dpoint_obj(decoded_points[3], -1000, 1000, "DPath not decoded correctly")


def test_decodes_dedge():
    json_dedge = json.loads(
        """{
        "_pya_type": "DEdge",
        "p1": {"_pya_type": "DPoint", "x": -1000.0, "y": 5.67},
        "p2": {"_pya_type": "DPoint", "x": 0.0, "y": 1234.56}
    }""",
        cls=GeometryJsonDecoder,
    )
    assert isinstance(json_dedge, pya.DEdge), "DEdge not decoded correctly"
    assert (
        json_dedge.x1 == -1000 and json_dedge.y1 == 5.67 and json_dedge.x2 == 0 and json_dedge.y2 == 1234.56
    ), "DEdge not decoded correctly"
    decoded_dedge = decode_dict_as_python_obj(
        {
            "_pya_type": "DEdge",
            "p1": {"_pya_type": "DPoint", "x": -1000, "y": 5.67},
            "p2": {"_pya_type": "DPoint", "x": 0, "y": 1234.56},
        }
    )
    assert isinstance(decoded_dedge, pya.DEdge), "DEdge not decoded correctly"
    assert (
        decoded_dedge.x1 == -1000 and decoded_dedge.y1 == 5.67 and decoded_dedge.x2 == 0 and decoded_dedge.y2 == 1234.56
    ), "DEdge not decoded correctly"


def test_decodes_dpolygon():
    json_dpolygon = json.loads(
        """{
        "_pya_type": "DPolygon",
        "hull": [
            {"_pya_type": "DPoint", "x": 1.2, "y": 3},
            {"_pya_type": "DPoint", "x": -3.4, "y": 5},
            {"_pya_type": "DPoint", "x": 6, "y": -7.8},
            {"_pya_type": "DPoint", "x": -1000, "y": 1000}
        ],
        "holes": []
    }""",
        cls=GeometryJsonDecoder,
    )
    assert isinstance(json_dpolygon, pya.DPolygon), "DPolygon not decoded correctly"
    json_points = sorted(list(json_dpolygon.each_point_hull()), key=lambda p: p.x)
    assert len(json_points) == 4, "DPolygon not decoded correctly"
    _check_dpoint_obj(json_points[0], -1000, 1000, "DPolygon not decoded correctly")
    _check_dpoint_obj(json_points[1], -3.4, 5, "DPolygon not decoded correctly")
    _check_dpoint_obj(json_points[2], 1.2, 3, "DPolygon not decoded correctly")
    _check_dpoint_obj(json_points[3], 6, -7.8, "DPolygon not decoded correctly")
    decoded_dpolygon = decode_dict_as_python_obj(
        {
            "_pya_type": "DPolygon",
            "hull": [
                {"_pya_type": "DPoint", "x": 1.2, "y": 3},
                {"_pya_type": "DPoint", "x": -3.4, "y": 5},
                {"_pya_type": "DPoint", "x": 6, "y": -7.8},
                {"_pya_type": "DPoint", "x": -1000, "y": 1000},
            ],
            "holes": [],
        }
    )
    assert isinstance(decoded_dpolygon, pya.DPolygon), "DPolygon not decoded correctly"
    decoded_points = sorted(list(decoded_dpolygon.each_point_hull()), key=lambda p: p.x)
    assert len(decoded_points) == 4, "DPolygon not decoded correctly"
    _check_dpoint_obj(decoded_points[0], -1000, 1000, "DPolygon not decoded correctly")
    _check_dpoint_obj(decoded_points[1], -3.4, 5, "DPolygon not decoded correctly")
    _check_dpoint_obj(decoded_points[2], 1.2, 3, "DPolygon not decoded correctly")
    _check_dpoint_obj(decoded_points[3], 6, -7.8, "DPolygon not decoded correctly")


def test_decodes_dpolygon_with_holes():
    json_dpolygon = json.loads(
        """{
        "_pya_type": "DPolygon",
        "hull": [
            {"_pya_type": "DPoint", "x": -1001, "y": -1000},
            {"_pya_type": "DPoint", "x": 999, "y": -1000},
            {"_pya_type": "DPoint", "x": 1001, "y": 1000},
            {"_pya_type": "DPoint", "x": -1000, "y": 1000}
        ],
        "holes": [
            [
                {"_pya_type": "DPoint", "x": -900, "y": -900},
                {"_pya_type": "DPoint", "x": -500, "y": -500},
                {"_pya_type": "DPoint", "x": -300, "y": -900}
            ],
            [
                {"_pya_type": "DPoint", "x": 900, "y": 900},
                {"_pya_type": "DPoint", "x": 500, "y": 500},
                {"_pya_type": "DPoint", "x": 300, "y": 900}
            ]
        ]
    }""",
        cls=GeometryJsonDecoder,
    )
    assert isinstance(json_dpolygon, pya.DPolygon), "DPolygon not decoded correctly"
    json_points = sorted(list(json_dpolygon.each_point_hull()), key=lambda p: p.x)
    assert len(json_points) == 4, "DPolygon not decoded correctly"
    _check_dpoint_obj(json_points[0], -1001, -1000, "DPolygon not decoded correctly")
    _check_dpoint_obj(json_points[1], -1000, 1000, "DPolygon not decoded correctly")
    _check_dpoint_obj(json_points[2], 999, -1000, "DPolygon not decoded correctly")
    _check_dpoint_obj(json_points[3], 1001, 1000, "DPolygon not decoded correctly")
    assert json_dpolygon.holes() == 2, "DPolygon not decoded correctly"
    hole1_points = sorted(list(json_dpolygon.each_point_hole(0)), key=lambda p: p.x)
    assert len(hole1_points) == 3, "DPolygon not decoded correctly"
    _check_dpoint_obj(hole1_points[0], -900, -900, "DPolygon not decoded correctly")
    _check_dpoint_obj(hole1_points[1], -500, -500, "DPolygon not decoded correctly")
    _check_dpoint_obj(hole1_points[2], -300, -900, "DPolygon not decoded correctly")
    hole2_points = sorted(list(json_dpolygon.each_point_hole(1)), key=lambda p: p.x)
    assert len(hole2_points) == 3, "DPolygon not decoded correctly"
    _check_dpoint_obj(hole2_points[0], 300, 900, "DPolygon not decoded correctly")
    _check_dpoint_obj(hole2_points[1], 500, 500, "DPolygon not decoded correctly")
    _check_dpoint_obj(hole2_points[2], 900, 900, "DPolygon not decoded correctly")

    decoded_dpolygon = decode_dict_as_python_obj(
        {
            "_pya_type": "DPolygon",
            "hull": [
                {"_pya_type": "DPoint", "x": -1001, "y": -1000},
                {"_pya_type": "DPoint", "x": 999, "y": -1000},
                {"_pya_type": "DPoint", "x": 1001, "y": 1000},
                {"_pya_type": "DPoint", "x": -1000, "y": 1000},
            ],
            "holes": [
                [
                    {"_pya_type": "DPoint", "x": -900, "y": -900},
                    {"_pya_type": "DPoint", "x": -500, "y": -500},
                    {"_pya_type": "DPoint", "x": -300, "y": -900},
                ],
                [
                    {"_pya_type": "DPoint", "x": 900, "y": 900},
                    {"_pya_type": "DPoint", "x": 500, "y": 500},
                    {"_pya_type": "DPoint", "x": 300, "y": 900},
                ],
            ],
        }
    )
    assert isinstance(decoded_dpolygon, pya.DPolygon), "DPolygon not decoded correctly"
    decoded_points = sorted(list(decoded_dpolygon.each_point_hull()), key=lambda p: p.x)
    assert len(decoded_points) == 4, "DPolygon not decoded correctly"
    _check_dpoint_obj(decoded_points[0], -1001, -1000, "DPolygon not decoded correctly")
    _check_dpoint_obj(decoded_points[1], -1000, 1000, "DPolygon not decoded correctly")
    _check_dpoint_obj(decoded_points[2], 999, -1000, "DPolygon not decoded correctly")
    _check_dpoint_obj(decoded_points[3], 1001, 1000, "DPolygon not decoded correctly")
    assert decoded_dpolygon.holes() == 2, "DPolygon not decoded correctly"
    decoded_hole1_points = sorted(list(decoded_dpolygon.each_point_hole(0)), key=lambda p: p.x)
    assert len(decoded_hole1_points) == 3, "DPolygon not decoded correctly"
    _check_dpoint_obj(decoded_hole1_points[0], -900, -900, "DPolygon not decoded correctly")
    _check_dpoint_obj(decoded_hole1_points[1], -500, -500, "DPolygon not decoded correctly")
    _check_dpoint_obj(decoded_hole1_points[2], -300, -900, "DPolygon not decoded correctly")
    decoded_hole2_points = sorted(list(decoded_dpolygon.each_point_hole(1)), key=lambda p: p.x)
    assert len(decoded_hole2_points) == 3, "DPolygon not decoded correctly"
    _check_dpoint_obj(decoded_hole2_points[0], 300, 900, "DPolygon not decoded correctly")
    _check_dpoint_obj(decoded_hole2_points[1], 500, 500, "DPolygon not decoded correctly")
    _check_dpoint_obj(decoded_hole2_points[2], 900, 900, "DPolygon not decoded correctly")


def test_decode_composite_dict():
    test_json = """
    {
        "test_layer": {"_pya_type": "LayerInfo", "layer": 1001, "datatype": 2},
        "test_vectors": [
            {"_pya_type": "DVector", "x": 1.2, "y": 3},
            {"_pya_type": "DVector", "x": -3.4, "y": 5},
            null,
            {"_pya_type": "DVector", "x": -1000, "y": 1000}
        ],
        "test_point_sets": {
            "path": {
                "_pya_type": "DPath",
                "points": [{"_pya_type": "DPoint", "x": 0, "y": -1}, {"_pya_type": "DPoint", "x": 1, "y": 0}, {"_pya_type": "DPoint", "x": 0.33, "y": 0.66}],
                "width": 6.5
            },
            "polygon": {
                "_pya_type": "DPolygon",
                "hull": [
                    {"_pya_type": "DPoint", "x": -1001, "y": -1000},
                    {"_pya_type": "DPoint", "x": 999, "y": -1000},
                    {"_pya_type": "DPoint", "x": 1001, "y": 1000},
                    {"_pya_type": "DPoint", "x": -1000, "y": 1000}
                ],
                "holes": [
                    [
                        {"_pya_type": "DPoint", "x": -900, "y": -900},
                        {"_pya_type": "DPoint", "x": -500, "y": -500},
                        {"_pya_type": "DPoint", "x": -300, "y": -900}
                    ],
                    [
                        {"_pya_type": "DPoint", "x": 900, "y": 900},
                        {"_pya_type": "DPoint", "x": 500, "y": 500},
                        {"_pya_type": "DPoint", "x": 300, "y": 900}
                    ]
                ]
            },
            "just_points": [{"_pya_type": "DPoint", "x": -2, "y": 2}, {"_pya_type": "DPoint", "x": 1, "y": -1}, {"_pya_type": "DPoint", "x": 1.33, "y": 2.66}]
        },
        "random_string": "I am a random string",
        "deep_hierarchy": {
            "very_deep_hierarchy": {
                "edge": {
                    "_pya_type": "DEdge",
                    "p1": {"_pya_type": "DPoint", "x": -123.45, "y": 54.321},
                    "p2": {"_pya_type": "DPoint", "x": 13.421, "y": 45.231}
                }
            },
            "box": {
                "_pya_type": "DBox",
                "p1": {"_pya_type": "DPoint", "x": -98.765, "y": -89.763},
                "p2": {"_pya_type": "DPoint", "x": 67.876, "y": 789.87}
            }
        }
    }
    """
    test_json = json.loads(test_json, cls=GeometryJsonDecoder)

    assert isinstance(test_json, dict), "Dict with pya shapes not decoded correctly"
    assert set(test_json.keys()) == set(
        ["test_layer", "test_vectors", "test_point_sets", "random_string", "deep_hierarchy"]
    ), "Dict with pya shapes not decoded correctly"

    assert isinstance(test_json["test_layer"], pya.LayerInfo), "Dict with pya shapes not decoded correctly"
    assert (
        test_json["test_layer"].layer == 1001 and test_json["test_layer"].datatype == 2
    ), "Dict with pya shapes not decoded correctly"

    assert isinstance(test_json["test_vectors"], list), "Dict with pya shapes not decoded correctly"
    assert len(test_json["test_vectors"]) == 4, "Dict with pya shapes not decoded correctly"
    assert isinstance(test_json["test_vectors"][0], pya.DVector), "Dict with pya shapes not decoded correctly"
    assert (
        test_json["test_vectors"][0].x == 1.2 and test_json["test_vectors"][0].y == 3
    ), "Dict with pya shapes not decoded correctly"
    assert isinstance(test_json["test_vectors"][1], pya.DVector), "Dict with pya shapes not decoded correctly"
    assert (
        test_json["test_vectors"][1].x == -3.4 and test_json["test_vectors"][1].y == 5
    ), "Dict with pya shapes not decoded correctly"
    assert test_json["test_vectors"][2] is None, "Dict with pya shapes not decoded correctly"
    assert isinstance(test_json["test_vectors"][3], pya.DVector), "Dict with pya shapes not decoded correctly"
    assert (
        test_json["test_vectors"][3].x == -1000 and test_json["test_vectors"][3].y == 1000
    ), "Dict with pya shapes not decoded correctly"

    assert isinstance(test_json["test_point_sets"], dict), "Dict with pya shapes not decoded correctly"
    assert set(test_json["test_point_sets"].keys()) == set(
        ["path", "polygon", "just_points"]
    ), "Dict with pya shapes not decoded correctly"
    assert isinstance(test_json["test_point_sets"]["path"], pya.DPath), "Dict with pya shapes not decoded correctly"
    points = list(test_json["test_point_sets"]["path"].each_point())
    assert len(points) == 3, "Dict with pya shapes not decoded correctly"
    _check_dpoint_obj(points[0], 0, -1, "Dict with pya shapes not decoded correctly")
    _check_dpoint_obj(points[1], 1, 0, "Dict with pya shapes not decoded correctly")
    _check_dpoint_obj(points[2], 0.33, 0.66, "Dict with pya shapes not decoded correctly")
    assert test_json["test_point_sets"]["path"].width == 6.5, "Dict with pya shapes not decoded correctly"
    assert isinstance(
        test_json["test_point_sets"]["polygon"], pya.DPolygon
    ), "Dict with pya shapes not decoded correctly"
    points = sorted(list(test_json["test_point_sets"]["polygon"].each_point_hull()), key=lambda p: p.x)
    assert len(points) == 4, "Dict with pya shapes not decoded correctly"
    _check_dpoint_obj(points[0], -1001, -1000, "Dict with pya shapes not decoded correctly")
    _check_dpoint_obj(points[1], -1000, 1000, "Dict with pya shapes not decoded correctly")
    _check_dpoint_obj(points[2], 999, -1000, "Dict with pya shapes not decoded correctly")
    _check_dpoint_obj(points[3], 1001, 1000, "Dict with pya shapes not decoded correctly")
    assert test_json["test_point_sets"]["polygon"].holes() == 2, "DPolygon not decoded correctly"
    hole1_points = sorted(list(test_json["test_point_sets"]["polygon"].each_point_hole(0)), key=lambda p: p.x)
    assert len(hole1_points) == 3, "DPolygon not decoded correctly"
    _check_dpoint_obj(hole1_points[0], -900, -900, "DPolygon not decoded correctly")
    _check_dpoint_obj(hole1_points[1], -500, -500, "DPolygon not decoded correctly")
    _check_dpoint_obj(hole1_points[2], -300, -900, "DPolygon not decoded correctly")
    hole2_points = sorted(list(test_json["test_point_sets"]["polygon"].each_point_hole(1)), key=lambda p: p.x)
    assert len(hole2_points) == 3, "DPolygon not decoded correctly"
    _check_dpoint_obj(hole2_points[0], 300, 900, "DPolygon not decoded correctly")
    _check_dpoint_obj(hole2_points[1], 500, 500, "DPolygon not decoded correctly")
    _check_dpoint_obj(hole2_points[2], 900, 900, "DPolygon not decoded correctly")
    assert isinstance(test_json["test_point_sets"]["just_points"], list), "Dict with pya shapes not decoded correctly"
    assert len(test_json["test_point_sets"]["just_points"]) == 3, "Dict with pya shapes not decoded correctly"
    _check_dpoint_obj(
        test_json["test_point_sets"]["just_points"][0], -2, 2, "Dict with pya shapes not decoded correctly"
    )
    _check_dpoint_obj(
        test_json["test_point_sets"]["just_points"][1], 1, -1, "Dict with pya shapes not decoded correctly"
    )
    _check_dpoint_obj(
        test_json["test_point_sets"]["just_points"][2], 1.33, 2.66, "Dict with pya shapes not decoded correctly"
    )

    assert test_json["random_string"] == "I am a random string", "Dict with pya shapes not decoded correctly"

    assert isinstance(test_json["deep_hierarchy"], dict), "Dict with pya shapes not decoded correctly"
    assert set(test_json["deep_hierarchy"].keys()) == set(
        ["very_deep_hierarchy", "box"]
    ), "Dict with pya shapes not decoded correctly"
    assert isinstance(
        test_json["deep_hierarchy"]["very_deep_hierarchy"], dict
    ), "Dict with pya shapes not decoded correctly"
    assert set(test_json["deep_hierarchy"]["very_deep_hierarchy"].keys()) == set(
        ["edge"]
    ), "Dict with pya shapes not decoded correctly"
    assert isinstance(
        test_json["deep_hierarchy"]["very_deep_hierarchy"]["edge"], pya.DEdge
    ), "Dict with pya shapes not decoded correctly"
    assert (
        test_json["deep_hierarchy"]["very_deep_hierarchy"]["edge"].x1 == -123.45
        and test_json["deep_hierarchy"]["very_deep_hierarchy"]["edge"].y1 == 54.321
        and test_json["deep_hierarchy"]["very_deep_hierarchy"]["edge"].x2 == 13.421
        and test_json["deep_hierarchy"]["very_deep_hierarchy"]["edge"].y2 == 45.231
    ), "Dict with pya shapes not decoded correctly"
    assert isinstance(test_json["deep_hierarchy"]["box"], pya.DBox), "Dict with pya shapes not decoded correctly"
    assert (
        test_json["deep_hierarchy"]["box"].left == -98.765
        and test_json["deep_hierarchy"]["box"].bottom == -89.763
        and test_json["deep_hierarchy"]["box"].right == 67.876
        and test_json["deep_hierarchy"]["box"].top == 789.87
    ), "Dict with pya shapes not decoded correctly"

    test_dict = {
        "test_layer": {"_pya_type": "LayerInfo", "layer": 1001, "datatype": 2},
        "test_vectors": [
            {"_pya_type": "DVector", "x": 1.2, "y": 3},
            {"_pya_type": "DVector", "x": -3.4, "y": 5},
            None,
            {"_pya_type": "DVector", "x": -1000, "y": 1000},
        ],
        "test_point_sets": {
            "path": {
                "_pya_type": "DPath",
                "points": [
                    {"_pya_type": "DPoint", "x": 0, "y": -1},
                    {"_pya_type": "DPoint", "x": 1, "y": 0},
                    {"_pya_type": "DPoint", "x": 0.33, "y": 0.66},
                ],
                "width": 6.5,
            },
            "polygon": {
                "_pya_type": "DPolygon",
                "hull": [
                    {"_pya_type": "DPoint", "x": -1001, "y": -1000},
                    {"_pya_type": "DPoint", "x": 999, "y": -1000},
                    {"_pya_type": "DPoint", "x": 1001, "y": 1000},
                    {"_pya_type": "DPoint", "x": -1000, "y": 1000},
                ],
                "holes": [
                    [
                        {"_pya_type": "DPoint", "x": -900, "y": -900},
                        {"_pya_type": "DPoint", "x": -500, "y": -500},
                        {"_pya_type": "DPoint", "x": -300, "y": -900},
                    ],
                    [
                        {"_pya_type": "DPoint", "x": 900, "y": 900},
                        {"_pya_type": "DPoint", "x": 500, "y": 500},
                        {"_pya_type": "DPoint", "x": 300, "y": 900},
                    ],
                ],
            },
            "just_points": [
                {"_pya_type": "DPoint", "x": -2, "y": 2},
                {"_pya_type": "DPoint", "x": 1, "y": -1},
                {"_pya_type": "DPoint", "x": 1.33, "y": 2.66},
            ],
        },
        "random_string": "I am a random string",
        "deep_hierarchy": {
            "very_deep_hierarchy": {
                "edge": {
                    "_pya_type": "DEdge",
                    "p1": {"_pya_type": "DPoint", "x": -123.45, "y": 54.321},
                    "p2": {"_pya_type": "DPoint", "x": 13.421, "y": 45.231},
                }
            },
            "box": {
                "_pya_type": "DBox",
                "p1": {"_pya_type": "DPoint", "x": -98.765, "y": -89.763},
                "p2": {"_pya_type": "DPoint", "x": 67.876, "y": 789.87},
            },
        },
    }
    test_dict = decode_dict_as_python_obj(test_dict)

    assert isinstance(test_dict, dict), "Dict with pya shapes not decoded correctly"
    assert set(test_dict.keys()) == set(
        ["test_layer", "test_vectors", "test_point_sets", "random_string", "deep_hierarchy"]
    ), "Dict with pya shapes not decoded correctly"

    assert isinstance(test_dict["test_layer"], pya.LayerInfo), "Dict with pya shapes not decoded correctly"
    assert (
        test_dict["test_layer"].layer == 1001 and test_dict["test_layer"].datatype == 2
    ), "Dict with pya shapes not decoded correctly"

    assert isinstance(test_dict["test_vectors"], list), "Dict with pya shapes not decoded correctly"
    assert len(test_dict["test_vectors"]) == 4, "Dict with pya shapes not decoded correctly"
    assert isinstance(test_dict["test_vectors"][0], pya.DVector), "Dict with pya shapes not decoded correctly"
    assert (
        test_dict["test_vectors"][0].x == 1.2 and test_dict["test_vectors"][0].y == 3
    ), "Dict with pya shapes not decoded correctly"
    assert isinstance(test_dict["test_vectors"][1], pya.DVector), "Dict with pya shapes not decoded correctly"
    assert (
        test_dict["test_vectors"][1].x == -3.4 and test_dict["test_vectors"][1].y == 5
    ), "Dict with pya shapes not decoded correctly"
    assert test_dict["test_vectors"][2] is None, "Dict with pya shapes not decoded correctly"
    assert isinstance(test_dict["test_vectors"][3], pya.DVector), "Dict with pya shapes not decoded correctly"
    assert (
        test_dict["test_vectors"][3].x == -1000 and test_dict["test_vectors"][3].y == 1000
    ), "Dict with pya shapes not decoded correctly"

    assert isinstance(test_dict["test_point_sets"], dict), "Dict with pya shapes not decoded correctly"
    assert set(test_dict["test_point_sets"].keys()) == set(
        ["path", "polygon", "just_points"]
    ), "Dict with pya shapes not decoded correctly"
    assert isinstance(test_dict["test_point_sets"]["path"], pya.DPath), "Dict with pya shapes not decoded correctly"
    points = list(test_dict["test_point_sets"]["path"].each_point())
    assert len(points) == 3, "Dict with pya shapes not decoded correctly"
    _check_dpoint_obj(points[0], 0, -1, "Dict with pya shapes not decoded correctly")
    _check_dpoint_obj(points[1], 1, 0, "Dict with pya shapes not decoded correctly")
    _check_dpoint_obj(points[2], 0.33, 0.66, "Dict with pya shapes not decoded correctly")
    assert test_dict["test_point_sets"]["path"].width == 6.5, "Dict with pya shapes not decoded correctly"
    assert isinstance(
        test_dict["test_point_sets"]["polygon"], pya.DPolygon
    ), "Dict with pya shapes not decoded correctly"
    points = sorted(list(test_dict["test_point_sets"]["polygon"].each_point_hull()), key=lambda p: p.x)
    assert len(points) == 4, "Dict with pya shapes not decoded correctly"
    _check_dpoint_obj(points[0], -1001, -1000, "Dict with pya shapes not decoded correctly")
    _check_dpoint_obj(points[1], -1000, 1000, "Dict with pya shapes not decoded correctly")
    _check_dpoint_obj(points[2], 999, -1000, "Dict with pya shapes not decoded correctly")
    _check_dpoint_obj(points[3], 1001, 1000, "Dict with pya shapes not decoded correctly")
    assert test_dict["test_point_sets"]["polygon"].holes() == 2, "DPolygon not decoded correctly"
    hole1_points = sorted(list(test_dict["test_point_sets"]["polygon"].each_point_hole(0)), key=lambda p: p.x)
    assert len(hole1_points) == 3, "DPolygon not decoded correctly"
    _check_dpoint_obj(hole1_points[0], -900, -900, "DPolygon not decoded correctly")
    _check_dpoint_obj(hole1_points[1], -500, -500, "DPolygon not decoded correctly")
    _check_dpoint_obj(hole1_points[2], -300, -900, "DPolygon not decoded correctly")
    hole2_points = sorted(list(test_dict["test_point_sets"]["polygon"].each_point_hole(1)), key=lambda p: p.x)
    assert len(hole2_points) == 3, "DPolygon not decoded correctly"
    _check_dpoint_obj(hole2_points[0], 300, 900, "DPolygon not decoded correctly")
    _check_dpoint_obj(hole2_points[1], 500, 500, "DPolygon not decoded correctly")
    _check_dpoint_obj(hole2_points[2], 900, 900, "DPolygon not decoded correctly")
    assert isinstance(test_dict["test_point_sets"]["just_points"], list), "Dict with pya shapes not decoded correctly"
    assert len(test_dict["test_point_sets"]["just_points"]) == 3, "Dict with pya shapes not decoded correctly"
    _check_dpoint_obj(
        test_dict["test_point_sets"]["just_points"][0], -2, 2, "Dict with pya shapes not decoded correctly"
    )
    _check_dpoint_obj(
        test_dict["test_point_sets"]["just_points"][1], 1, -1, "Dict with pya shapes not decoded correctly"
    )
    _check_dpoint_obj(
        test_dict["test_point_sets"]["just_points"][2], 1.33, 2.66, "Dict with pya shapes not decoded correctly"
    )

    assert test_dict["random_string"] == "I am a random string", "Dict with pya shapes not decoded correctly"

    assert isinstance(test_dict["deep_hierarchy"], dict), "Dict with pya shapes not decoded correctly"
    assert set(test_dict["deep_hierarchy"].keys()) == set(
        ["very_deep_hierarchy", "box"]
    ), "Dict with pya shapes not decoded correctly"
    assert isinstance(
        test_dict["deep_hierarchy"]["very_deep_hierarchy"], dict
    ), "Dict with pya shapes not decoded correctly"
    assert set(test_dict["deep_hierarchy"]["very_deep_hierarchy"].keys()) == set(
        ["edge"]
    ), "Dict with pya shapes not decoded correctly"
    assert isinstance(
        test_dict["deep_hierarchy"]["very_deep_hierarchy"]["edge"], pya.DEdge
    ), "Dict with pya shapes not decoded correctly"
    assert (
        test_dict["deep_hierarchy"]["very_deep_hierarchy"]["edge"].x1 == -123.45
        and test_dict["deep_hierarchy"]["very_deep_hierarchy"]["edge"].y1 == 54.321
        and test_dict["deep_hierarchy"]["very_deep_hierarchy"]["edge"].x2 == 13.421
        and test_dict["deep_hierarchy"]["very_deep_hierarchy"]["edge"].y2 == 45.231
    ), "Dict with pya shapes not decoded correctly"
    assert isinstance(test_dict["deep_hierarchy"]["box"], pya.DBox), "Dict with pya shapes not decoded correctly"
    assert (
        test_dict["deep_hierarchy"]["box"].left == -98.765
        and test_dict["deep_hierarchy"]["box"].bottom == -89.763
        and test_dict["deep_hierarchy"]["box"].right == 67.876
        and test_dict["deep_hierarchy"]["box"].top == 789.87
    ), "Dict with pya shapes not decoded correctly"


def test_fail_if_unknown_pya_type():
    exception_caught = False
    try:
        json.loads('{"_pya_type": "DBanana", "x": -1000, "y": 5.67}', cls=GeometryJsonDecoder)
    except Exception:
        exception_caught = True
    assert exception_caught, "Unknown pya type doesn't cause error"

    exception_caught = False
    try:
        decode_dict_as_python_obj({"_pya_type": "DBanana", "x": -1000, "y": 5.67})
    except Exception:
        exception_caught = True
    assert exception_caught, "Unknown pya type doesn't cause error"
