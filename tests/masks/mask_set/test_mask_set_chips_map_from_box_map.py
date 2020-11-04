# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.masks.mask_set import MaskSet


def test_box_map_identical_boxes():

    box_map = {"A": [
        ["A", "B", "C"],
        ["D", "E", "F"],
        ["G", "H", "I"],
    ]}

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
        ]
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
