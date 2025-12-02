# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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

import pytest
from kqcircuits.chips.single_xmons import SingleXmons
from kqcircuits.junctions.manhattan import Manhattan
from kqcircuits.junctions.manhattan_single_junction import ManhattanSingleJunction
from kqcircuits.pya_resolver import pya
from kqcircuits.util.load_save_layout import load_layout, save_layout
from kqcircuits.util.replace_junctions import extract_junctions, place_junctions, get_tuned_junction_json, JunctionEntry


@pytest.fixture
def layout():
    return pya.Layout()


@pytest.fixture
def test_chip(layout):
    return SingleXmons.create(layout)


@pytest.fixture
def pcell(layout, test_chip):
    value = layout.create_cell("top_pcell")
    value.insert(pya.DCellInstArray(test_chip.cell_index(), pya.DTrans()))
    return value


@pytest.fixture
def static_cell(layout, test_chip, tmp_path):
    cell = layout.cell(layout.convert_cell_to_static(test_chip.cell_index()))
    static_cell_path = str(tmp_path / "static.oas")
    save_layout(static_cell_path, layout, [cell])
    load_layout(static_cell_path, layout)
    return [c for c in layout.top_cells() if c.name != "top_pcell"][-1]


def check_static_cell_extracts_same_junctions(junctions, static_cell, caplog):
    tuned_params = get_tuned_junction_json(junctions)
    static_junctions = extract_junctions(static_cell, tuned_params)

    def comparator(j):
        return (j.parent_name, j.name)

    assert sorted(junctions, key=comparator) == sorted(
        static_junctions, key=comparator
    ), "Static cell produces different set of junction entries than PCell"
    log_messages = [x.message for x in caplog.records]
    assert (
        len(log_messages) == 1 and log_messages[0] == "Top cell doesn't contain PCell parameter data"
    ), "Expected warning about top cell not containing PCell data"


def test_junction_entry_equality():
    t1 = pya.DCplxTrans(1, 0, False, pya.DVector(1, 2))
    t1_ = pya.DCplxTrans(1, 0, False, pya.DVector(1, 2))
    t2 = pya.DCplxTrans(1, 180, False, pya.DVector(2, 3))
    junction_entry = JunctionEntry(Manhattan, t1, [t1], {"a": 10, "b": 6}, "qb_0", "squid")
    assert junction_entry == JunctionEntry(
        Manhattan, t1_, [t1_], {"b": 6, "a": 10}, "qb_0", "squid"
    ), "Expected these JunctionEntry objects to be considered equal"
    assert junction_entry != JunctionEntry(
        ManhattanSingleJunction, t1, [t1], {"a": 10, "b": 6}, "qb_0", "squid"
    ), "JunctionEntry objects should not be considered equal if they have different type"
    assert junction_entry != JunctionEntry(
        type(None), t1, [t1], {"a": 10, "b": 6}, "qb_0", "squid"
    ), "JunctionEntry objects should not be considered equal if they have different type"
    assert junction_entry != JunctionEntry(
        Manhattan, t2, [t2], {"a": 10, "b": 6}, "qb_0", "squid"
    ), "JunctionEntry objects should not be considered equal if they have different transformation"
    assert junction_entry != JunctionEntry(
        Manhattan, t1, [t1], {"a": 10, "b": 7}, "qb_0", "squid"
    ), "JunctionEntry objects should not be considered equal if they have different parameters"
    assert junction_entry != JunctionEntry(
        Manhattan, t1, [t1], {"a": 10, "b": 6, "c": 0}, "qb_0", "squid"
    ), "JunctionEntry objects should not be considered equal if they have different parameters"
    assert junction_entry != JunctionEntry(
        Manhattan, t1, [t1], {"b": 6}, "qb_0", "squid"
    ), "JunctionEntry objects should not be considered equal if they have different parameters"
    assert junction_entry != JunctionEntry(
        Manhattan, t1, [t1], {"a": 10, "b": 6}, "qb_1", "squid"
    ), "JunctionEntry objects should not be considered equal if they have different parent name"
    assert junction_entry != JunctionEntry(
        Manhattan, t1, [t1], {"a": 10, "b": 6}, "qb_0", "squid_1"
    ), "JunctionEntry objects should not be considered equal if they have different parent name"


