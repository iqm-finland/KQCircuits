from tests.chips.chip_test_helpers import errors_test, base_refpoint_existence_test

from kqcircuits.chips.single_xmons import SingleXmons


def test_errors(capfd):
    errors_test(capfd, SingleXmons)


def test_base_refpoint_existence():
    base_refpoint_existence_test(SingleXmons)
