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

from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter, t_cross_parameters
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper
from kqcircuits.pya_resolver import pya
from kqcircuits.util.node import Node
from kqcircuits.util.gui_helper import node_from_text, node_to_text


def _test_nodes():
    return [
        Node(pya.DPoint(0, 0)),
        Node(pya.DPoint(800, 0), FingerCapacitorSquare),
        Node(pya.DPoint(400, 0), FlipChipConnectorRf, face_id="2b1"),
        Node(pya.DPoint(2700, -500), FlipChipConnectorRf, face_id="2b1", output_rotation=90),
        Node(pya.DPoint(400, 0), face_id="2b1"),
        Node(pya.DPoint(400, 0), Airbridge),
        Node(
            pya.DPoint(200, 0),
            AirbridgeConnection,
            airbridge_type="Airbridge Rectangular",
            with_side_airbridges=False,
            b=4,
            a=5,
        ),
        Node(pya.DPoint(1060, 100), ab_across=True),
        Node(pya.DPoint(1100, 100), WaveguideCoplanarTaper, a=10, b=5),
        Node(pya.DPoint(1400, 0), n_bridges=3),
        Node(pya.DPoint(2150, 0), WaveguideCoplanarSplitter, align=("port_a", "port_c")),
    ]


@pytest.mark.parametrize("node", _test_nodes())
def test_nodes_from_text_is_inverse_of_nodes_to_text(node):
    """
    Test that nodes_from_text is the inverse of node_to_text
    """
    original_node_str = str(node)
    converted_node = node_from_text(*node_to_text(node))
    assert original_node_str == str(converted_node)


# Expected behavior
def test_node_from_text_valid_values():
    """
    Test some valid arguments, including whitespace here and there
    """
    node = node_from_text("1", "2.2", "Airbridge", "my_instance", "90.0", "\t1000", "300 ", "port_in, port_out", "")

    assert node.position.x == 1
    assert node.position.y == 2.2
    assert node.element is Airbridge
    assert node.inst_name == "my_instance"
    assert node.angle == 90
    assert node.length_before == 1000
    assert node.length_increment == 300
    assert node.align == ("port_in", "port_out")


def test_node_from_text_with_parameters():
    """
    Test key=value parameters
    """
    params = "key1='value1'\nkey2=3.0\n\tkey3 = ['list', 'of', 'strings']\nkey_4=[1,2,3]\nkey_5=(1,12)"
    node = node_from_text("1", "2.2", "Airbridge", "", "", "", "", "", params)

    assert node.params == {
        "key1": "value1",
        "key2": 3.0,
        "key3": ["list", "of", "strings"],
        "key_4": [1, 2, 3],
        "key_5": pya.DPoint(1, 12),
    }


# Edge cases
def test_nodes_from_text_raises_on_x():
    with pytest.raises(ValueError):
        node_from_text("not a float", "0", "", "", "", "", "", "", "")


def test_nodes_from_text_raises_on_y():
    with pytest.raises(ValueError):
        node_from_text("0", "not a float", "", "", "", "", "", "", "")


def test_nodes_from_text_invalid_element():
    node = node_from_text("0", "0", "ThisElementDoesNotExist", "", "", "", "", "", "")
    assert node.element is None


def test_nodes_from_text_raises_on_invalid_tuple_parameter():
    with pytest.raises(ValueError):
        node_from_text("0", "0", "Airbridge", "", "", "", "", "", "key=(1,'two')")


def test_nodes_from_text_raises_on_too_short_tuple_parameter():
    with pytest.raises(ValueError):
        node_from_text("0", "0", "Airbridge", "", "", "", "", "", "key=(1,)")