def test_junctions_get_extracted_from_pcell(pcell):
    junctions = extract_junctions(pcell, {})
    assert set((j.parent_name, j.name) for j in junctions) == {
        ("testarray_w", "squid_0"),
        ("testarray_w", "squid_1"),
        ("testarray_w", "squid_2"),
        ("testarray_w", "squid_3"),
        ("testarray_e", "squid_0"),
        ("testarray_e", "squid_1"),
        ("testarray_e", "squid_2"),
        ("testarray_e", "squid_3"),
        ("testarray_n", "squid_0"),
        ("testarray_n", "squid_1"),
        ("testarray_n", "squid_2"),
        ("testarray_n", "squid_3"),
        ("testarray_s", "squid_0"),
        ("testarray_s", "squid_1"),
        ("testarray_s", "squid_2"),
        ("testarray_s", "squid_3"),
        ("qb_0", "squid"),
        ("qb_1", "squid"),
        ("qb_2", "squid"),
        ("qb_3", "squid"),
        ("qb_4", "squid"),
        ("qb_5", "squid"),
    }, "Extracted junctions have unexpected parent_name and name values"
    transformations = [j.trans for j in junctions]
    for i, t1 in enumerate(transformations):
        for t2 in transformations[i + 1 :]:
            assert t1 != t2, "No pair of extracted junctions should have the same transformation"
    assert all(j.type == Manhattan for j in junctions), "All extracted junctions should be of type Manhattan"
    vertical_test_array_params = [j.parameters for j in junctions if j.parent_name in ("testarray_w", "testarray_e")]
    horizontal_test_array_params = [j.parameters for j in junctions if j.parent_name in ("testarray_n", "testarray_s")]
    qb_params = [j.parameters for j in junctions if j.parent_name.startswith("qb_")]
    assert all(
        vertical_test_array_params[0] == param for param in vertical_test_array_params
    ), "Vertical test array junctions should have same junction parameters"
    assert all(
        horizontal_test_array_params[0] == param for param in horizontal_test_array_params
    ), "Horizontal test array junctions should have same junction parameters"
    assert all(qb_params[0] == param for param in qb_params), "Qubit junctions should have same junction parameters"


def test_same_junctions_get_extracted_from_static_cell(pcell, static_cell, caplog):
    junctions = extract_junctions(pcell, {})
    check_static_cell_extracts_same_junctions(junctions, static_cell, caplog)


def test_junction_parameters_must_be_exhaustive_for_static_cell1(static_cell):
    with pytest.raises(ValueError) as expected_error:
        extract_junctions(static_cell, {})
    assert "'junction_type' value None for junction" in str(
        expected_error.value
    ) and "is not part of junction_type_choices" in str(expected_error.value), f"Unexpected error {expected_error}"


def test_junction_parameters_must_be_exhaustive_for_static_cell2(pcell, static_cell, caplog):
    junctions = extract_junctions(pcell, {})
    tuned_params = {
        parent_name: {name: {"junction_type": params["junction_type"]} for name, params in obj.items()}
        for parent_name, obj in get_tuned_junction_json(junctions).items()
    }
    with pytest.raises(ValueError) as expected_error:
        extract_junctions(static_cell, tuned_params)
    assert "Some junction parameters were missing in the tuning json, see log for details" in str(
        expected_error.value
    ), f"Unexpected error {expected_error}"
    main_warning = [x.message for x in caplog.records][1]
    assert (
        "Since the cell doesn't contain pre-existing PCell parameter data, "
        "the tuned junction json should be exhaustive.\n"
        "Following junction parameters missing:\n\n"
        "Manhattan class junction parameters missing {"
    ) in main_warning and all(
        x in main_warning for x in ["'face_ids'", "'junction_width'", "'loop_area'"]
    ), f"Unexpected warning: {main_warning}"


