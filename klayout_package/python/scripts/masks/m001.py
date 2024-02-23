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

"""M001 mask.

Q and AB tests. Showcases box maps and how to load cells from files to a mask.

"""
from kqcircuits.chips.airbridge_crossings import AirbridgeCrossings
from kqcircuits.chips.quality_factor import QualityFactor
from kqcircuits.pya_resolver import pya
from kqcircuits.defaults import TMP_PATH
from kqcircuits.klayout_view import KLayoutView
from kqcircuits.masks.mask_set import MaskSet

m001 = MaskSet(name="M001", version=2, with_grid=False)

box_map = {
    "A": [
        ["AB1", "AB2", "QSG"],
        ["QSA", "QSC", "QDG"],
        ["QDA", "QDC", "QDD"],
    ]
}

mask_map = [
    ["A", "A", "A", "A", "A"],
    ["A", "A", "A", "A", "A"],
    ["A", "A", "A", "A", "A"],
    ["A", "A", "A", "A", "A"],
    ["A", "A", "A", "A", "A"],
]

m001.add_mask_layout(MaskSet.chips_map_from_box_map(box_map, mask_map))

# fmt: off
parameters_qd = {
    "res_lengths": [4649.6, 4743.3, 4869.9, 4962.9, 5050.7, 5138.7, 5139., 5257., 5397.4, 5516.8, 5626.6, 5736.2,
                    5742.9, 5888.7, 6058.3, 6202.5, 6350., 6489.4],
    "type_coupler": ["interdigital", "interdigital", "interdigital", "gap", "gap", "gap", "interdigital",
                     "interdigital", "interdigital", "gap", "gap", "gap", "interdigital", "interdigital",
                     "interdigital", "interdigital", "gap", "gap"],
    "l_fingers": [19.9, 54.6, 6.7, 9.7, 22.8, 30.5, 26.1, 14.2, 18.2, 10.9, 19.8, 26.4, 34.2, 19.9, 25.3, 8., 15.8,
                  22.2],
    "n_fingers": [4, 2, 2, 4, 4, 4, 4, 4, 2, 4, 4, 4, 4, 4, 2, 2, 4, 4],
    "res_beg": ["galvanic"] * 18,
    "res_a": [10] * 18,
    "res_b": [6] * 18
}
# fmt: on

parameters_qs = {
    "res_lengths": [4649.6, 4908.9, 5208.5, 5516.8, 5848.9, 6217.4],
    "type_coupler": ["interdigital", "interdigital", "interdigital", "gap", "gap", "gap"],
    "l_fingers": [19.9, 7.3, 15.2, 10.9, 18.5, 23.6],
    "n_fingers": [4, 4, 2, 4, 4, 4],
    "res_beg": ["galvanic"] * 6,
    "res_a": [10] * 6,
    "res_b": [6] * 6,
}

# Let's generate a static OASIS file first:
view_2 = KLayoutView()
view_2.insert_cell(
    QualityFactor,
    name_chip="QDD",
    name_mask="M001",
    **{**parameters_qd, "n_ab": 18 * [5], "res_term": 18 * ["airbridge"]},
)
save_opts = pya.SaveLayoutOptions()
save_opts.write_context_info = True
file_name = str(TMP_PATH / "m001_QDD.oas")
view_2.top_cell.write(file_name, save_opts)
view_2.close()

print("Loading:", file_name)
m001.add_chip(file_name, "QDD")

m001.add_chip(
    [
        (AirbridgeCrossings, "AB1", {"crossings": 1}),
        (AirbridgeCrossings, "AB2", {"crossings": 10}),
        (QualityFactor, "QSG", {**parameters_qs, "n_ab": 6 * [0], "res_term": 6 * ["galvanic"]}),
        (QualityFactor, "QSA", {**parameters_qs, "n_ab": 6 * [0], "res_term": 6 * ["airbridge"]}),
        (QualityFactor, "QSC", {**parameters_qs, "n_ab": 6 * [5], "res_term": 6 * ["galvanic"]}),
        (QualityFactor, "QDG", {**parameters_qd, "n_ab": 18 * [0], "res_term": 18 * ["galvanic"]}),
        (QualityFactor, "QDA", {**parameters_qd, "n_ab": 18 * [0], "res_term": 18 * ["airbridge"]}),
        (QualityFactor, "QDC", {**parameters_qd, "n_ab": 18 * [5], "res_term": 18 * ["galvanic"]}),
    ]
)

m001.build()
m001.export()
