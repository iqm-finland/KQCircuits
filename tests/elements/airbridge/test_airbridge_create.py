# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

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
