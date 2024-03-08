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

import pytest
from kqcircuits.defaults import default_layers
from kqcircuits.chips.chip import Chip
from kqcircuits.elements.element import insert_cell_into
from kqcircuits.pya_resolver import pya
from kqcircuits.util.export_helper import generate_probepoints_json


def add_refpoint(cell, name, x, y):
    refpoint_layer = cell.layout().layer(default_layers["refpoints"])
    cell.shapes(refpoint_layer).insert(pya.DText(name, x, y))


def site_is_at(group, site_id, west_x, west_y, east_x, east_y):
    site = [s for s in group["sites"] if s["id"] == site_id][0]
    assert site, f"Site with id {site_id} was not exported: {group}"
    expected_value = {"east": {"x": east_x, "y": east_y}, "id": site_id, "west": {"x": west_x, "y": west_y}}
    assert site == expected_value, f"Expected {expected_value}, got {site}"


@pytest.fixture
def layout():
    return pya.Layout()


@pytest.fixture
def empty_cell(layout):
    """Adds two substrate flipchip

    with dimensions (0, 0, 10000, 1000) and (1500, 1500, 8500, 8500)
    with bottom chip markers at (1500, 1500, 8500, 8500)
    and top markers at (7500, 7500, 7500, 7500) relative to bottom chip origin,
    or (1000, 1000, 6000, 6000) relative to top chip origin and oritentation
    """
    cell = layout.create_cell("test")
    insert_cell_into(cell, Chip, frames_enabled=[0, 1])
    return cell


@pytest.fixture
def dummy_cell(empty_cell):
    """Add some refpoints so that probepoint generator returns something."""
    add_refpoint(empty_cell, "testarray_1_probe_0_l", 4400, 8600)
    add_refpoint(empty_cell, "testarray_1_probe_0_r", 4000, 8600)
    return empty_cell


@pytest.fixture
def legacy_cell(dummy_cell):
    """Recreates empty_cell such that layer and refpoint names uses legacy face naming scheme."""
    bottom_bbox = dummy_cell.dbbox_per_layer(
        dummy_cell.layout().layer(
            [l for l in dummy_cell.layout().layer_infos() if l.name == "1t1_base_metal_gap_wo_grid"][0]
        )
    )
    top_bbox = dummy_cell.dbbox_per_layer(
        dummy_cell.layout().layer(
            [l for l in dummy_cell.layout().layer_infos() if l.name == "2b1_base_metal_gap_wo_grid"][0]
        )
    )
    dummy_cell.shapes(dummy_cell.layout().layer(pya.LayerInfo(1000, 0, "b_base_metal_gap_wo_grid"))).insert(bottom_bbox)
    dummy_cell.shapes(dummy_cell.layout().layer(pya.LayerInfo(1001, 0, "t_base_metal_gap_wo_grid"))).insert(top_bbox)
    add_refpoint(dummy_cell, "b_marker_nw", 1500, 8500)
    add_refpoint(dummy_cell, "t_marker_nw", 7500, 7500)
    return dummy_cell


def test_finds_bottom_face_marker(dummy_cell, caplog):
    probepoints = generate_probepoints_json(dummy_cell)
    assert not caplog.records, f"Didn't expect warnings but got following: {[x.message for x in caplog.records]}"
    assert probepoints["alignment"] == {"x": 1.5, "y": 8.5}, "Expected 1t1 face NW marker at 1.5,8.5"


def test_finds_top_face_marker(dummy_cell, caplog):
    probepoints = generate_probepoints_json(dummy_cell, face="2b1")
    assert not caplog.records, f"Didn't expect warnings but got following: {[x.message for x in caplog.records]}"
    assert probepoints["alignment"] == {"x": 1.0, "y": 6.0}, "Expected 2b1 face NW marker at 1.0,6.0"


def test_finds_bottom_face_legacy_marker(legacy_cell, caplog):
    probepoints = generate_probepoints_json(legacy_cell, face="b")
    assert not caplog.records, f"Didn't expect warnings but got following: {[x.message for x in caplog.records]}"
    assert probepoints["alignment"] == {"x": 1.5, "y": 8.5}, "Expected b face NW marker at 1.5,8.5"
    site_is_at(probepoints, "testarray_1_probe_0", 4.0, 8.6, 4.4, 8.6)


def test_finds_top_face_legacy_marker(legacy_cell, caplog):
    probepoints = generate_probepoints_json(legacy_cell, face="t")
    assert not caplog.records, f"Didn't expect warnings but got following: {[x.message for x in caplog.records]}"
    assert probepoints["alignment"] == {"x": 1.0, "y": 6.0}, "Expected t face NW marker at 1.0,6.0"
    top_chip_width, top_chip_offset_x, top_chip_offset_y = 7.0, 1.5, 1.5
    site_is_at(
        probepoints,
        "testarray_1_probe_0",
        round(top_chip_width - (4.4 - top_chip_offset_x), 4),
        round(8.6 - top_chip_offset_y, 4),
        round(top_chip_width - (4.0 - top_chip_offset_x), 4),
        round(8.6 - top_chip_offset_y, 4),
    )


def test_warn_if_geometry_missing1(dummy_cell, caplog):
    add_refpoint(dummy_cell, "1x1_marker_nw", 1500, 1500)
    generate_probepoints_json(dummy_cell, face="1x1")
    log_messages = [x.message for x in caplog.records]
    assert len(log_messages) == 2, "Expected to have a warning in the log for not finding geometry"
    assert (
        "No geometry found at layer 1x1_base_metal_gap_wo_grid!" in log_messages[0]
    ), f"Unexpected warning message: {log_messages[0]}"
    assert (
        "Assuming chip dimensions are at (0,0;10000,10000)" in log_messages[1]
    ), f"Unexpected warning message: {log_messages[1]}"


