# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
from kqcircuits.simulations.single_xmons_full_chip_sim import SingleXmonsFullChipSim


def test_can_create(layout):
    simulation = SingleXmonsFullChipSim(layout)
