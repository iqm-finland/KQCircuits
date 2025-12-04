# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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
import numpy as np
import pytest

from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.elements.waveguide_coplanar_taper import WaveguideCoplanarTaper
from kqcircuits.pya_resolver import pya
from kqcircuits.elements.waveguide_composite import WaveguideComposite
from kqcircuits.util.node import Node
from kqcircuits.elements.waveguide_coplanar_splitter import WaveguideCoplanarSplitter
from kqcircuits.util.merge import convert_child_instances_to_static


def test_segment_lengths_of_straight_segments():
    layout = pya.Layout()
    wg = WaveguideComposite.create(
        layout,
        nodes=[
            Node((0, 0)),
            Node((1000, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0]),
            Node((2010, 0)),
        ],
    )

    assert np.allclose(wg.segment_lengths(), [0, 1000, 1010], atol=0.01)
    assert np.isclose(wg.length(), sum(wg.segment_lengths()), atol=0.01)


def test_segment_lengths_with_meander():
    layout = pya.Layout()
    wg = WaveguideComposite.create(
        layout,
        nodes=[
            Node((0, 0)),
            Node((1000, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0], length_before=2000),
            Node((2010, 0)),
        ],
    )

    assert np.allclose(wg.segment_lengths(), [0, 2000, 1010], atol=1.5)
    assert np.isclose(wg.length(), sum(wg.segment_lengths()), atol=0.01)


def test_segment_lengths_with_meander_after_splitter():
    layout = pya.Layout()
    wg = WaveguideComposite.create(
        layout,
        nodes=[
            Node((0, 0)),
            Node((1000, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0]),
            Node((2010, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0], length_before=2000),
            Node((3030, 0)),
        ],
    )

    assert np.allclose(wg.segment_lengths(), [0, 1000, 2000, 1020], atol=1.5)
    assert np.isclose(wg.length(), sum(wg.segment_lengths()), atol=0.01)


def test_segment_lengths_with_normal_segment_before_meander():
    layout = pya.Layout()
    wg = WaveguideComposite.create(
        layout,
        nodes=[
            Node((0, 0)),
            Node((1000, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0]),
            Node((2010, 0)),  # Normal segment gets absorbed into the next node
            Node((3030, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0], length_before=2000),
            Node((4060, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0]),
            Node((5100, 0)),
        ],
    )

    assert np.allclose(wg.segment_lengths(), [0, 1000, 0, 1010 + 2000, 1030, 1040], atol=1.5)
    assert np.isclose(wg.length(), sum(wg.segment_lengths()), atol=0.01)


def test_segment_lengths_with_multiple_meanders():
    layout = pya.Layout()
    wg = WaveguideComposite.create(
        layout,
        nodes=[
            Node((0, 0)),
            Node((1000, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0]),
            Node((2010, 0)),
            Node((3030, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0], length_before=2000),
            Node((4060, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0]),
            Node((5100, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0], length_before=3000),
            Node((6150, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0]),
        ],
    )

    assert np.allclose(wg.segment_lengths(), [0, 1000, 0, 1010 + 2000, 1030, 3000, 1050], atol=1.5)
    assert np.isclose(wg.length(), sum(wg.segment_lengths()), atol=0.01)


def test_segment_lengths_with_multiple_consecutive_meanders():
    layout = pya.Layout()
    wg = WaveguideComposite.create(
        layout,
        nodes=[
            Node((0, 0)),
            Node((1000, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0]),
            Node((2010, 0)),
            Node((3030, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0], length_before=2000),
            Node((4060, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0], length_before=3000),
            Node((5100, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0]),
            Node((6150, 0)),
        ],
    )

    assert np.allclose(wg.segment_lengths(), [0, 1000, 0, 1010 + 2000, 3000, 1040, 1050], atol=1.5)
    assert np.isclose(wg.length(), sum(wg.segment_lengths()), atol=0.01)


def test_segment_lengths_with_taper():
    layout = pya.Layout()
    wg = WaveguideComposite.create(
        layout,
        nodes=[
            Node((0, 0)),
            Node((1000, 0), a=20, taper_length=100),  # Taper length is counted in the node it is defined ...
            Node((2010, 0)),  # And this segment will be shorter since the taper _starts_ at the previous node.
        ],
    )

    assert np.allclose(wg.segment_lengths(), [0, 1000 + 100, 1010 - 100], atol=1.5)
    assert np.isclose(wg.length(), sum(wg.segment_lengths()), atol=0.01)