def test_warn_if_geometry_missing2(layout, caplog):
    cell = layout.create_cell("test")
    insert_cell_into(cell, Chip)
    add_refpoint(cell, "2b1_marker_nw", 7500, 7500)
    generate_probepoints_json(cell, face="2b1")
    log_messages = [x.message for x in caplog.records]
    assert len(log_messages) == 2, "Expected to have a warning in the log for not finding geometry"
    assert (
        "No geometry found at layer 2b1_base_metal_gap_wo_grid!" in log_messages[0]
    ), f"Unexpected warning message: {log_messages[0]}"
    assert (
        "Assuming chip dimensions are at (1500,1500;8500,8500)" in log_messages[1]
    ), f"Unexpected warning message: {log_messages[1]}"


def test_warn_if_missing_marker_refpoint_and_give_default1(layout, caplog):
    cell = layout.create_cell("test")
    cell.shapes(cell.layout().layer(pya.LayerInfo(1000, 0, "1t1_base_metal_gap_wo_grid"))).insert(
        pya.DBox(0, 0, 10000, 10000)
    )
    add_refpoint(cell, "testarray_1_probe_0_l", 4400, 8600)
    add_refpoint(cell, "testarray_1_probe_0_r", 4000, 8600)
    probepoints = generate_probepoints_json(cell)
    log_messages = [x.message for x in caplog.records]
    assert len(log_messages) == 2, "Expected to have a warning in the log for not finding a marker refpoint"
    assert (
        "The marker or at least its refpoint 1t1_marker_nw is missing in the cell test!" in log_messages[0]
    ), f"Unexpected warning message: {log_messages[0]}"
    assert (
        "Setting marker 1t1_marker_nw to DPoint(1500, 8500)" in log_messages[1]
    ), f"Unexpected warning message: {log_messages[1]}"
    site_is_at(probepoints, "testarray_1_probe_0", 4.0, 8.6, 4.4, 8.6)


def test_warn_if_missing_marker_refpoint_and_give_default2(dummy_cell, caplog):
    dummy_cell.shapes(dummy_cell.layout().layer(pya.LayerInfo(1000, 0, "1x1_base_metal_gap_wo_grid"))).insert(
        pya.DBox(0, 0, 10000, 10000)
    )
    probepoints = generate_probepoints_json(dummy_cell, face="1x1")
    log_messages = [x.message for x in caplog.records]
    assert len(log_messages) == 2, "Expected to have a warning in the log for not finding a marker refpoint"
    assert (
        "The marker or at least its refpoint 1x1_marker_nw is missing in the cell test!" in log_messages[0]
    ), f"Unexpected warning message: {log_messages[0]}"
    assert (
        "Setting marker 1x1_marker_nw to DPoint(1500, 8500)" in log_messages[1]
    ), f"Unexpected warning message: {log_messages[1]}"
    site_is_at(probepoints, "testarray_1_probe_0", 4.0, 8.6, 4.4, 8.6)


def test_warn_if_missing_marker_refpoint_and_give_default3(dummy_cell, caplog):
    probepoints = generate_probepoints_json(dummy_cell, references=["xw"])
    log_messages = [x.message for x in caplog.records]
    assert len(log_messages) > 0, "Expected to have a warning in the log for not finding a marker refpoint"
    assert (
        "The marker or at least its refpoint 1t1_marker_xw is missing in the cell test!" in log_messages[0]
    ), f"Unexpected warning message: {log_messages[0]}"
    assert (
        "Setting marker 1t1_marker_xw to DPoint(1500, 8500)" in log_messages[1]
    ), f"Unexpected warning message: {log_messages[1]}"
    site_is_at(probepoints, "testarray_1_probe_0", 4.0, 8.6, 4.4, 8.6)


def test_warn_if_missing_marker_refpoint_multireference(dummy_cell, caplog):
    add_refpoint(dummy_cell, "testarray_2_probe_0_l", 4400, 2600)
    add_refpoint(dummy_cell, "testarray_2_probe_0_r", 4000, 2600)
    probepoints = generate_probepoints_json(dummy_cell, references=["nw", "xw", "se"])
    log_messages = [x.message for x in caplog.records]
    assert len(log_messages) == 1, "Expected to have exactly one warning in the log for not finding a marker refpoint"
    assert (
        "The marker or at least its refpoint 1t1_marker_xw is missing in the cell test!" in log_messages[0]
    ), f"Unexpected warning message: {log_messages[0]}"
    nw_sites = [g for g in probepoints["groups"] if g["id"] == "NW"][0]
    se_sites = [g for g in probepoints["groups"] if g["id"] == "SE"][0]
    site_is_at(nw_sites, "testarray_1_probe_0", 4.0, 8.6, 4.4, 8.6)
    site_is_at(se_sites, "testarray_2_probe_0", 4.0, 2.6, 4.4, 2.6)


def test_fail_if_cell_is_null():
    with pytest.raises(ValueError) as expected_error:
        generate_probepoints_json(None)
    assert "Cell is null" in str(expected_error.value)


def test_fail_if_references_is_empty(dummy_cell):
    with pytest.raises(ValueError) as expected_error:
        generate_probepoints_json(dummy_cell, references=[])
    assert "Can't use empty list of references" in str(expected_error.value)


def test_fail_if_malformed_contact_arg(dummy_cell):
    with pytest.raises(ValueError) as expected_error:
        generate_probepoints_json(dummy_cell, contact=(pya.DPoint(5000, 5000),))
    assert "Singular contact must be tuple of two DPoints" in str(expected_error.value)


