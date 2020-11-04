# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from tests.chips.chip_test_helpers import errors_test, base_refpoint_existence_test

from kqcircuits.chips.stripes import Stripes


def test_errors(capfd):
    errors_test(capfd, Stripes)


def test_base_refpoint_existence():
    base_refpoint_existence_test(Stripes)

