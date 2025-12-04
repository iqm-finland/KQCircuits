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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).
import pytest

from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter, t_cross_parameters
from kqcircuits.pya_resolver import pya
from kqcircuits.elements.waveguide_composite import WaveguideComposite
from kqcircuits.util.node import Node
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.elements.airbridges.airbridge_rectangular import AirbridgeRectangular
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf


@pytest.fixture
def nodes1():
    """Node list that uses all features and parameters and some combinations of these"""
    return [
        Node(pya.DPoint(0, 0)),
        Node(
            pya.DPoint(200, 0),
            AirbridgeConnection,
            airbridge_type="Airbridge Rectangular",
            with_side_airbridges=False,
            b=4,
            a=5,
        ),
        Node(pya.DPoint(400, 0), FlipChipConnectorRf, face_id="2b1"),
        Node(pya.DPoint(600, 0), AirbridgeConnection, with_side_airbridges=False),
        Node(pya.DPoint(800, 0), FingerCapacitorSquare),
        Node(pya.DPoint(1000, 100)),
        Node(pya.DPoint(1060, 100), ab_across=True),
        Node(pya.DPoint(1100, 100), WaveguideCoplanarTaper, a=10, b=5),
        Node(pya.DPoint(1300, 100)),
        Node(pya.DPoint(1400, 0), n_bridges=3),
        Node(pya.DPoint(1700, 0), FlipChipConnectorRf, face_id="1t1", connector_type="Single"),
        Node(pya.DPoint(1900, 0), AirbridgeConnection, with_side_airbridges=True),
        Node(pya.DPoint(2100, 0)),
        Node(
            pya.DPoint(2150, 0),
            WaveguideCoplanarSplitter,
            **t_cross_parameters(a=10, b=5),
            align=("port_left", "port_right"),
        ),
        Node(pya.DPoint(2350, 50)),
        Node(
            pya.DPoint(2400, 50),
            WaveguideCoplanarSplitter,
            **t_cross_parameters(a=10, b=5),
            align=("port_right", "port_left"),
            inst_name="second_tee",
        ),
        Node(pya.DPoint(2500, 50)),
        Node(
            pya.DPoint(2600, 50),
            WaveguideCoplanarSplitter,
            **t_cross_parameters(a=10, b=5),
            align=("port_bottom", "port_right"),
        ),
        Node(pya.DPoint(2700, -200)),
        Node(pya.DPoint(2700, -500), FlipChipConnectorRf, face_id="2b1", output_rotation=90),
        Node(pya.DPoint(2500, -400)),
    ]


@pytest.fixture
def nodes2():
    """Node list specifying *exactly* the same waveguide as nodes1, but but using simplified notation"""
    return [
        Node((0, 0)),
        Node((200, 0), AirbridgeRectangular, a=5, b=4),
        Node((400, 0), face_id="2b1"),
        Node((600, 0), Airbridge),
        Node((800, 0), FingerCapacitorSquare),
        Node((1000, 100)),
        Node((1060, 100), ab_across=True),
        Node((1100, 100), a=10, b=5),
        Node((1300, 100)),
        Node((1400, 0), n_bridges=3),
        Node((1700, 0), face_id="1t1", connector_type="Single"),
        Node((1900, 0), AirbridgeConnection),
        Node((2100, 0)),
        Node(
            pya.DPoint(2150, 0),
            WaveguideCoplanarSplitter,
            **t_cross_parameters(a=10, b=5),
            align=("port_left", "port_right"),
        ),
        Node(pya.DPoint(2350, 50)),
        Node(
            pya.DPoint(2400, 50),
            WaveguideCoplanarSplitter,
            **t_cross_parameters(a=10, b=5),
            align=("port_right", "port_left"),
            inst_name="second_tee",
        ),
        Node(pya.DPoint(2500, 50)),
        Node(
            pya.DPoint(2600, 50),
            WaveguideCoplanarSplitter,
            **t_cross_parameters(a=10, b=5),
            align=("port_bottom", "port_right"),
        ),
        Node(pya.DPoint(2700, -200)),
        Node(pya.DPoint(2700, -500), face_id="2b1", output_rotation=90),
        Node(pya.DPoint(2500, -400)),
    ]