def test_fail_if_contact_list_does_not_match_references1():
    with pytest.raises(ValueError) as expected_error:
        generate_probepoints_json(
            dummy_cell,
            references=["nw", "sw", "se", "ne"],
            contact=[
                (pya.DPoint(5000, 5000), pya.DPoint(5000, 5100)),
                (pya.DPoint(4000, 5000), pya.DPoint(4000, 5100)),
                (pya.DPoint(3000, 5000), pya.DPoint(3000, 5100)),
            ],
        )
    assert "List of contacts should define a tuple of two DPoints for each reference" in str(expected_error.value)


def test_fail_if_contact_list_does_not_match_references2():
    with pytest.raises(ValueError) as expected_error:
        generate_probepoints_json(
            dummy_cell,
            references=["nw", "sw", "se", "ne"],
            contact=[
                (pya.DPoint(5000, 5000), pya.DPoint(5000, 5100)),
                (pya.DPoint(4000, 5000), pya.DPoint(4000, 5100)),
                (pya.DPoint(3000, 5000), pya.DPoint(3000, 5100)),
                (pya.DPoint(6000, 5000), pya.DPoint(6000, 5100)),
                (pya.DPoint(7000, 5000), pya.DPoint(7000, 5100)),
            ],
        )
    assert "List of contacts should define a tuple of two DPoints for each reference" in str(expected_error.value)


def test_fail_if_malformed_contact_arg_in_list():
    with pytest.raises(ValueError) as expected_error:
        generate_probepoints_json(
            dummy_cell,
            references=["nw", "sw", "se", "ne"],
            contact=[
                (pya.DPoint(5000, 5000), pya.DPoint(5000, 5100)),
                (pya.DPoint(4000, 5000), pya.DPoint(4000, 5100)),
                (pya.DPoint(3000, 5000),),
                (pya.DPoint(6000, 5000), pya.DPoint(6000, 5100)),
            ],
        )
    assert "List of contacts should define a tuple of two DPoints for each reference" in str(expected_error.value)


def test_generates_probepoints(dummy_cell, caplog):
    add_refpoint(dummy_cell, "QB1_probe_island_1", 3400, 2600)
    add_refpoint(dummy_cell, "QB1_probe_island_2", 3000, 2600)
    add_refpoint(dummy_cell, "QB2_probe_ground", 5400, 5600)
    add_refpoint(dummy_cell, "QB2_probe_island", 5000, 5600)
    probepoints = generate_probepoints_json(dummy_cell)
    assert not caplog.records, f"Didn't expect warnings but got following: {[x.message for x in caplog.records]}"
    site_is_at(probepoints, "testarray_1_probe_0", 4.0, 8.6, 4.4, 8.6)
    site_is_at(probepoints, "QB1_probe", 3.0, 2.6, 3.4, 2.6)
    site_is_at(probepoints, "QB2_probe", 5.0, 5.6, 5.4, 5.6)


def test_top_face_probepoints(dummy_cell, caplog):
    add_refpoint(dummy_cell, "QB1_probe_island_1", 3000, 2600)
    add_refpoint(dummy_cell, "QB1_probe_island_2", 3400, 2600)
    add_refpoint(dummy_cell, "QB2_probe_island", 5400, 5600)
    add_refpoint(dummy_cell, "QB2_probe_ground", 5000, 5600)
    probepoints = generate_probepoints_json(dummy_cell, face="2b1")
    assert not caplog.records, f"Didn't expect warnings but got following: {[x.message for x in caplog.records]}"
    top_chip_width, top_chip_offset_x, top_chip_offset_y = 7.0, 1.5, 1.5
    site_is_at(
        probepoints,
        "testarray_1_probe_0",
        round(top_chip_width - (4.4 - top_chip_offset_x), 4),
        round(8.6 - top_chip_offset_y, 4),
        round(top_chip_width - (4.0 - top_chip_offset_x), 4),
        round(8.6 - top_chip_offset_y, 4),
    )
    site_is_at(
        probepoints,
        "QB1_probe",
        round(top_chip_width - (3.4 - top_chip_offset_x), 4),
        round(2.6 - top_chip_offset_y, 4),
        round(top_chip_width - (3.0 - top_chip_offset_x), 4),
        round(2.6 - top_chip_offset_y, 4),
    )
    site_is_at(
        probepoints,
        "QB2_probe",
        round(top_chip_width - (5.4 - top_chip_offset_x), 4),
        round(5.6 - top_chip_offset_y, 4),
        round(top_chip_width - (5.0 - top_chip_offset_x), 4),
        round(5.6 - top_chip_offset_y, 4),
    )


def test_top_face_probepoints_no_flipping(dummy_cell, caplog):
    add_refpoint(dummy_cell, "QB1_probe_island_1", 3400, 2600)
    add_refpoint(dummy_cell, "QB1_probe_island_2", 3000, 2600)
    add_refpoint(dummy_cell, "QB2_probe_ground", 5400, 5600)
    add_refpoint(dummy_cell, "QB2_probe_island", 5000, 5600)
    probepoints = generate_probepoints_json(dummy_cell, face="2b1", flip_face=False)
    assert not caplog.records, f"Didn't expect warnings but got following: {[x.message for x in caplog.records]}"
    top_chip_offset_x, top_chip_offset_y = 1.5, 1.5
    site_is_at(
        probepoints,
        "testarray_1_probe_0",
        round(4.0 - top_chip_offset_x, 4),
        round(8.6 - top_chip_offset_y, 4),
        round(4.4 - top_chip_offset_x, 4),
        round(8.6 - top_chip_offset_y, 4),
    )
    site_is_at(
        probepoints,
        "QB1_probe",
        round(3.0 - top_chip_offset_x, 4),
        round(2.6 - top_chip_offset_y, 4),
        round(3.4 - top_chip_offset_x, 4),
        round(2.6 - top_chip_offset_y, 4),
    )
    site_is_at(
        probepoints,
        "QB2_probe",
        round(5.0 - top_chip_offset_x, 4),
        round(5.6 - top_chip_offset_y, 4),
        round(5.4 - top_chip_offset_x, 4),
        round(5.6 - top_chip_offset_y, 4),
    )


