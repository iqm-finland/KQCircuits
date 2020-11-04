# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
from kqcircuits.simulations.export.hfss.hfss_export import HfssExport


def test_can_create_hfss_export_of_empty_simulation(empty_simulation):
    hfss_export = HfssExport(empty_simulation)
