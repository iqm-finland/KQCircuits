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
from kqcircuits.elements.airbridges import airbridge_type_choices
from kqcircuits.elements.element import get_refpoints
from kqcircuits.pya_resolver import pya

from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.airbridges.airbridge_rectangular import AirbridgeRectangular
from kqcircuits.defaults import default_layers


def test_for_errors(capfd):
    """Test if exceptions happen during creation of the element.

    When an element is created using create(), it calls the element's produce_impl(). Exceptions
    happening in produce_impl() are caught by KLayout and output to stderr. Thus we can't detect the exceptions
    directly, but we can check stderr for errors. This assumes that there are no unrelated errors output to stderr
    by klayout.
    """
    layout = pya.Layout()
    Airbridge.create(layout)
    out, err = capfd.readouterr()
    assert err == "", err


def test_default_type():
    layout = pya.Layout()
    cell = Airbridge.create(layout)
    assert cell.name == Airbridge.default_type


def test_rect_type():
    layout = pya.Layout()
    cell = Airbridge.create(layout, airbridge_type="Airbridge Rectangular")
    assert type(cell.pcell_declaration()) == AirbridgeRectangular


def test_wrong_type_override():
    layout = pya.Layout()
    cell = Airbridge.create(layout, airbridge_type="Airbridge NoSuchThing")
    assert cell.name == Airbridge.default_type


def test_bridge_length_rectangular():
    pad_1, pad_2 = _get_pad_boxes("Airbridge Rectangular", "1t1_airbridge_pads", bridge_length=101)
    assert min(abs(pad_1.top - pad_2.bottom), abs(pad_2.top - pad_1.bottom)) == 101


def test_pad_dimensions_rectangular():
    pad_1, pad_2 = _get_pad_boxes(
        "Airbridge Rectangular", "1t1_airbridge_pads", bridge_width=19, pad_extra=1, pad_length=33
    )
    assert pad_1.width() == 21
    assert pad_2.width() == 21
    assert pad_1.height() == 33
    assert pad_2.height() == 33


def _get_pad_boxes(airbridge_type, pad_layer, **params):
    layout = pya.Layout()
    cell = Airbridge.create(layout, airbridge_type=airbridge_type, **params)
    shapes_iter = cell.begin_shapes_rec(layout.layer(default_layers[pad_layer]))
    pad_1 = shapes_iter.shape().dbbox()
    shapes_iter.next()
    pad_2 = shapes_iter.shape().dbbox()
    return pad_1, pad_2


def test_reference_points():
    for ab_type in airbridge_type_choices:
        layout = pya.Layout()
        cell = Airbridge.create(layout, airbridge_type=ab_type[1])
        refp = get_refpoints(layout.layer(default_layers["refpoints"]), cell)
        assert refp["port_a"].x == 0
        assert refp["port_b"].x == 0
        assert refp["port_a"].y > 0
        assert refp["port_a"].y == -refp["port_b"].y