def test_junction_parameters_must_be_exhaustive_for_static_cell3(pcell, static_cell, caplog):
    junctions = extract_junctions(pcell, {})
    tuned_params = get_tuned_junction_json(junctions)
    del tuned_params["qb_1"]["squid"]["junction_width"]
    with pytest.raises(ValueError) as expected_error:
        extract_junctions(static_cell, tuned_params)
    assert "Some junction parameters were missing in the tuning json, see log for details" in str(
        expected_error.value
    ), f"Unexpected error {expected_error}"
    main_warning = [x.message for x in caplog.records][1]
    assert (
        "Since the cell doesn't contain pre-existing PCell parameter data, "
        "the tuned junction json should be exhaustive.\n"
        "Following junction parameters missing:\n\n"
        "Manhattan class junction parameters missing {'junction_width'}\n"
        "missing for [('qb_1', 'squid')]\n\n"
    ) in main_warning, f"Unexpected warning: {main_warning}"


def test_junction_cant_be_none_for_static_cell(pcell, static_cell):
    junctions = extract_junctions(pcell, {})
    tuned_params = get_tuned_junction_json(junctions)
    del tuned_params["qb_1"]["squid"]["junction_type"]
    with pytest.raises(ValueError) as expected_error:
        extract_junctions(static_cell, tuned_params)
    assert "'junction_type' value None for junction (qb_1, squid) is not part of junction_type_choices" in str(
        expected_error.value
    ), f"Unexpected error {expected_error}"


def test_tune_parameter1(pcell, static_cell, caplog):
    junctions = extract_junctions(pcell, {"qb_1": {"squid": {"junction_width": 2.0}}})
    assert [j.parameters for j in junctions if j.parent_name == "qb_1" and j.name == "squid"][0][
        "junction_width"
    ] == 2.0, "Expected junction_width for qb_1 to be tuned to 2.0"
    junction_width_values = set(j.parameters["junction_width"] for j in junctions)
    other_junction_value = list(junction_width_values.difference({2.0}))[0]
    assert all(
        j.parameters["junction_width"] == other_junction_value
        for j in junctions
        if not (j.parent_name == "qb_1" and j.name == "squid")
    ), "All other junction_width values should be the same"
    check_static_cell_extracts_same_junctions(junctions, static_cell, caplog)


def test_tune_parameter2(pcell, static_cell, caplog):
    junctions = extract_junctions(
        pcell,
        {
            "qb_1": {
                "squid": {
                    "junction_width": 2.0,
                    "loop_area": 50,
                }
            }
        },
    )
    assert [j.parameters for j in junctions if j.parent_name == "qb_1" and j.name == "squid"][0][
        "junction_width"
    ] == 2.0, "Expected junction_width for qb_1 to be tuned to 2.0"
    assert [j.parameters for j in junctions if j.parent_name == "qb_1" and j.name == "squid"][0][
        "loop_area"
    ] == 50, "Expected loop_area for qb_1 to be tuned to 50"
    junction_width_values = set(j.parameters["junction_width"] for j in junctions)
    other_junction_value = list(junction_width_values.difference({2.0}))[0]
    loop_area_values = set(j.parameters["loop_area"] for j in junctions)
    other_loop_value = list(loop_area_values.difference({50}))[0]
    assert all(
        j.parameters["junction_width"] == other_junction_value and j.parameters["loop_area"] == other_loop_value
        for j in junctions
        if not (j.parent_name == "qb_1" and j.name == "squid")
    ), "All other junction_width values should be the same"
    check_static_cell_extracts_same_junctions(junctions, static_cell, caplog)


