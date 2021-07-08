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
import pytest

from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter
from kqcircuits.elements.waveguide_coplanar_tcross import WaveguideCoplanarTCross
from kqcircuits.pya_resolver import pya
from kqcircuits.elements.waveguide_composite import Node, WaveguideComposite
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.elements.airbridges.airbridge_rectangular import AirbridgeRectangular
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.elements.f2f_connectors.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf


@pytest.fixture
def nodes1():
    """ Node list that uses all features and parameters and some combinations of these """
    return [
        Node(pya.DPoint(0, 0)),
        Node(pya.DPoint(200, 0), AirbridgeConnection, airbridge_type="Airbridge Rectangular",
             with_side_airbridges=False, b=4, a=5),
        Node(pya.DPoint(400, 0), FlipChipConnectorRf, face_id="t"),
        Node(pya.DPoint(600, 0), AirbridgeConnection, with_side_airbridges=False),
        Node(pya.DPoint(800, 0), FingerCapacitorSquare),
        Node(pya.DPoint(1000, 100)),
        Node(pya.DPoint(1050, 100), ab_across=True),
        Node(pya.DPoint(1100, 100), WaveguideCoplanarTaper, a=10, b=5),
        Node(pya.DPoint(1300, 100)),
        Node(pya.DPoint(1400, 0), n_bridges=3),
        Node(pya.DPoint(1700, 0), FlipChipConnectorRf, face_id="b", connector_type="Single"),
        Node(pya.DPoint(1900, 0), AirbridgeConnection, with_side_airbridges=True),
        Node(pya.DPoint(2100, 0)),
        Node(pya.DPoint(2150,0), WaveguideCoplanarTCross, align=("port_left", "port_right")),
        Node(pya.DPoint(2350, 50)),
        Node(pya.DPoint(2400, 50), WaveguideCoplanarTCross, align=("port_right", "port_left"), inst_name="second_tee"),
        Node(pya.DPoint(2500, 50)),
        Node(pya.DPoint(2600, 50), WaveguideCoplanarTCross, align=("port_bottom", "port_right")),
        Node(pya.DPoint(2700, -200)),
        Node(pya.DPoint(2700, -300), FlipChipConnectorRf, face_id="t", output_rotation=90),
        Node(pya.DPoint(2500, -200)),
    ]


@pytest.fixture
def nodes2():
    """ Node list specifying *exactly* the same waveguide as nodes1, but but using simplified notation """
    return [
        Node((0, 0)),
        Node((200, 0), AirbridgeRectangular, a=5, b=4),
        Node((400, 0), face_id="t"),
        Node((600, 0), Airbridge),
        Node((800, 0), FingerCapacitorSquare),
        Node((1000, 100)),
        Node((1050, 100), ab_across=True),
        Node((1100, 100), a=10, b=5),
        Node((1300, 100)),
        Node((1400, 0), n_bridges=3),
        Node((1700, 0), face_id="b", connector_type="Single"),
        Node((1900, 0), AirbridgeConnection),
        Node((2100, 0)),
        Node(pya.DPoint(2150, 0), WaveguideCoplanarTCross, align=("port_left", "port_right")),
        Node(pya.DPoint(2350, 50)),
        Node(pya.DPoint(2400, 50), WaveguideCoplanarTCross, align=("port_right", "port_left"), inst_name="second_tee"),
        Node(pya.DPoint(2500, 50)),
        Node(pya.DPoint(2600, 50), WaveguideCoplanarTCross, align=("port_bottom", "port_right")),
        Node(pya.DPoint(2700, -200)),
        Node(pya.DPoint(2700, -300), face_id="t", output_rotation=90),
        Node(pya.DPoint(2500, -200)),
    ]


@pytest.fixture
def nodes_with_expected_segment_lengths():
    """
    Node list for which the segment_lengths() is easy to predict

    Returns: Tuple (nodes, expected_segment_lengths)
    """

    nodes = [
        # Start at x position 0
        Node((0, 0)),
        Node((100, 0)),  # Regular nodes do not end segment
        Node((200, 0)),
        Node((300, 0), WaveguideCoplanarTaper, a=6, b=3, taper_length=50),  # Ends segment 0 at position 300

        # Position after taper is 350
        Node((400, 0), ab_across=True),  # Airbridge across does not end segment
        Node((600, 0), WaveguideCoplanarSplitter, angles=[0, 180, 60], lengths=[50, 100, 75]),  # Ends segment 1 at 550

        # Position after splitter is 700
        Node((1000, 0), FingerCapacitorSquare, fixed_length=160),  # Ends segment 2 at 920

        # Position after capacitor is 1080
        Node((1200, 0)),  # Ends segment 3 at 1200
    ]

    expected_segment_lengths = [300 - 0, 550 - 350, 920 - 700, 1200 - 1080]

    return nodes, expected_segment_lengths


def test_crash_and_node_formats(capfd, nodes1, nodes2):
    l1 = _make_wg(capfd, nodes1)
    l2 = _make_wg(capfd, nodes2)
    assert l1 == l2


def _make_wg(capfd, nodes):
    layout = pya.Layout()
    wg = WaveguideComposite.create(layout, nodes=nodes)
    _, err = capfd.readouterr()
    assert err == "", err
    return wg.length()


def test_length(nodes1):
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

    # Without "special" nodes it should be identical to a plain WaveguideCoplanar
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


def test_segment_lengths(nodes_with_expected_segment_lengths):
    layout = pya.Layout()
    nodes, expected_segment_lengths = nodes_with_expected_segment_lengths

    wg = WaveguideComposite.create(layout, nodes=nodes)

    tolerance = 1e-4
    assert (all(abs(real / expected - 1) < tolerance for (real, expected) in
                zip(wg.segment_lengths(), expected_segment_lengths)))