def test_warn_if_not_recommended_west_east_assigned_bottom_face(dummy_cell, caplog):
    add_refpoint(dummy_cell, "QB2_probe_island", 5400, 5600)
    add_refpoint(dummy_cell, "QB2_probe_ground", 5000, 5600)
    probepoints = generate_probepoints_json(dummy_cell)
    log_messages = [x.message for x in caplog.records]
    assert (
        len(caplog.records) == 1
    ), "Expected to have exactly one warning in the log for ground and island probes having non-standard sides"
    str1 = "Probepoint QB2_probe_island was mapped to east, but recommended direction for _probe_island is west"
    str2 = "Probepoint QB2_probe_ground was mapped to west, but recommended direction for _probe_ground is east"
    assert str1 in log_messages[0] or str2 in log_messages[0], f"Unexpected warning message: {log_messages[0]}"
    site_is_at(probepoints, "QB2_probe", 5.0, 5.6, 5.4, 5.6)


def test_warn_if_not_recommended_west_east_assigned_top_face(dummy_cell, caplog):
    add_refpoint(dummy_cell, "QB2_probe_ground", 5400, 5600)
    add_refpoint(dummy_cell, "QB2_probe_island", 5000, 5600)
    probepoints = generate_probepoints_json(dummy_cell, face="2b1")
    log_messages = [x.message for x in caplog.records]
    assert (
        len(caplog.records) == 1
    ), "Expected to have exactly one warning in the log for ground and island probes having non-standard sides"
    str1 = "Probepoint QB2_probe_island was mapped to east, but recommended direction for _probe_island is west"
    str2 = "Probepoint QB2_probe_ground was mapped to west, but recommended direction for _probe_ground is east"
    assert str1 in log_messages[0] or str2 in log_messages[0], f"Unexpected warning message: {log_messages[0]}"
    top_chip_width, top_chip_offset_x, top_chip_offset_y = 7.0, 1.5, 1.5
    site_is_at(
        probepoints,
        "QB2_probe",
        round(top_chip_width - (5.4 - top_chip_offset_x), 4),
        round(5.6 - top_chip_offset_y, 4),
        round(top_chip_width - (5.0 - top_chip_offset_x), 4),
        round(5.6 - top_chip_offset_y, 4),
    )


def test_warn_if_not_recommended_west_east_assigned_top_face_no_flip(dummy_cell, caplog):
    add_refpoint(dummy_cell, "QB2_probe_island", 5400, 5600)
    add_refpoint(dummy_cell, "QB2_probe_ground", 5000, 5600)
    probepoints = generate_probepoints_json(dummy_cell, face="2b1", flip_face=False)
    log_messages = [x.message for x in caplog.records]
    assert (
        len(caplog.records) == 1
    ), "Expected to have exactly one warning in the log for ground and island probes having non-standard sides"
    str1 = "Probepoint QB2_probe_island was mapped to east, but recommended direction for _probe_island is west"
    str2 = "Probepoint QB2_probe_ground was mapped to west, but recommended direction for _probe_ground is east"
    assert str1 in log_messages[0] or str2 in log_messages[0], f"Unexpected warning message: {log_messages[0]}"
    top_chip_offset_x, top_chip_offset_y = 1.5, 1.5
    site_is_at(
        probepoints,
        "QB2_probe",
        round(5.0 - top_chip_offset_x, 4),
        round(5.6 - top_chip_offset_y, 4),
        round(5.4 - top_chip_offset_x, 4),
        round(5.6 - top_chip_offset_y, 4),
    )


def test_probepoints_with_multiple_references1(empty_cell):
    add_refpoint(empty_cell, "QB1_probe_island_1", 2400, 5000)
    add_refpoint(empty_cell, "QB1_probe_island_2", 2000, 5000)
    add_refpoint(empty_cell, "testarray_2_probe_0_l", 8400, 2600)
    add_refpoint(empty_cell, "testarray_2_probe_0_r", 8000, 2600)
    add_refpoint(empty_cell, "testarray_1_probe_0_l", 2400, 8600)
    add_refpoint(empty_cell, "testarray_1_probe_0_r", 2000, 8600)
    add_refpoint(empty_cell, "QB2_probe_ground", 8400, 5000)
    add_refpoint(empty_cell, "QB2_probe_island", 8000, 5000)
    probepoints = generate_probepoints_json(empty_cell, references=["nw", "se"])
    assert set(probepoints.keys()) == {"groups"}, (
        "For multireference probepoint json expected to have 'groups' " f"member on top-level, was {probepoints}"
    )
    pp_nw = [pp for pp in probepoints["groups"] if pp["id"] == "NW"]
    pp_se = [pp for pp in probepoints["groups"] if pp["id"] == "SE"]
    assert pp_nw, "No probepoint group extracted with id 'NW'"
    assert pp_se, "No probepoint group extracted with id 'SE'"
    pp_nw, pp_se = pp_nw[0], pp_se[0]
    assert pp_nw["alignment"] == {"x": 1.5, "y": 8.5}, "Expected NW marker at 1.5,8.5"
    assert pp_se["alignment"] == {"x": 8.5, "y": 1.5}, "Expected SE marker at 8.5,1.5"
    assert len(pp_nw["sites"]) == 2, f"Expected to have exactly two 'NW' sites, got {pp_nw['sites']}"
    assert len(pp_se["sites"]) == 2, f"Expected to have exactly two 'SE' sites, got {pp_se['sites']}"
    site_is_at(pp_nw, "QB1_probe", 2.0, 5.0, 2.4, 5.0)
    site_is_at(pp_se, "testarray_2_probe_0", 8.0, 2.6, 8.4, 2.6)
    site_is_at(pp_nw, "testarray_1_probe_0", 2.0, 8.6, 2.4, 8.6)
    site_is_at(pp_se, "QB2_probe", 8.0, 5.0, 8.4, 5.0)