def test_tune_parameter3(pcell, static_cell, caplog):
    junctions = extract_junctions(
        pcell,
        {
            "qb_1": {
                "squid": {
                    "junction_width": 2.0,
                    "loop_area": 50,
                }
            },
            "testarray_s": {"squid_1": {"loop_area": 25}},
        },
    )
    assert [j.parameters for j in junctions if j.parent_name == "qb_1" and j.name == "squid"][0][
        "junction_width"
    ] == 2.0, "Expected junction_width for qb_1 to be tuned to 2.0"
    assert [j.parameters for j in junctions if j.parent_name == "qb_1" and j.name == "squid"][0][
        "loop_area"
    ] == 50, "Expected loop_area for qb_1 to be tuned to 50"
    assert [j.parameters for j in junctions if j.parent_name == "testarray_s" and j.name == "squid_1"][0][
        "loop_area"
    ] == 25, "Expected loop_area for qb_1 to be tuned to 25"
    junction_width_values = set(j.parameters["junction_width"] for j in junctions)
    other_junction_value = list(junction_width_values.difference({2.0}))[0]
    loop_area_values = set(j.parameters["loop_area"] for j in junctions)
    other_loop_value = list(loop_area_values.difference({50, 25}))[0]
    assert all(
        j.parameters["junction_width"] == other_junction_value
        for j in junctions
        if not (j.parent_name == "qb_1" and j.name == "squid")
    ), "All other junction_width values should be the same"
    assert all(
        j.parameters["loop_area"] == other_loop_value
        for j in junctions
        if not (
            (j.parent_name == "qb_1" and j.name == "squid") or (j.parent_name == "testarray_s" and j.name == "squid_1")
        )
    ), "All other junction_width values should be the same"
    check_static_cell_extracts_same_junctions(junctions, static_cell, caplog)


def test_change_junction_type(pcell, static_cell, caplog):
    junctions = extract_junctions(
        pcell,
        {
            "qb_1": {
                "squid": {
                    "junction_type": "Manhattan Single Junction",
                    # Parameters that ManhattanSingleJunction uses but Manhattan does not use
                    "width": 22,
                    "pad_to_pad_separation": 6,
                    "pad_height": 6,
                    "pad_width": 12,
                    "include_base_metal_addition": True,
                    "x_offset": 0,
                    "height": 22,
                    "pad_rounding_radius": 0.5,
                }
            }
        },
    )
    assert set((j.parent_name, j.name) for j in junctions) == {
        ("testarray_w", "squid_0"),
        ("testarray_w", "squid_1"),
        ("testarray_w", "squid_2"),
        ("testarray_w", "squid_3"),
        ("testarray_e", "squid_0"),
        ("testarray_e", "squid_1"),
        ("testarray_e", "squid_2"),
        ("testarray_e", "squid_3"),
        ("testarray_n", "squid_0"),
        ("testarray_n", "squid_1"),
        ("testarray_n", "squid_2"),
        ("testarray_n", "squid_3"),
        ("testarray_s", "squid_0"),
        ("testarray_s", "squid_1"),
        ("testarray_s", "squid_2"),
        ("testarray_s", "squid_3"),
        ("qb_0", "squid"),
        ("qb_1", "squid"),
        ("qb_2", "squid"),
        ("qb_3", "squid"),
        ("qb_4", "squid"),
        ("qb_5", "squid"),
    }, "Extracted junctions have unexpected parent_name and name values"
    transformations = [j.trans for j in junctions]
    for i, t1 in enumerate(transformations):
        for t2 in transformations[i + 1 :]:
            assert t1 != t2, "No pair of extracted junctions should have the same transformation"
    assert [j for j in junctions if j.parent_name == "qb_1"][
        0
    ].type == ManhattanSingleJunction, "Junction of qb_1 should be of type ManhattanSingleJunction"
    assert all(
        j.type == Manhattan for j in junctions if j.parent_name != "qb_1"
    ), "All extracted junctions except qb_1 should be of type Manhattan"
    vertical_test_array_params = [j.parameters for j in junctions if j.parent_name in ("testarray_w", "testarray_e")]
    horizontal_test_array_params = [j.parameters for j in junctions if j.parent_name in ("testarray_n", "testarray_s")]
    qb_params = [j.parameters for j in junctions if j.parent_name.startswith("qb_") and j.parent_name != "qb_1"]
    assert all(
        vertical_test_array_params[0] == param for param in vertical_test_array_params
    ), "Vertical test array junctions should have same junction parameters"
    assert all(
        horizontal_test_array_params[0] == param for param in horizontal_test_array_params
    ), "Horizontal test array junctions should have same junction parameters"
    assert all(qb_params[0] == param for param in qb_params), "Qubit junctions should have same junction parameters"
    check_static_cell_extracts_same_junctions(junctions, static_cell, caplog)


