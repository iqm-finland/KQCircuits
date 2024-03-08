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
from kqcircuits.masks.mask_layout import MaskLayout


@pytest.fixture
def all_valid_coordinates():
    """List of pairs of all valid chip coordinates and labels they map to"""
    result = []
    for i in range(0, len(range(ord("A"), ord("Z") + 1))):
        for j in range(0, 100):
            result.append([i, j])
    idx = 0
    for c in [chr(cc) for cc in range(ord("A"), ord("Z") + 1)]:
        for j in range(0, 100):
            result[idx].append(f"{c}{j:02d}")
            idx += 1
    return result


def test_two_coordinates_to_position_label(all_valid_coordinates):
    for coord in all_valid_coordinates:
        actual_result = MaskLayout.two_coordinates_to_position_label(coord[0], coord[1])
        assert actual_result == coord[2], (
            f"MaskLayout.two_coordinates_to_position_label({coord[0]}, {coord[1]}) expected to be {coord[2]}, "
            f"got {actual_result}"
        )


def test_position_label_to_two_coordinates(all_valid_coordinates):
    for coord in all_valid_coordinates:
        actual_result = MaskLayout.position_label_to_two_coordinates(coord[2])
        assert actual_result == (coord[0], coord[1]), (
            f"MaskLayout.position_label_to_two_coordinates({coord[2]}) expected to be ({coord[0]}, {coord[1]}), "
            f"got {actual_result}"
        )


def test_commutativity(all_valid_coordinates):
    for coord in all_valid_coordinates:
        actual_result = MaskLayout.position_label_to_two_coordinates(
            MaskLayout.two_coordinates_to_position_label(coord[0], coord[1])
        )
        assert actual_result == (coord[0], coord[1]), (
            "MaskLayout.position_label_to_two_coordinates"
            f"(MaskLayout.two_coordinates_to_position_label(coord[0], coord[1])) returned {actual_result}"
        )
        actual_result2 = MaskLayout.two_coordinates_to_position_label(
            *MaskLayout.position_label_to_two_coordinates(coord[2])
        )
        assert actual_result2 == coord[2], (
            "MaskLayout.two_coordinates_to_position_label"
            f"(MaskLayout.position_label_to_two_coordinates(coord[2])) returned {actual_result2}"
        )


def test_invalid_two_coordinates_to_position_label_1():
    with pytest.raises(ValueError) as expected_error:
        MaskLayout.two_coordinates_to_position_label(-1, 1)
    assert "Row coordinate -1 out of bounds" in str(expected_error.value)


def test_invalid_two_coordinates_to_position_label_2():
    with pytest.raises(ValueError) as expected_error:
        MaskLayout.two_coordinates_to_position_label(91, 1)
    assert "Row coordinate 91 out of bounds" in str(expected_error.value)


def test_invalid_two_coordinates_to_position_label_3():
    with pytest.raises(ValueError) as expected_error:
        MaskLayout.two_coordinates_to_position_label(1, -1)
    assert "Column coordinate -1 out of bounds" in str(expected_error.value)


def test_invalid_two_coordinates_to_position_label_4():
    with pytest.raises(ValueError) as expected_error:
        MaskLayout.two_coordinates_to_position_label(1, 100)
    assert "Column coordinate 100 out of bounds" in str(expected_error.value)


def test_invalid_position_label_to_two_coordinates_1():
    with pytest.raises(ValueError) as expected_error:
        MaskLayout.position_label_to_two_coordinates("@03")
    assert "Letter part in @03 out of bounds" in str(expected_error.value)


def test_invalid_position_label_to_two_coordinates_2():
    with pytest.raises(ValueError) as expected_error:
        MaskLayout.position_label_to_two_coordinates("[03")
    assert "Letter part in [03 out of bounds" in str(expected_error.value)


def test_invalid_position_label_to_two_coordinates_3():
    with pytest.raises(ValueError) as expected_error:
        MaskLayout.position_label_to_two_coordinates("C-1")
    assert "Number part in C-1 out of bounds" in str(expected_error.value)


def test_invalid_position_label_to_two_coordinates_4():
    with pytest.raises(ValueError) as expected_error:
        MaskLayout.position_label_to_two_coordinates("C100")
    assert "Number part in C100 out of bounds" in str(expected_error.value)