def test_probepoints_with_multiple_references2(empty_cell):
    add_refpoint(empty_cell, "QB1_probe_island_1", 2400, 2600)
    add_refpoint(empty_cell, "QB1_probe_island_2", 2000, 2600)
    add_refpoint(empty_cell, "testarray_2_probe_0_l", 8400, 2600)
    add_refpoint(empty_cell, "testarray_2_probe_0_r", 8000, 2600)
    add_refpoint(empty_cell, "testarray_1_probe_0_l", 2400, 8600)
    add_refpoint(empty_cell, "testarray_1_probe_0_r", 2000, 8600)
    add_refpoint(empty_cell, "QB2_probe_ground", 8400, 8600)
    add_refpoint(empty_cell, "QB2_probe_island", 8000, 8600)
    probepoints = generate_probepoints_json(empty_cell, references=["nw", "ne", "sw", "se"])
    assert set(probepoints.keys()) == {"groups"}, (
        "For multireference probepoint json expected to have 'groups' " f"member on top-level, was {probepoints}"
    )
    pp_nw = [pp for pp in probepoints["groups"] if pp["id"] == "NW"]
    pp_ne = [pp for pp in probepoints["groups"] if pp["id"] == "NE"]
    pp_sw = [pp for pp in probepoints["groups"] if pp["id"] == "SW"]
    pp_se = [pp for pp in probepoints["groups"] if pp["id"] == "SE"]
    assert pp_nw, "No probepoint group extracted with id 'NW'"
    assert pp_ne, "No probepoint group extracted with id 'NE'"
    assert pp_sw, "No probepoint group extracted with id 'SW'"
    assert pp_se, "No probepoint group extracted with id 'SE'"
    pp_nw, pp_ne, pp_sw, pp_se = pp_nw[0], pp_ne[0], pp_sw[0], pp_se[0]
    assert pp_nw["alignment"] == {"x": 1.5, "y": 8.5}, "Expected NW marker at 1.5,8.5"
    assert pp_ne["alignment"] == {"x": 8.5, "y": 8.5}, "Expected NE marker at 8.5,8.5"
    assert pp_sw["alignment"] == {"x": 1.5, "y": 1.5}, "Expected SW marker at 1.5,1.5"
    assert pp_se["alignment"] == {"x": 8.5, "y": 1.5}, "Expected SE marker at 8.5,1.5"
    assert len(pp_nw["sites"]) == 1, f"Expected to have exactly two 'NW' sites, got {pp_nw['sites']}"
    assert len(pp_ne["sites"]) == 1, f"Expected to have exactly two 'NE' sites, got {pp_ne['sites']}"
    assert len(pp_sw["sites"]) == 1, f"Expected to have exactly two 'SW' sites, got {pp_sw['sites']}"
    assert len(pp_se["sites"]) == 1, f"Expected to have exactly two 'SE' sites, got {pp_se['sites']}"
    site_is_at(pp_sw, "QB1_probe", 2.0, 2.6, 2.4, 2.6)
    site_is_at(pp_se, "testarray_2_probe_0", 8.0, 2.6, 8.4, 2.6)
    site_is_at(pp_nw, "testarray_1_probe_0", 2.0, 8.6, 2.4, 8.6)
    site_is_at(pp_ne, "QB2_probe", 8.0, 8.6, 8.4, 8.6)


def test_probepoints_with_multiple_references_doesnt_separate_site(empty_cell):
    add_refpoint(empty_cell, "testarray_2_probe_0_l", 8400, 2600)
    add_refpoint(empty_cell, "testarray_2_probe_0_r", 8000, 2600)
    add_refpoint(empty_cell, "testarray_1_probe_0_l", 2400, 8600)
    add_refpoint(empty_cell, "testarray_1_probe_0_r", 2000, 8600)
    add_refpoint(empty_cell, "QB2_probe_ground", 4800, 4000)
    add_refpoint(empty_cell, "QB2_probe_island", 5200, 4000)
    probepoints = generate_probepoints_json(empty_cell, references=["nw", "se"])
    pp_nw = [pp for pp in probepoints["groups"] if pp["id"] == "NW"]
    pp_se = [pp for pp in probepoints["groups"] if pp["id"] == "SE"]
    assert pp_nw, "No probepoint group extracted with id 'NW'"
    assert pp_se, "No probepoint group extracted with id 'SE'"
    pp_nw, pp_se = pp_nw[0], pp_se[0]
    assert len(pp_nw["sites"]) == 1, f"Expected to have exactly two 'NW' sites, got {pp_nw['sites']}"
    assert len(pp_se["sites"]) == 2, f"Expected to have exactly two 'SE' sites, got {pp_se['sites']}"
    site_is_at(pp_se, "testarray_2_probe_0", 8.0, 2.6, 8.4, 2.6)
    site_is_at(pp_nw, "testarray_1_probe_0", 2.0, 8.6, 2.4, 8.6)
    site_is_at(pp_se, "QB2_probe", 4.8, 4.0, 5.2, 4.0)


