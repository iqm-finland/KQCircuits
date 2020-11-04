# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
from kqcircuits.simulations.export.sonnet.sonnet_export import SonnetExport


def test_can_create_sonnet_export_of_empty_simulation(empty_simulation):
    sonnet_export = SonnetExport(empty_simulation)
