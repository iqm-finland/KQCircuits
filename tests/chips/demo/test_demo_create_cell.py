from tests.chips.chip_test_helpers import errors_test, base_refpoint_existence_test

from kqcircuits.chips.demo import Demo


def test_errors(capfd):
    errors_test(capfd, Demo)


def test_base_refpoint_existence():
    base_refpoint_existence_test(Demo)