def test_probepoints_with_multiple_references_remove_empty_groups(empty_cell):
    add_refpoint(empty_cell, "QB1_probe_island_1", 2400, 6600)
    add_refpoint(empty_cell, "QB1_probe_island_2", 2000, 6600)
    add_refpoint(empty_cell, "testarray_2_probe_0_l", 8400, 2600)
    add_refpoint(empty_cell, "testarray_2_probe_0_r", 8000, 2600)
    add_refpoint(empty_cell, "testarray_1_probe_0_l", 2400, 8600)
    add_refpoint(empty_cell, "testarray_1_probe_0_r", 2000, 8600)
    add_refpoint(empty_cell, "QB2_probe_ground", 8400, 8600)
    add_refpoint(empty_cell, "QB2_probe_island", 8000, 8600)
    probepoints = generate_probepoints_json(empty_cell, references=["nw", "ne", "sw", "se"])
    pp_nw = [pp for pp in probepoints["groups"] if pp["id"] == "NW"]
    pp_ne = [pp for pp in probepoints["groups"] if pp["id"] == "NE"]
    pp_sw = [pp for pp in probepoints["groups"] if pp["id"] == "SW"]
    pp_se = [pp for pp in probepoints["groups"] if pp["id"] == "SE"]
    assert pp_nw, "No probepoint group extracted with id 'NW'"
    assert pp_ne, "No probepoint group extracted with id 'NE'"
    assert not pp_sw, f"There should be not probepoint group extracted with id 'SW', got {pp_sw}"
    assert pp_se, "No probepoint group extracted with id 'SE'"
    pp_nw, pp_ne, pp_se = pp_nw[0], pp_ne[0], pp_se[0]
    assert len(pp_nw["sites"]) == 2, f"Expected to have exactly two 'NW' sites, got {pp_nw['sites']}"
    assert len(pp_ne["sites"]) == 1, f"Expected to have exactly two 'NE' sites, got {pp_ne['sites']}"
    assert len(pp_se["sites"]) == 1, f"Expected to have exactly two 'SE' sites, got {pp_se['sites']}"
    site_is_at(pp_nw, "QB1_probe", 2.0, 6.6, 2.4, 6.6)
    site_is_at(pp_se, "testarray_2_probe_0", 8.0, 2.6, 8.4, 2.6)
    site_is_at(pp_nw, "testarray_1_probe_0", 2.0, 8.6, 2.4, 8.6)
    site_is_at(pp_ne, "QB2_probe", 8.0, 8.6, 8.4, 8.6)


def test_three_probe_points(dummy_cell, caplog):
    add_refpoint(dummy_cell, "testarray_2_probe_0_l", 8000, 2600)
    add_refpoint(dummy_cell, "testarray_2_probe_0_r", 8400, 2600)
    add_refpoint(dummy_cell, "testarray_2_probe_0_top", 8200, 2700)
    probepoints = generate_probepoints_json(dummy_cell)
    assert not caplog.records, f"Didn't expect warnings but got following: {[x.message for x in caplog.records]}"
    site_is_at(probepoints, "testarray_2_probe_0", 8.0, 2.6, 8.4, 2.6)
    site_is_at(probepoints, "testarray_2_probe_0_top_east", 8.2, 2.7, 8.4, 2.6)
    site_is_at(probepoints, "testarray_2_probe_0_top_west", 8.0, 2.6, 8.2, 2.7)


def test_three_probe_points_with_multiple_references(empty_cell):
    add_refpoint(empty_cell, "testarray_2_probe_0_l", 4900, 4900)
    add_refpoint(empty_cell, "testarray_2_probe_0_r", 5100, 4900)
    add_refpoint(empty_cell, "testarray_2_probe_0_top", 5000, 5100)
    probepoints = generate_probepoints_json(empty_cell, references=["nw", "se"])
    pp_nw = [pp for pp in probepoints["groups"] if pp["id"] == "NW"]
    pp_se = [pp for pp in probepoints["groups"] if pp["id"] == "SE"]
    assert pp_nw, "No probepoint group extracted with id 'NW'"
    assert pp_se, "No probepoint group extracted with id 'SE'"
    pp_nw, pp_se = pp_nw[0], pp_se[0]
    site_is_at(pp_se, "testarray_2_probe_0", 4.9, 4.9, 5.1, 4.9)
    site_is_at(pp_se, "testarray_2_probe_0_top_east", 5.0, 5.1, 5.1, 4.9)
    site_is_at(pp_nw, "testarray_2_probe_0_top_west", 4.9, 4.9, 5.0, 5.1)


def test_contact_pair_can_be_defined(dummy_cell):
    probepoints = generate_probepoints_json(dummy_cell, contact=(pya.DPoint(2000, 3000), pya.DPoint(2100, 3000)))
    assert len(probepoints["sites"]) == 2, f"Expected exactly two sites, got {probepoints}"
    site_is_at(probepoints, "testarray_1_probe_0", 4.0, 8.6, 4.4, 8.6)
    site_is_at(probepoints, "contact", 2.0, 3.0, 2.1, 3.0)