def test_too_few_nodes(capfd):
    layout = pya.Layout()
    WaveguideComposite.create(layout, nodes=[Node((0, 0))])
    _, err = capfd.readouterr()
    assert err != ""


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
    for node in nodes1:  # make them empty Nodes
        if node.element is not AirbridgeConnection:
            node.element = None
            node.params = {}

    wg = WaveguideComposite.create(layout, nodes=nodes1)
    l2 = wg.length()
    assert l2 > l1

    # Without "special" nodes it should be identical to a plain WaveguideCoplanar
    points = []
    for node in nodes1:  # get the points
        points.append(node.position)
    wg = WaveguideCoplanar.create(layout, path=pya.DPath(points, 1))
    l3 = wg.length()
    assert abs(l2 - l3) / l2 < 1e-12


relative_length_tolerance = 1e-3


def test_length_one_series_airbridge():
    layout = pya.Layout()
    length = 400
    nodes = [Node((250 + length, -500)), Node((250, -500), Airbridge, a=20, b=30)]
    wg = WaveguideComposite.create(layout, nodes=nodes)

    true_length = wg.length()
    relative_length_error = abs(true_length - length) / length

    assert relative_length_error < relative_length_tolerance


def test_length_before_straight():
    layout = pya.Layout()
    length = 2500
    nodes = [Node((0, 0)), Node((0, 1000), length_before=length)]
    wg = WaveguideComposite.create(layout, nodes=nodes)

    true_length = wg.length()
    relative_length_error = abs(true_length - length) / length

    assert relative_length_error < relative_length_tolerance


def test_length_before_diagonal():
    layout = pya.Layout()
    straight_len = 200
    length = 3500  # long enough to have 90 degree turns
    nodes = [
        Node((0, 0)),
        Node((straight_len, 0), angle=0),
        Node((1500, 1000), length_before=length, angle=0),
        Node((1500 + straight_len, 1000)),
    ]
    wg = WaveguideComposite.create(layout, nodes=nodes)

    total_length = wg.length()
    true_length = total_length - 2 * straight_len
    relative_length_error = abs(true_length - length) / length

    assert relative_length_error < relative_length_tolerance


def test_length_before_diagonal_non_90_deg_turns():
    layout = pya.Layout()
    straight_len = 200
    length = 2000
    nodes = [
        Node((0, 0)),
        Node((straight_len, 0), angle=0),
        Node((1500, 1300), length_before=length, angle=0),
        Node((1500 + straight_len, 1300)),
    ]
    wg = WaveguideComposite.create(layout, nodes=nodes)

    total_length = wg.length()
    true_length = total_length - 2 * straight_len
    relative_length_error = abs(true_length - length) / length

    assert relative_length_error < relative_length_tolerance


def test_tight_routing():
    layout = pya.Layout()
    nodes = [
        Node((300, -300), angle=-90),  # start with angle
        Node((2000, -602), angle=180),  # 90 degree bend + straight + 180 degree bend
        Node((0, -401), angle=0),  # straight + 180 degree bend
        Node((0, 0), angle=0),  # two 180 degree bends without straight in between
        Node((200, 200), angle=0),  # two 90 degree bends without straight in between
        Node((1000, 200), angle=0),  # only straight
        Node((5000, 100), angle=-60),  # very small bend + long straight + 30 degree bend
        Node((200, 0)),  # 60 degree bend + long straight + end without angle
    ]
    wg = WaveguideComposite.create(layout, nodes=nodes, tight_routing=True)

    true_length = wg.length()
    ref_length = 15069.481
    relative_length_error = abs(true_length - ref_length) / ref_length

    assert relative_length_error < relative_length_tolerance
