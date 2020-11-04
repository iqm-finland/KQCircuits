# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya

from kqcircuits.elements.airbridge import Airbridge
from kqcircuits.test_structures.airbridge_dc import AirbridgeDC


def test_bridge_number_few():
    n_bridges = 7
    assert _get_number_of_bridges(n_bridges) == n_bridges


def test_bridge_number_many():
    n_bridges = 124
    assert _get_number_of_bridges(n_bridges) == n_bridges


def _get_number_of_bridges(n_bridges):
    layout = pya.Layout()
    cell = AirbridgeDC.create(layout, n_ab=n_bridges)
    actual_n_bridges = 0
    for inst in cell.each_inst():
        if type(inst.cell.pcell_declaration()) == Airbridge:
            actual_n_bridges += 1
    return actual_n_bridges