def test_contact_designates_west_east_top_face(dummy_cell):
    probepoints = generate_probepoints_json(
        dummy_cell, face="2b1", contact=(pya.DPoint(2000, 3000), pya.DPoint(2100, 3000))
    )
    assert len(probepoints["sites"]) == 2, f"Expected exactly two sites, got {probepoints}"
    top_chip_width, top_chip_offset_x, top_chip_offset_y = 7.0, 1.5, 1.5
    site_is_at(
        probepoints,
        "testarray_1_probe_0",
        round(top_chip_width - (4.4 - top_chip_offset_x), 4),
        round(8.6 - top_chip_offset_y, 4),
        round(top_chip_width - (4.0 - top_chip_offset_x), 4),
        round(8.6 - top_chip_offset_y, 4),
    )
    site_is_at(
        probepoints,
        "contact",
        round(top_chip_width - (2.1 - top_chip_offset_x), 4),
        round(3.0 - top_chip_offset_y, 4),
        round(top_chip_width - (2.0 - top_chip_offset_x), 4),
        round(3.0 - top_chip_offset_y, 4),
    )


def test_contact_designates_west_east_top_face_no_flip(dummy_cell):
    probepoints = generate_probepoints_json(
        dummy_cell, face="2b1", flip_face=False, contact=(pya.DPoint(2000, 3000), pya.DPoint(2100, 3000))
    )
    assert len(probepoints["sites"]) == 2, f"Expected exactly two sites, got {probepoints}"
    top_chip_offset_x, top_chip_offset_y = 1.5, 1.5
    site_is_at(
        probepoints,
        "testarray_1_probe_0",
        round(4.0 - top_chip_offset_x, 4),
        round(8.6 - top_chip_offset_y, 4),
        round(4.4 - top_chip_offset_x, 4),
        round(8.6 - top_chip_offset_y, 4),
    )
    site_is_at(
        probepoints,
        "contact",
        round(2.0 - top_chip_offset_x, 4),
        round(3.0 - top_chip_offset_y, 4),
        round(2.1 - top_chip_offset_x, 4),
        round(3.0 - top_chip_offset_y, 4),
    )


def test_one_contact_pair_for_multireference(empty_cell):
    add_refpoint(empty_cell, "QB1_probe_island_1", 2400, 2600)
    add_refpoint(empty_cell, "QB1_probe_island_2", 2000, 2600)
    add_refpoint(empty_cell, "testarray_2_probe_0_l", 8400, 2600)
    add_refpoint(empty_cell, "testarray_2_probe_0_r", 8000, 2600)
    add_refpoint(empty_cell, "testarray_1_probe_0_l", 2400, 8600)
    add_refpoint(empty_cell, "testarray_1_probe_0_r", 2000, 8600)
    add_refpoint(empty_cell, "QB2_probe_ground", 8400, 8600)
    add_refpoint(empty_cell, "QB2_probe_island", 8000, 8600)
    probepoints = generate_probepoints_json(
        empty_cell, references=["nw", "ne", "sw", "se"], contact=(pya.DPoint(2100, 7500), pya.DPoint(2300, 7500))
    )
    pp_nw = [pp for pp in probepoints["groups"] if pp["id"] == "NW"][0]
    pp_ne = [pp for pp in probepoints["groups"] if pp["id"] == "NE"][0]
    pp_sw = [pp for pp in probepoints["groups"] if pp["id"] == "SW"][0]
    pp_se = [pp for pp in probepoints["groups"] if pp["id"] == "SE"][0]
    site_is_at(pp_nw, "testarray_1_probe_0", 2.0, 8.6, 2.4, 8.6)
    site_is_at(pp_ne, "QB2_probe", 8.0, 8.6, 8.4, 8.6)
    site_is_at(pp_sw, "QB1_probe", 2.0, 2.6, 2.4, 2.6)
    site_is_at(pp_se, "testarray_2_probe_0", 8.0, 2.6, 8.4, 2.6)
    site_is_at(pp_nw, "contact", 2.1, 7.5, 2.3, 7.5)
    site_is_at(pp_ne, "contact", 2.1, 7.5, 2.3, 7.5)
    site_is_at(pp_sw, "contact", 2.1, 7.5, 2.3, 7.5)
    site_is_at(pp_se, "contact", 2.1, 7.5, 2.3, 7.5)


def test_multiple_contacts_for_multireference(empty_cell):
    add_refpoint(empty_cell, "QB1_probe_island_1", 2400, 2600)
    add_refpoint(empty_cell, "QB1_probe_island_2", 2000, 2600)
    add_refpoint(empty_cell, "testarray_2_probe_0_l", 8400, 2600)
    add_refpoint(empty_cell, "testarray_2_probe_0_r", 8000, 2600)
    add_refpoint(empty_cell, "testarray_1_probe_0_l", 2400, 8600)
    add_refpoint(empty_cell, "testarray_1_probe_0_r", 2000, 8600)
    add_refpoint(empty_cell, "QB2_probe_ground", 8400, 8600)
    add_refpoint(empty_cell, "QB2_probe_island", 8000, 8600)
    probepoints = generate_probepoints_json(
        empty_cell,
        references=["nw", "ne", "sw", "se"],
        contact=[
            (pya.DPoint(8200, 3400), pya.DPoint(8400, 3400)),
            (pya.DPoint(2200, 3500), pya.DPoint(2400, 3500)),
            (pya.DPoint(8100, 7400), pya.DPoint(8300, 7400)),
            (pya.DPoint(2100, 7500), pya.DPoint(2300, 7500)),
        ],
    )
    pp_nw = [pp for pp in probepoints["groups"] if pp["id"] == "NW"][0]
    pp_ne = [pp for pp in probepoints["groups"] if pp["id"] == "NE"][0]
    pp_sw = [pp for pp in probepoints["groups"] if pp["id"] == "SW"][0]
    pp_se = [pp for pp in probepoints["groups"] if pp["id"] == "SE"][0]
    site_is_at(pp_nw, "testarray_1_probe_0", 2.0, 8.6, 2.4, 8.6)
    site_is_at(pp_ne, "QB2_probe", 8.0, 8.6, 8.4, 8.6)
    site_is_at(pp_sw, "QB1_probe", 2.0, 2.6, 2.4, 2.6)
    site_is_at(pp_se, "testarray_2_probe_0", 8.0, 2.6, 8.4, 2.6)
    site_is_at(pp_nw, "contact", 8.2, 3.4, 8.4, 3.4)
    site_is_at(pp_ne, "contact", 2.2, 3.5, 2.4, 3.5)
    site_is_at(pp_sw, "contact", 8.1, 7.4, 8.3, 7.4)
    site_is_at(pp_se, "contact", 2.1, 7.5, 2.3, 7.5)


