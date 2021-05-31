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
