# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from tests.chips.chip_test_helpers import errors_test, base_refpoint_existence_test

from kqcircuits.chips.multi_face.demo_twoface import DemoTwoface

from autologging import logging


def test_errors(capfd, caplog):
    caplog.set_level(logging.DEBUG)
    errors_test(capfd, DemoTwoface)


def test_base_refpoint_existence():
    base_refpoint_existence_test(DemoTwoface)