def test_duplicate_sites_removed(empty_cell, caplog):
    add_refpoint(empty_cell, "testarray_short_name_l", 4400, 2600)
    add_refpoint(empty_cell, "testarray_short_name_r", 4000, 2600)
    add_refpoint(empty_cell, "testarray_veery_loong_name_l", 4000, 2600)
    add_refpoint(empty_cell, "testarray_veery_loong_name_r", 4400, 2600)
    probepoints = generate_probepoints_json(empty_cell)
    log_messages = [x.message for x in caplog.records]
    assert len(log_messages) == 4, f"Expected to have four row warning in the log, got: {log_messages}"
    assert (
        "Found two sites " in log_messages[0]
        and "'testarray_short_name'" in log_messages[0]
        and "'testarray_veery_loong_name'" in log_messages[0]
        and " with similar coordinates (respectively)" in log_messages[0]
    ), f"Unexpected warning message: {log_messages}"
    assert "  west 4.0,2.6 = 4.0,2.6" in log_messages[1], f"Unexpected warning message: {log_messages}"
    assert "  east 4.4,2.6 = 4.4,2.6" in log_messages[2], f"Unexpected warning message: {log_messages}"
    assert (
        "  will only keep the site 'testarray_veery_loong_name'" in log_messages[3]
    ), f"Unexpected warning message: {log_messages}"
    assert len(probepoints["sites"]) == 1, f"Expected exactly one site, got {probepoints}"
    site_is_at(probepoints, "testarray_veery_loong_name", 4.0, 2.6, 4.4, 2.6)


def test_close_sites_removed(empty_cell, caplog):
    add_refpoint(empty_cell, "testarray_short_name_l", 4400.1, 2600)
    add_refpoint(empty_cell, "testarray_short_name_r", 4000, 2600.1)
    add_refpoint(empty_cell, "testarray_veery_loong_name_l", 4000.1, 2600)
    add_refpoint(empty_cell, "testarray_veery_loong_name_r", 4400, 2600.1)
    probepoints = generate_probepoints_json(empty_cell)
    log_messages = [x.message for x in caplog.records]
    assert len(log_messages) == 4, f"Expected to have four row warning in the log, got: {log_messages}"
    assert (
        "Found two sites " in log_messages[0]
        and "'testarray_short_name'" in log_messages[0]
        and "'testarray_veery_loong_name'" in log_messages[0]
        and " with similar coordinates (respectively)" in log_messages[0]
    ), f"Unexpected warning message: {log_messages}"
    assert (
        "  west " in log_messages[1] and "4.0,2.6001" in log_messages[1] and "4.0001,2.6" in log_messages[1]
    ), f"Unexpected warning message: {log_messages}"
    assert (
        "  east " in log_messages[2] and "4.4001,2.6" in log_messages[2] and "4.4,2.6001" in log_messages[2]
    ), f"Unexpected warning message: {log_messages}"
    assert (
        "  will only keep the site 'testarray_veery_loong_name'" in log_messages[3]
    ), f"Unexpected warning message: {log_messages}"
    assert len(probepoints["sites"]) == 1, f"Expected exactly one site, got {probepoints}"
    site_is_at(probepoints, "testarray_veery_loong_name", 4.0001, 2.6, 4.4, 2.6001)


def test_far_enough_sites_stay(empty_cell, caplog):
    add_refpoint(empty_cell, "testarray_short_name_l", 4402, 2600)
    add_refpoint(empty_cell, "testarray_short_name_r", 4000, 2602)
    add_refpoint(empty_cell, "testarray_veery_loong_name_l", 4002, 2600)
    add_refpoint(empty_cell, "testarray_veery_loong_name_r", 4400, 2602)
    probepoints = generate_probepoints_json(empty_cell)
    log_messages = [x.message for x in caplog.records]
    assert not log_messages, f"Unexpected warnings in the log: {log_messages}"
    assert len(probepoints["sites"]) == 2, f"Expected two distinct sites, got {probepoints}"
    site_is_at(probepoints, "testarray_veery_loong_name", 4.002, 2.6, 4.4, 2.602)
    site_is_at(probepoints, "testarray_short_name", 4.0, 2.602, 4.402, 2.6)


def test_warn_if_only_one_probepoint_per_site(dummy_cell, caplog):
    add_refpoint(dummy_cell, "testarray_solitary_r", 5000, 5000)
    probepoints = generate_probepoints_json(dummy_cell)
    log_messages = [x.message for x in caplog.records]
    assert len(log_messages) == 1, "Expected exactly one warning about site with one probepoint"
    assert (
        "Malformed site object detected: " in log_messages[0] and "'id': 'testarray_solitary'" in log_messages[0]
    ), f"Unexpected warning: {log_messages[0]}"
    site_is_at(probepoints, "testarray_1_probe_0", 4.0, 8.6, 4.4, 8.6)
    site_is_at(probepoints, "testarray_solitary", 5.0, 5.0, 5.0, 5.0)