def test_changing_junction_type_requires_missing_parameters_for_pcell1(pcell, caplog):
    with pytest.raises(ValueError) as expected_error:
        junctions = extract_junctions(
            pcell,
            {
                "qb_1": {
                    "squid": {
                        "junction_type": "Manhattan Single Junction",
                    }
                }
            },
        )
    assert "Some junction parameters were missing in the tuning json, see log for details" in str(
        expected_error.value
    ), f"Unexpected error {expected_error}"
    main_warning = [x.message for x in caplog.records][0]
    assert (
        (
            "Since junction type was changed for some junctions, "
            "the tuned junction json should give value at least for parameters that are in new junction type "
            "but not in old junction type.\nFollowing junction parameters missing:\n\n"
            "ManhattanSingleJunction class junction parameters missing {"
        )
        in main_warning
        and all(
            x in main_warning
            for x in [
                "'pad_rounding_radius'",
                "'include_base_metal_addition'",
                "'height'",
                "'width'",
                "'pad_to_pad_separation'",
                "'x_offset'",
                "'pad_width'",
                "'pad_height'",
            ]
        )
        and "missing for [('qb_1', 'squid')]\n\n" in main_warning
    )


def test_changing_junction_type_requires_missing_parameters_for_pcell2(pcell, caplog):
    with pytest.raises(ValueError) as expected_error:
        junctions = extract_junctions(
            pcell,
            {
                "qb_1": {
                    "squid": {
                        "junction_type": "Manhattan Single Junction",
                        # Parameters that ManhattanSingleJunction uses but Manhattan does not use
                        "width": 22,
                        # "pad_to_pad_separation": 6,
                        "pad_height": 6,
                        "pad_width": 12,
                        "include_base_metal_addition": True,
                        "x_offset": 0,
                        "height": 22,
                        "pad_rounding_radius": 0.5,
                    }
                }
            },
        )
    assert "Some junction parameters were missing in the tuning json, see log for details" in str(
        expected_error.value
    ), f"Unexpected error {expected_error}"
    main_warning = [x.message for x in caplog.records][0]
    assert (
        "Since junction type was changed for some junctions, "
        "the tuned junction json should give value at least for parameters that are in new junction type "
        "but not in old junction type.\nFollowing junction parameters missing:\n\n"
        "ManhattanSingleJunction class junction parameters missing {'pad_to_pad_separation'}\n"
        "missing for [('qb_1', 'squid')]\n\n"
    ) in main_warning


def test_changing_junction_type_for_pcell_can_reuse_parameter_values(pcell):
    junctions = extract_junctions(
        pcell,
        {
            "qb_1": {
                "squid": {
                    "junction_type": "Manhattan Single Junction",
                    "offset_compensation": 1.0,  # Parameter shared by Manhattan and ManhattanSingleJunction
                    # Parameters that ManhattanSingleJunction uses but Manhattan does not use
                    "width": 22,
                    "pad_to_pad_separation": 6,
                    "pad_height": 6,
                    "pad_width": 12,
                    "include_base_metal_addition": True,
                    "x_offset": 0,
                    "height": 22,
                    "pad_rounding_radius": 0.5,
                }
            }
        },
    )
    got_offset_compensation = [j for j in junctions if j.parent_name == "qb_1"][0].parameters["offset_compensation"]
    assert (
        got_offset_compensation == 1.0
    ), f"Expected offset_compensation for qb_1 to be tuned to 1.0, got {got_offset_compensation}"
    assert all(
        j.parameters["offset_compensation"] == 0.0 for j in junctions if j.parent_name != "qb_1"
    ), "Expected offset_compensation to be set to default 0.0 for all junctions except qb_1"
    junctions2 = extract_junctions(
        pcell,
        {
            "qb_1": {
                "squid": {
                    "junction_type": "Manhattan Single Junction",
                    # Parameters that ManhattanSingleJunction uses but Manhattan does not use
                    "width": 22,
                    "pad_to_pad_separation": 6,
                    "pad_height": 6,
                    "pad_width": 12,
                    "include_base_metal_addition": True,
                    "x_offset": 0,
                    "height": 22,
                    "pad_rounding_radius": 0.5,
                }
            }
        },
    )
    assert all(
        j.parameters["offset_compensation"] == 0.0 for j in junctions2
    ), "Expected offset_compensation to be set to default 0.0 for all junctions"


