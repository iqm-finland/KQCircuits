from tests.chips.chip_test_helpers import errors_test, base_refpoint_existence_test

from kqcircuits.chips.fluxline_test import FluxlineTest


def test_errors(capfd):
    errors_test(capfd, FluxlineTest)


def test_base_refpoint_existence():
    base_refpoint_existence_test(FluxlineTest)