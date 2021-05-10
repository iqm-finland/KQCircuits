# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.waveguide_composite import Node, WaveguideComposite
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.elements.airbridges.airbridge_rectangular import AirbridgeRectangular
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.elements.f2f_connectors.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf

# use all features and parameters and some combinations of these
nodes1 = [
    Node(pya.DPoint(0, 0)),
    Node(pya.DPoint(200, 0), AirbridgeConnection, airbridge_type="Airbridge Rectangular", with_side_airbridges=False, b=4, a=5),
    Node(pya.DPoint(400, 0), FlipChipConnectorRf, face_id="t"),
    Node(pya.DPoint(600, 0), AirbridgeConnection, with_side_airbridges=False),
    Node(pya.DPoint(800, 0), FingerCapacitorSquare),
    Node(pya.DPoint(1000, 100)),
    Node(pya.DPoint(1050, 100), ab_across=True),
    Node(pya.DPoint(1100, 100), WaveguideCoplanarTaper, a=10, b=5),
    Node(pya.DPoint(1200, 100)),
    Node(pya.DPoint(1300, 0), n_bridges=3),
    Node(pya.DPoint(1600, 0), FlipChipConnectorRf, face_id="b", connector_type="Single"),
    Node(pya.DPoint(1800, 0), AirbridgeConnection, with_side_airbridges=True),
    Node(pya.DPoint(2000, 0)),
]

# *exactly* like above but use simplified notation
nodes2 = [
    Node((0, 0)),
    Node((200, 0), AirbridgeRectangular, a=5, b=4),
    Node((400, 0), face_id="t"),
    Node((600, 0), Airbridge),
    Node((800, 0), FingerCapacitorSquare),
    Node((1000, 100)),
    Node((1050, 100), ab_across=True),
    Node((1100, 100), a=10, b=5),
    Node((1200, 100)),
    Node((1300, 0), n_bridges=3),
    Node((1600, 0), face_id="b", connector_type="Single"),
    Node((1800, 0), AirbridgeConnection),
    Node((2000, 0)),
]

def test_crash_and_node_formats(capfd):
    l1 = _make_wg(capfd, nodes1)
    l2 = _make_wg(capfd, nodes2)
    assert l1 == l2

def _make_wg(capfd, nodes):
    layout = pya.Layout()
    wg = WaveguideComposite.create(layout, nodes=nodes)
    out, err = capfd.readouterr()
    assert err == "", err
    return wg.length()

def test_length():
    layout = pya.Layout()
    wg = WaveguideComposite.create(layout, nodes=nodes1)
    l1 = wg.length()

    # length of fc-bump and capacitors don't count
    for node in nodes1:    # make them empty Nodes
        if node.element is not AirbridgeConnection:
            node.element = None
            node.params = {}

    wg = WaveguideComposite.create(layout, nodes=nodes1)
    l2 = wg.length()
    assert l2 > l1

    # Without "special" nodes it shoould be identical to a plain WaveguideCoplanar
    points = []
    for node in nodes1:    # get the points
        points.append(node.position)
    wg = WaveguideCoplanar.create(layout, path=pya.DPath(points, 1))
    l3 = wg.length()
    assert abs(l2 - l3)/l2 < 1e-12

relative_length_tolerance = 1e-4

def test_length_one_series_airbridge():
    layout = pya.Layout()
    length = 400
    nodes = [
        Node((250 + length, -500)),
        Node((250, -500), Airbridge, a=20, b=30)
    ]
    wg = WaveguideComposite.create(layout, nodes=nodes)

    true_length = wg.length()
    relative_length_error = abs(true_length - length) / length

    assert relative_length_error < relative_length_tolerance