def test_changing_junction_type_expects_different_schema_for_static_cell(pcell, static_cell, caplog):
    # First extract junctions to get schemas at runtime of both junction types
    params_with_orig_junction = extract_junctions(pcell, {})
    params_with_orig_junction = get_tuned_junction_json(params_with_orig_junction)
    params_with_orig_junction["qb_1"]["squid"]["junction_type"] = "Manhattan Single Junction"
    params_with_changed_junction = extract_junctions(
        pcell,
        {
            "qb_1": {
                "squid": {
                    "junction_type": "Manhattan Single Junction",
                    # Parameters that ManhattanSingleJunction uses but Manhattan does not use
                    "width": 22,
                    "pad_to_pad_separation": 6,
                    "pad_height": 6,
                    "pad_width": 12,
                    "include_base_metal_addition": True,
                    "x_offset": 0,
                    "height": 22,
                    "pad_rounding_radius": 0.5,
                }
            }
        },
    )
    params_with_changed_junction = get_tuned_junction_json(params_with_changed_junction)
    with pytest.raises(ValueError) as expected_error:
        junctions = extract_junctions(static_cell, params_with_orig_junction)
    assert "Some junction parameters were missing in the tuning json, see log for details" in str(
        expected_error.value
    ), f"Unexpected error {expected_error}"
    main_warning = [x.message for x in caplog.records][-1]
    assert (
        "Since the cell doesn't contain pre-existing PCell parameter data, "
        "the tuned junction json should be exhaustive.\nFollowing junction parameters missing:\n\n"
        "ManhattanSingleJunction class junction parameters missing {"
    ) in main_warning and "missing for [('qb_1', 'squid')]\n\n" in main_warning
    junctions = extract_junctions(static_cell, params_with_changed_junction)
    assert [j for j in junctions if j.parent_name == "qb_1"][
        0
    ].type == ManhattanSingleJunction, "Junction of qb_1 should be of type ManhattanSingleJunction"
    assert all(
        j.type == Manhattan for j in junctions if j.parent_name != "qb_1"
    ), "All extracted junctions except qb_1 should be of type Manhattan"


def test_warn_about_surplus_parameters_pcell1(pcell, caplog):
    junctions = extract_junctions(pcell, {"qb_1": {"squid": {"foobar": 123}}})
    warnings = [x.message for x in caplog.records]
    assert (
        "Manhattan class junction attempted to be tuned with parameters " "that are not part of the class: {'foobar'}"
    ) in warnings[0], f"Unexpected warning: {warnings[0]}"
    assert "for [('qb_1', 'squid')]" in warnings[1], f"Unexpected warning: {warnings[1]}"
    assert len(junctions) == 22, "Junctions should get extracted even if it caused warnings"


def test_warn_about_surplus_parameters_pcell2(pcell, caplog):
    junctions = extract_junctions(
        pcell,
        {
            "qb_1": {
                "squid": {
                    "width": 22,
                    "pad_to_pad_separation": 6,
                    "pad_height": 6,
                    "pad_width": 12,
                    "include_base_metal_addition": True,
                    "x_offset": 0,
                    "height": 22,
                    "pad_rounding_radius": 0.5,
                }
            }
        },
    )
    warnings = [x.message for x in caplog.records]
    assert (
        "Manhattan class junction attempted to be tuned with parameters " "that are not part of the class: {"
    ) in warnings[0] and all(
        x in warnings[0]
        for x in [
            "'width'",
            "'pad_to_pad_separation'",
            "'pad_height'",
            "'pad_width'",
            "'include_base_metal_addition'",
            "'x_offset'",
            "'height'",
            "'pad_rounding_radius'",
        ]
    ), f"Unexpected warning: {warnings[0]}"
    assert "for [('qb_1', 'squid')]" in warnings[1], f"Unexpected warning: {warnings[1]}"
    assert len(junctions) == 22, "Junctions should get extracted even if it caused warnings"


