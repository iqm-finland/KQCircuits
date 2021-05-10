# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare


def test_presence_and_absence_of_length():
    layout = pya.Layout()

    waveguide_cell = WaveguideCoplanar.create(layout, path=pya.DPath([pya.DPoint(0, 0), pya.DPoint(0, 99)], 0))
    assert hasattr(waveguide_cell, "length")
    assert waveguide_cell.length() == 99

    capacitor_cell = FingerCapacitorSquare.create(layout)
    assert not hasattr(capacitor_cell, "length")
