# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.airbridge import Airbridge
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