def test_warn_about_surplus_parameters_static1(pcell, static_cell, caplog):
    tuned_params = extract_junctions(pcell, {})
    tuned_params = get_tuned_junction_json(tuned_params)
    tuned_params["qb_1"]["squid"]["foobar"] = 123
    junctions = extract_junctions(static_cell, tuned_params)
    warnings = [x.message for x in caplog.records]
    assert "Top cell doesn't contain PCell parameter data" in warnings[0], f"Unexpected warning: {warnings[0]}"
    assert (
        "Manhattan class junction attempted to be tuned with parameters " "that are not part of the class: {'foobar'}"
    ) in warnings[1], f"Unexpected warning: {warnings[1]}"
    assert "for [('qb_1', 'squid')]" in warnings[2], f"Unexpected warning: {warnings[2]}"
    assert len(junctions) == 22, "Junctions should get extracted even if it caused warnings"


def test_warn_about_surplus_parameters_static2(pcell, static_cell, caplog):
    tuned_params = extract_junctions(
        pcell,
        {
            "qb_1": {
                "squid": {
                    "junction_type": "Manhattan Single Junction",
                    "width": 22,
                    "pad_to_pad_separation": 6,
                    "pad_height": 6,
                    "pad_width": 12,
                    "include_base_metal_addition": True,
                    "x_offset": 0,
                    "height": 22,
                    "pad_rounding_radius": 0.5,
                }
            }
        },
    )
    tuned_params = get_tuned_junction_json(tuned_params)
    tuned_params["qb_1"]["squid"].update(tuned_params["qb_0"]["squid"])
    junctions = extract_junctions(static_cell, tuned_params)
    warnings = [x.message for x in caplog.records]
    assert "Top cell doesn't contain PCell parameter data" in warnings[0], f"Unexpected warning: {warnings[0]}"
    assert (
        "Manhattan class junction attempted to be tuned with parameters " "that are not part of the class: {"
    ) in warnings[1] and all(
        x in warnings[1]
        for x in [
            "'width'",
            "'pad_to_pad_separation'",
            "'pad_height'",
            "'pad_width'",
            "'include_base_metal_addition'",
            "'x_offset'",
            "'height'",
            "'pad_rounding_radius'",
        ]
    ), f"Unexpected warning: {warnings[1]}"
    assert "for [('qb_1', 'squid')]" in warnings[2], f"Unexpected warning: {warnings[2]}"
    assert len(junctions) == 22, "Junctions should get extracted even if it caused warnings"


def test_cant_change_to_junction_type_that_doesnt_exist(pcell):
    with pytest.raises(ValueError) as expected_error:
        junctions = extract_junctions(
            pcell,
            {
                "qb_1": {
                    "squid": {
                        "junction_type": "Foobar Junction",
                    }
                }
            },
        )
    assert (
        "'junction_type' value Foobar Junction for junction (qb_1, squid) is not part of junction_type_choices"
        in str(expected_error.value)
    ), (f"Unexpected error {expected_error}")


def test_recreating_chip_with_no_tuning_has_identical_geometry(pcell):
    must_be_exact = ["1t1_SIS_junction", "1t1_SIS_shadow", "1t1_SIS_junction_2"]
    must_be_within = ["1t1_base_metal_gap_wo_grid", "1t1_base_metal_addition"]
    junctions = extract_junctions(pcell, {})
    layout = pya.Layout()
    junction_cell = layout.create_cell("junctions")
    place_junctions(junction_cell, junctions)
    junction_regions = {}
    for layer_info in layout.layer_infos():
        if layer_info.name in must_be_exact + must_be_within:
            region = pya.Region(junction_cell.begin_shapes_rec(layout.layer(layer_info)))
            if not region.is_empty():
                junction_regions[layer_info] = region
    for layer_info, junction_region in junction_regions.items():
        region = pya.Region(pcell.begin_shapes_rec(pcell.layout().layer(layer_info)))
        if layer_info.name in must_be_exact:
            assert (
                region ^ junction_region
            ).is_empty(), f"In layer {layer_info.name} junction geometry should be a identical to original geometry"
        elif layer_info.name in must_be_within:
            assert (
                junction_region - region
            ).is_empty(), f"In layer {layer_info.name} junction geometry should be a subset of original geometry"