def test_segment_lengths_with_multiple_tapers():
    layout = pya.Layout()
    wg = WaveguideComposite.create(
        layout,
        nodes=[
            Node((0, 0)),
            Node((1000, 0), a=20, taper_length=100),
            Node((2010, 0)),
            Node((3030, 0), a=10, taper_length=200),
            Node((4060, 0)),
        ],
    )

    assert np.allclose(wg.segment_lengths(), [0, 1000 + 100, 0, 1010 - 100 + 1020 + 200, 1030 - 200], atol=1.5)
    assert np.isclose(wg.length(), sum(wg.segment_lengths()), atol=0.01)


def test_segment_lengths_static_cell():
    layout = pya.Layout()
    wg = WaveguideComposite.create(
        layout,
        nodes=[
            Node((0, 0)),
            Node((1000, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0]),
            Node((2010, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0], length_before=2000),
            Node((3030, 0)),
        ],
    )
    pcell_segment_lengths = wg.segment_lengths()

    # Converts the WaveguideComposite cell to static, but leaves child cells as PCell
    static_wg = layout.cell(layout.convert_cell_to_static(wg.cell_index()))

    assert np.allclose(WaveguideComposite.get_segment_lengths(static_wg), [0, 1000, 2000, 1020], atol=1.5)
    assert np.allclose(WaveguideComposite.get_segment_lengths(static_wg), pcell_segment_lengths, atol=0.01)


def test_segment_lengths_static_cell_hierarchy():
    layout = pya.Layout()
    wg = WaveguideComposite.create(
        layout,
        nodes=[
            Node((0, 0)),
            Node((1000, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0]),
            Node((2010, 0), WaveguideCoplanarSplitter, lengths=[0, 0, 0], length_before=2000),
            Node((3030, 0)),
        ],
    )
    pcell_segment_lengths = wg.segment_lengths()

    # Converts the WaveguideComposite cell and all first-level child instances to static
    static_wg = layout.cell(layout.convert_cell_to_static(wg.cell_index()))
    convert_child_instances_to_static(layout, static_wg, only_elements=False, prune=False)

    assert np.allclose(WaveguideComposite.get_segment_lengths(static_wg), [0, 1000, 2000, 1020], atol=1.5)
    assert np.allclose(WaveguideComposite.get_segment_lengths(static_wg), pcell_segment_lengths, atol=0.01)


@pytest.fixture
def nodes_with_expected_segment_lengths():
    """Node list for which the segment_lengths() is easy to predict.

    Returns: Tuple (nodes, expected_segment_lengths)
    """

    nodes = [
        # Start at x position 0
        Node((0, 0)),
        Node((100, 0)),  # Regular nodes' length accumulates to the first "special" node
        Node((200, 0)),
        Node((300, 0), WaveguideCoplanarTaper, a=6, b=3, taper_length=50),  # Ends segment at x=300, but includes taper
        # Position after taper is 350
        Node((400, 0), ab_across=True),  # Airbridge across does not end segment
        Node((600, 0), WaveguideCoplanarSplitter, angles=[0, 180, 60], lengths=[50, 100, 75]),  # Ends segment 1 at 550
        # Position after splitter is 700
        Node((1000, 0), FingerCapacitorSquare, fixed_length=160),  # Ends segment 2 at 920
        # Position after capacitor is 1080
        Node((1200, 0)),  # Ends segment 3 at 1200
    ]

    expected_segment_lengths = [0, 0, 0, 350 - 0, 0, 550 - 350, 920 - 700, 1200 - 1080]

    return nodes, expected_segment_lengths


def test_segment_lengths(nodes_with_expected_segment_lengths):
    layout = pya.Layout()
    nodes, expected_segment_lengths = nodes_with_expected_segment_lengths

    wg = WaveguideComposite.create(layout, nodes=nodes)

    assert np.allclose(wg.segment_lengths(), expected_segment_lengths, rtol=1e-4, atol=1)
