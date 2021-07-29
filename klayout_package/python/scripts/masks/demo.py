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

"""Demo mask."""

from kqcircuits.chips.airbridge_crossings import AirbridgeCrossings
from kqcircuits.chips.chip import Chip
from kqcircuits.chips.demo import Demo
from kqcircuits.chips.junction_test import JunctionTest
from kqcircuits.chips.junction_test2 import JunctionTest2
from kqcircuits.chips.quality_factor import QualityFactor
from kqcircuits.chips.shaping import Shaping
from kqcircuits.chips.single_xmons import SingleXmons
from kqcircuits.chips.stripes import Stripes
from kqcircuits.chips.multi_face.demo_twoface import DemoTwoface
from kqcircuits.chips.multi_face.multi_face import MultiFace
from kqcircuits.defaults import TMP_PATH
from kqcircuits.masks.mask_set import MaskSet
from kqcircuits.klayout_view import KLayoutView


view = KLayoutView(current=True, initialize=True)
layout = KLayoutView.get_active_layout()

mdemo = MaskSet(layout, name="Demo", version=1, with_grid=False,
                mask_export_layers=["base_metal_gap", "base_metal_gap_wo_grid", "underbump_metallization",
                                    "indium_bump"]
                )

layers_to_mask = {
    "base_metal_gap": "1",
    "underbump_metallization": "2",
    "indium_bump": "3"
}

# b-face mask
mdemo.add_mask_layout([
    ["---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---"],
    ["---", "---", "---", "---", "---", "DE1", "DE1", "DE1", "DE1", "DE1", "---", "---", "---", "---", "---"],
    ["---", "---", "---", "AC1", "AC1", "DT1", "DT1", "DT1", "DT1", "DT1", "JT1", "JT1", "---", "---", "---"],
    ["---", "---", "CH1", "AC1", "AC1", "JT1", "JT1", "JT1", "JT1", "JT1", "JT1", "JT1", "JT1", "---", "---"],
    ["---", "---", "CH1", "AC1", "AC1", "QF1", "QF1", "QF1", "QF1", "QF1", "QF1", "QF1", "QF1", "---", "---"],
    ["---", "DE1", "CH1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
    ["---", "DE1", "CH1", "SX1", "SX1", "SX1", "SX1", "SX1", "SX1", "SX1", "SX1", "SX1", "SX1", "SX1", "---"],
    ["---", "DE1", "CH1", "QF1", "QF1", "QF1", "QF1", "QF1", "QF1", "QF1", "MF1", "CH1", "DE1", "DE1", "---"],
    ["---", "DE1", "CH1", "SH1", "SH1", "SH1", "SH1", "SH1", "SH1", "SH1", "MF1", "MF1", "DE1", "DE1", "---"],
    ["---", "DE1", "CH1", "SH1", "SH1", "SH1", "SH1", "SH1", "SH1", "SH1", "MF1", "MF1", "DE1", "DE1", "---"],
    ["---", "---", "CH1", "AC1", "AC1", "AC1", "AC1", "AC1", "AC1", "AC1", "MF1", "MF1", "AC1", "---", "---"],
    ["---", "---", "CH1", "ST1", "ST1", "ST1", "ST1", "ST1", "ST1", "ST1", "ST1", "ST1", "ST1", "---", "---"],
    ["---", "---", "---", "JT2", "JT2", "JT2", "JT2", "JT2", "JT2", "JT2", "JT2", "JT2", "---", "---", "---"],
    ["---", "---", "---", "---", "---", "SX1", "SX1", "SX1", "SX1", "SX1", "---", "---", "---", "---", "---"],
    ["---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---"],
], "b", layers_to_mask=layers_to_mask)

# t-face mask
# pylint: disable=line-too-long
mdemo.add_mask_layout([
    ["---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---"],
    ["---", "---", "---", "---", "---", "---", "MF1", "MF1", "MF1", "MF1", "MF1", "MF1", "MF1", "MF1", "MF1", "---", "---", "---", "---", "---", "---"],
    ["---", "---", "---", "---", "---", "MF1", "MF1", "MF1", "MF1", "MF1", "MF1", "MF1", "MF1", "MF1", "MF1", "MF1", "---", "---", "---", "---", "---"],
    ["---", "---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---", "---"],
    ["---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---"],
    ["---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---"],
    ["---", "MF1", "MF1", "MF1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
    ["---", "MF1", "MF1", "MF1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
    ["---", "MF1", "MF1", "MF1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
    ["---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "MF1", "MF1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
    ["---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "MF1", "MF1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
    ["---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
    ["---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
    ["---", "DT1", "DT1", "DT1", "DT1", "MF1", "MF1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
    ["---", "DT1", "DT1", "DT1", "DT1", "MF1", "MF1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---"],
    ["---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---"],
    ["---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---"],
    ["---", "---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---", "---"],
    ["---", "---", "---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---", "---", "---"],
    ["---", "---", "---", "---", "---", "---", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "DT1", "---", "---", "---", "---", "---", "---"],
    ["---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---", "---"],
], "t", layers_to_mask=layers_to_mask)
# pylint: enable=line-too-long

# chip definitions
mdemo.add_chip(AirbridgeCrossings, "AC1", b_number=4, crossings=8)
mdemo.add_chip(Chip, "CH1")
mdemo.add_chip(Demo, "DE1")
mdemo.add_chip(DemoTwoface, "DT1")
mdemo.add_chip(JunctionTest, "JT1")
mdemo.add_chip(JunctionTest2, "JT2", pad_width=300)
mdemo.add_chip(MultiFace, "MF1")
mdemo.add_chip(QualityFactor, "QF1", n_ab=[1, 2, 3, 4, 5, 6])
mdemo.add_chip(Shaping, "SH1")
mdemo.add_chip(SingleXmons, "SX1")
mdemo.add_chip(Stripes, "ST1")

mdemo.build()
mdemo.export(TMP_PATH, view)