def test_recreating_chip_with_some_tuning_has_limited_diff_in_geometry1(pcell):
    must_be_exact = ["1t1_SIS_junction", "1t1_SIS_shadow", "1t1_SIS_junction_2"]
    must_be_within = ["1t1_base_metal_gap_wo_grid", "1t1_base_metal_addition"]
    junctions = extract_junctions(pcell, {"qb_1": {"squid": {"junction_width": 2.0}}})
    layout = pya.Layout()
    junction_cell = layout.create_cell("junctions")
    place_junctions(junction_cell, junctions)
    junction_regions = {}
    for layer_info in layout.layer_infos():
        if layer_info.name in must_be_exact + must_be_within:
            region = pya.Region(junction_cell.begin_shapes_rec(layout.layer(layer_info)))
            if not region.is_empty():
                junction_regions[layer_info] = region
    test_box = pya.Region(pya.DBox(5900, 6400, 6000, 6500).to_itype(layout.dbu))
    has_diff_somewhere = False
    for layer_info, junction_region in junction_regions.items():
        region = pya.Region(pcell.begin_shapes_rec(pcell.layout().layer(layer_info)))
        if layer_info.name in must_be_exact:
            diff_region = region ^ junction_region
            if not diff_region.is_empty():
                has_diff_somewhere = True
            assert (
                diff_region - test_box
            ).is_empty(), f"All geometry diffs at layer {layer_info.name} should be contained within a bounding box"
        elif layer_info.name in must_be_within:
            diff_region = junction_region - region
            assert (
                diff_region - test_box
            ).is_empty(), f"All geometry diffs at layer {layer_info.name} should be contained within a bounding box"
    assert has_diff_somewhere, (
        "There was no difference in geometry between original and junction cell, "
        "but should have thicker junction hands"
    )


def test_recreating_chip_with_some_tuning_has_limited_diff_in_geometry2(pcell):
    must_be_exact = ["1t1_SIS_junction", "1t1_SIS_shadow", "1t1_SIS_junction_2"]
    must_be_within = ["1t1_base_metal_gap_wo_grid", "1t1_base_metal_addition"]
    junctions = extract_junctions(
        pcell,
        {
            "qb_1": {
                "squid": {
                    "junction_type": "Manhattan Single Junction",
                    # Parameters that ManhattanSingleJunction uses but Manhattan does not use
                    "width": 22,
                    "pad_to_pad_separation": 6,
                    "pad_height": 6,
                    "pad_width": 12,
                    "include_base_metal_addition": True,
                    "x_offset": 0,
                    "height": 22,
                    "pad_rounding_radius": 0.5,
                }
            }
        },
    )
    layout = pya.Layout()
    junction_cell = layout.create_cell("junctions")
    place_junctions(junction_cell, junctions)
    junction_regions = {}
    for layer_info in layout.layer_infos():
        if layer_info.name in must_be_exact + must_be_within:
            region = pya.Region(junction_cell.begin_shapes_rec(layout.layer(layer_info)))
            if not region.is_empty():
                junction_regions[layer_info] = region
    test_box = pya.Region(pya.DBox(5900, 6400, 6000, 6500).to_itype(layout.dbu))
    has_diff_somewhere = False
    for layer_info, junction_region in junction_regions.items():
        region = pya.Region(pcell.begin_shapes_rec(pcell.layout().layer(layer_info)))
        if layer_info.name in must_be_exact:
            diff_region = region ^ junction_region
            if not diff_region.is_empty():
                has_diff_somewhere = True
            assert (
                diff_region - test_box
            ).is_empty(), f"All geometry diffs at layer {layer_info.name} should be contained within a bounding box"
        elif layer_info.name in must_be_within:
            diff_region = junction_region - region
            assert (
                diff_region - test_box
            ).is_empty(), f"All geometry diffs at layer {layer_info.name} should be contained within a bounding box"
    assert has_diff_somewhere, (
        "There was no difference in geometry between original and junction cell, "
        "but should have thicker junction hands"
    )
