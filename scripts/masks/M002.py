# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy's prior
# written permission.

import glob
import os.path

from kqcircuits.chips.shaping import Shaping
from kqcircuits.chips.quality_factor import QualityFactor
from kqcircuits.defaults import TMP_PATH
from kqcircuits.klayout_view import KLayoutView
from kqcircuits.masks.mask_set import MaskSet

"""M002 mask.

Photon shaping and spiral resonators.

"""

view = KLayoutView(current=True, initialize=True)
layout = KLayoutView.get_active_layout()

m002 = MaskSet(layout, name="M112", version=2, with_grid=False)

# 20*R4,
# 15*R5,
# 15*R6,
# 20*R7,
# 20*R8.
# 4*QDG,
# 20*S1,
# 20*ST.

# pixel_list = 10*["R4","R5","R6","R7","R8","S1","ST",
# "R4","R5","R6","R7","R8","S1","ST",
# "R4","R5","R6","R7","R8","S1","ST",
# "R4","R7","R8","S1","ST","QDG"]

m002.add_mask_layout([
    ["--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--"],
    ["--", "--", "--", "--", "--", "R4", "R4", "R4", "R4", "R4", "--", "--", "--", "--", "--"],
    ["--", "--", "--", "R7", "R7", "R4", "R4", "R4", "R4", "R4", "R8", "R8", "--", "--", "--"],
    ["--", "--", "R5", "R7", "R7", "R4", "R4", "R4", "R4", "R4", "R8", "R8", "R6", "--", "--"],
    ["--", "--", "R5", "R7", "R7", "R4", "R4", "R4", "R4", "R4", "R8", "R8", "R6", "--", "--"],
    ["--", "R5", "R5", "R7", "R7", "S1", "S1", "ST", "ST", "QD", "R8", "R8", "R6", "R6", "--"],
    ["--", "R5", "R5", "R7", "R7", "S1", "S1", "ST", "ST", "QD", "R8", "R8", "R6", "R6", "--"],
    ["--", "R5", "R5", "R7", "R7", "S1", "S1", "ST", "ST", "QD", "R7", "R8", "R6", "R6", "--"],
    ["--", "R5", "R5", "R7", "R7", "S1", "S1", "ST", "ST", "QD", "R8", "R8", "R6", "R6", "--"],
    ["--", "R5", "R5", "R7", "R7", "S1", "S1", "S1", "S1", "S1", "R8", "R8", "R6", "R6", "--"],
    ["--", "--", "R5", "R7", "R7", "ST", "ST", "ST", "S1", "S1", "R8", "R8", "R6", "--", "--"],
    ["--", "--", "R5", "R7", "R7", "ST", "ST", "ST", "S1", "S1", "R8", "R8", "R6", "--", "--"],
    ["--", "--", "--", "R7", "R7", "ST", "ST", "ST", "S1", "QD", "R8", "R8", "--", "--", "--"],
    ["--", "--", "--", "--", "--", "ST", "ST", "ST", "S1", "QD", "--", "--", "--", "--", "--"],
    ["--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--", "--"],
])
# "R4","R7","R8","S1","ST","QDG"]

# For quality factor test as on M001
parameters_qd = {
    "res_lengths": [4649.6, 4743.3, 4869.9, 4962.9, 5050.7, 5138.7, 5139., 5257., 5397.4, 5516.8, 5626.6, 5736.2,
                    5742.9, 5888.7, 6058.3, 6202.5, 6350., 6489.4],
    "type_coupler": ["square", "square", "square", "plate", "plate", "plate", "square", "square", "square", "plate",
                     "plate", "plate", "square", "square", "square", "square", "plate", "plate"],
    "l_fingers": [19.9, 54.6, 6.7, 9.7, 22.8, 30.5, 26.1, 14.2, 18.2, 10.9, 19.8, 26.4, 34.2, 19.9, 25.3, 8., 15.8,
                  22.2],
    "n_fingers": [4, 2, 2, 4, 4, 4, 4, 4, 2, 4, 4, 4, 4, 4, 2, 2, 4, 4],
    "res_beg": ["galvanic"]*18
}

# Load new cells from the files
imported = False
path_pixels_input = "path_pixels_input"
if not 'imported' in globals() or not imported:
    for file_name in glob.glob(os.path.join(path_pixels_input, "*.gds")):
        print("Loading:", file_name)
        m002.layout.read(file_name)
    imported = True

# Register the cells used on the mask
m002.chips_map_legend = {
    **m002.variant_definition(Shaping, "S1", tunable=False),
    **m002.variant_definition(Shaping, "ST", tunable=True),
    **m002.variant_definition(QualityFactor, "QD", **parameters_qd, n_ab=18*[0], res_term=18*["galvanic"]),
    "R4": m002.layout.create_cell("R04"),
    "R5": m002.layout.create_cell("R05"),
    "R6": m002.layout.create_cell("R06"),
    "R7": m002.layout.create_cell("R07"),
    "R8": m002.layout.create_cell("R08")
}

m002.build()
m002.export(TMP_PATH, view)