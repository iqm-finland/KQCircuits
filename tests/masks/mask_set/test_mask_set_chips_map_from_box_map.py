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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


from kqcircuits.masks.mask_set import MaskSet


def test_box_map_identical_boxes():

    box_map = {
        "A": [
            ["A", "B", "C"],
            ["D", "E", "F"],
            ["G", "H", "I"],
        ]
    }

    mask_map = [
        ["A", "A", "A", "A", "A"],
        ["A", "A", "A", "A", "A"],
        ["A", "A", "A", "A", "A"],
        ["A", "A", "A", "A", "A"],
        ["A", "A", "A", "A", "A"],
    ]

    mask_layout = MaskSet.chips_map_from_box_map(box_map, mask_map)

    correct_mask_layout = [
        ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C"],
        ["D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F"],
        ["G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I"],
        ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C"],
        ["D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F"],
        ["G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I"],
        ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C"],
        ["D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F"],
        ["G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I"],
        ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C"],
        ["D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F"],
        ["G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I"],
        ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C"],
        ["D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F"],
        ["G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I"],
    ]

    assert mask_layout == correct_mask_layout


def test_box_map_different_boxes():

    box_map = {
        "A": [
            ["A", "B", "C"],
            ["D", "E", "F"],
            ["G", "H", "I"],
        ],
        "B": [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
        ],
    }

    mask_map = [
        ["A", "A", "A", "A", "A"],
        ["A", "B", "A", "B", "A"],
        ["A", "A", "A", "A", "A"],
        ["A", "B", "A", "B", "A"],
        ["A", "A", "A", "A", "A"],
    ]

    mask_layout = MaskSet.chips_map_from_box_map(box_map, mask_map)

    correct_mask_layout = [
        ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C"],
        ["D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F"],
        ["G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I"],
        ["A", "B", "C", "1", "2", "3", "A", "B", "C", "1", "2", "3", "A", "B", "C"],
        ["D", "E", "F", "4", "5", "6", "D", "E", "F", "4", "5", "6", "D", "E", "F"],
        ["G", "H", "I", "7", "8", "9", "G", "H", "I", "7", "8", "9", "G", "H", "I"],
        ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C"],
        ["D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F"],
        ["G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I"],
        ["A", "B", "C", "1", "2", "3", "A", "B", "C", "1", "2", "3", "A", "B", "C"],
        ["D", "E", "F", "4", "5", "6", "D", "E", "F", "4", "5", "6", "D", "E", "F"],
        ["G", "H", "I", "7", "8", "9", "G", "H", "I", "7", "8", "9", "G", "H", "I"],
        ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C", "A", "B", "C"],
        ["D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F", "D", "E", "F"],
        ["G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I", "G", "H", "I"],
    ]

    assert mask_layout == correct_mask_layout
