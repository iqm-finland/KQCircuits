from tests.chips.chip_test_helpers import errors_test, base_refpoint_existence_test

from kqcircuits.chips.chip import Chip


def test_errors(capfd):
    errors_test(capfd, Chip)


def test_base_refpoint_existence():
    base_refpoint_existence_test(Chip)


