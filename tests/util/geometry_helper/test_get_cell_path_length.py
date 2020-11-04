# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import math

from kqcircuits.defaults import default_layers
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import get_cell_path_length

relative_length_tolerance = 1e-4


def test_get_length_simple_path():
    layout = pya.Layout()
    path_layer = layout.layer(default_layers["annotations"])
    cell = layout.create_cell("test")
    shape = pya.DPath([
        pya.DPoint(0, 0),
        pya.DPoint(300, 0),
        pya.DPoint(300, 100),
    ], 0)
    cell.shapes(path_layer).insert(shape)
    length = 300 + 100
    assert abs(get_cell_path_length(cell, path_layer) - length)/length < relative_length_tolerance


def test_get_length_simple_waveguide():
    layout = pya.Layout()
    path_layer = layout.layer(default_layers["annotations"])
    r = 50
    cell = WaveguideCoplanar.create(layout, path=pya.DPath([
        pya.DPoint(0, 0),
        pya.DPoint(0, 250),
        pya.DPoint(200, 250),
    ], 0), r=r)
    length = 250 + 200 - 2*r + math.pi*r/2
    assert abs(get_cell_path_length(cell, path_layer) - length)/length < relative_length_tolerance
