# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.defaults import default_layers
from kqcircuits.elements.waveguide_coplanar_bridged import WaveguideCoplanarBridged, Node, NodeType
from kqcircuits.pya_resolver import pya

relative_length_tolerance = 1e-4


def test_length_one_series_airbridge():
    layout = pya.Layout()
    length = 400
    nodes = [
        Node(NodeType.WAVEGUIDE, pya.DPoint(250 + length, -500)),
        Node(NodeType.AB_SERIES_SINGLE, pya.DPoint(250, -500), a=20, b=30)
    ]
    wg = WaveguideCoplanarBridged.create(layout, nodes=nodes)

    true_length = WaveguideCoplanarBridged.get_length(wg, layout.layer(default_layers["annotations"]))
    relative_length_error = abs(true_length - length) / length

    assert relative_length_error < relative_length_tolerance
