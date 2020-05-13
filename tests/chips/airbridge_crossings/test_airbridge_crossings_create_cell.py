from tests.chips.chip_test_helpers import errors_test, base_refpoint_existence_test

from kqcircuits.chips.airbridge_crossings import AirbridgeCrossings


def test_errors(capfd):
    errors_test(capfd, AirbridgeCrossings)


def test_base_refpoint_existence():
    base_refpoint_existence_test(AirbridgeCrossings)