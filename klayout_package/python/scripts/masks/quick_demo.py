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

"""This is a fast Demo mask."""

from kqcircuits.chips.chip import Chip
from kqcircuits.chips.demo import Demo
from kqcircuits.masks.mask_set import MaskSet


qdemo = MaskSet(name="Quick", version=1, with_grid=False)

layers_to_mask = {"base_metal_gap": "1", "underbump_metallization": "2", "indium_bump": "3"}

# b-face mask
qdemo.add_mask_layout(
    [
        ["---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---"],
        ["---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---"],
        ["---", "---", "---", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "DE1", "---", "---", "---"],
        ["---", "---", "DE1", "---", "---", "---", "---", "---", "---", "---", "---", "---", "DE1", "---", "---"],
        ["---", "---", "DE1", "---", "CH1", "CH1", "---", "---", "---", "CH1", "CH1", "---", "DE1", "---", "---"],
        ["---", "DE1", "---", "---", "CH1", "CH1", "---", "---", "---", "CH1", "CH1", "---", "---", "DE1", "---"],
        ["---", "DE1", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "DE1", "---"],
        ["---", "DE1", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "DE1", "---"],
        ["---", "DE1", "---", "CH1", "---", "---", "---", "---", "---", "---", "---", "CH1", "---", "DE1", "---"],
        ["---", "DE1", "---", "---", "CH1", "---", "---", "---", "---", "---", "CH1", "---", "---", "DE1", "---"],
        ["---", "---", "DE1", "---", "---", "CH1", "CH1", "CH1", "CH1", "CH1", "---", "---", "DE1", "---", "---"],
        ["---", "---", "DE1", "---", "---", "---", "---", "---", "---", "---", "---", "---", "DE1", "---", "---"],
        ["---", "---", "---", "DE1", "DE1", "---", "---", "---", "---", "---", "DE1", "DE1", "---", "---", "---"],
        ["---", "---", "---", "---", "---", "DE1", "DE1", "DE1", "DE1", "DE1", "---", "---", "---", "---", "---"],
        ["---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---"],
    ],
    "1t1",
    layers_to_mask=layers_to_mask,
)

# This is just a demonstration how to generate netlists with something else than 'default_netlist_breakdown'.
alt_nets = {"2nd": ["Meander"], "3rd": []}

# chip definitions
qdemo.add_chip(
    [
        (Chip, "CH1"),
        (Demo, "DE1", {"alt_netlists": alt_nets}),
    ],
    cpus=2,
)

# Alternatively, to add them one-by-one:
# qdemo.add_chip(Chip, "CH1")
# qdemo.add_chip(Demo, "DE1")

qdemo.build()
qdemo.export()
