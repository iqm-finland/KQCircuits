# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.


def test_export_produces_output_files(empty_simulation, perform_test_sonnet_export_produces_output_files):
    perform_test_sonnet_export_produces_output_files(empty_simulation)