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

"""
This mask layout demonstrates using multiple faces on a single wafer. As example, we use `1t1` as the top face, and
`1b1` as the bottom face of the wafer. We draw some example chips with metalization on both faces, and TSVs to connect
them together.

A separate MaskLayout is generated for each face, which means that things like markers can be customized on each side
of the wafer if needed. However, it is important that the chips on both sides line up exactly. The method
`MaskSet.add_multi_face_mask_layout` helps with this: it creates identical mask layouts for multiple faces, except for
any differences per face that are specified explicitly.

To generate this example, run `kqc mask demo_multiface.py` in the command line.

In this example, we use the convention that in the full mask files (`DemoMF_v1_1b1.oas` and `DemoMF_v1_1t1.oas`), all
shapes are seen from the top, so looking at `1t1` and seeing `1b1` "through the wafer". Hence, `1t1` is drawn with text
readable normally, and `1b1` with text mirrored. One can verify the combined mask of both side by opening both of these
`oas` files in KLayout in the same panel.

To draw the mirrored texts in `1b1`, we set `mirror_labels=True` for the mask layout, and also set
`frames_mirrored[1]=True` for each chip, where 1 is the chip frame index of `1b1` in our case.

For fabrication, usually the photomasks will have to be mirrored for the `1b1` face, such that they are again normal
when looking at the wafer from the bottom. In this script, the mirroring is done for all `1b1` mask exports, using the
`^` prefix in `mask_export_layers`. You can verify this by opening `DemoMF_v1-1b1-1b1_base_metal_gap.oas` for example,
here the texts are normally readable again.

This example also shows adding multiple sizes of chips to the same mask layout, and using rectangular vs square chips.
"""

from kqcircuits.chips.chip import Chip
from kqcircuits.chips.sample_holder_test import SampleHolderTest
from kqcircuits.defaults import default_marker_type
from kqcircuits.masks.mask_set import MaskSet
from kqcircuits.pya_resolver import pya

mask_set = MaskSet(name="DemoMF", version=1, with_grid=False)

# Create a multi-face mask layout with regular chip maps (default size 10x10mm)
wafer_1 = mask_set.add_multi_face_mask_layout(
    chips_map=[["CH1"] * 15] * 7,
    face_ids=["1t1", "1b1"],
    extra_face_params={
        "1t1": {
            "layers_to_mask": {"base_metal_gap": "1", "through_silicon_via": "2"},
            "mask_export_layers": ["base_metal_gap", "through_silicon_via"],
        },
        "1b1": {
            "mirror_labels": True,  # Mask label and chip copy labels are mirrored on the bottom side of the wafer
            "layers_to_mask": {"base_metal_gap": "1", "through_silicon_via": "2"},
            "mask_export_layers": ["^base_metal_gap", "^through_silicon_via"],  # Mirror individual output files
        },
    },
)

# Add 20x10mm chips on part of the chip
wafer_1.add_chips_map(
    [
        ["ST1"] * 6,
    ]
    * 7,
    align_to=(-65000, 5000),  # Top-left corner of the chip map
    chip_size=(20000, 10000),  # (width, height) of the ST1 chip
)

# Chip parameters for an empty multi-face chip that uses `1t1` and `1b1`
multi_face_parameters = {
    "face_ids": ["1t1", "2b1", "1b1", "2t1"],
    "frames_enabled": [0, 2],
    "frames_marker_dist": [1500, 1500],
    "frames_mirrored": [False, True],
    "frames_dice_width": [200, 200],
    "face_boxes": [None] * 4,  # Same size on all faces
    "with_gnd_tsvs": True,
    "marker_types": [default_marker_type] * 8,
}

# Chip parameters for a rectangular 20x10 mm chip.
# Note: only some chips in the KQC library support dynamic resizing, typically one would create a custom chip with
#       the size and design needed.
rectangular_parametes = {
    **multi_face_parameters,
    "box": pya.DBox(0, 0, 20000, 10000),
}

mask_set.add_chip([(Chip, "CH1", multi_face_parameters), (SampleHolderTest, "ST1", rectangular_parametes)])

mask_set.build()
mask_set.export()
