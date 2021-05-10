# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

"""This module is used for importing the KLayout Python API (pya).

Without this module, the API would need to be imported using ``import pya`` for usage in KLayout Editor and using
``import klayout.db`` for usage with standalone klayout package. To make it simple to create a python module for both
use cases, this module automatically imports the correct module and exposes it as ``pya``.

Usage:
    from kqcircuits.pya_resolver import pya

"""

try:
    import pya
except ImportError:
    import klayout.db as pya

def is_standalone_session():
    try:
        app = pya.Application
    except AttributeError:
        standalone = True
    else:
        standalone = False

    return standalone
