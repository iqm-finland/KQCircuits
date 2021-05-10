# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
from kqcircuits.simulations.flip_chip_connector_sim import FlipChipConnectorSim


def test_can_create(layout):
    simulation = FlipChipConnectorSim(layout)
