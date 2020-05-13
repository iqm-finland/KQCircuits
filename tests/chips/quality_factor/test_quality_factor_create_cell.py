from tests.chips.chip_test_helpers import errors_test, base_refpoint_existence_test

from kqcircuits.chips.quality_factor import QualityFactor


def test_errors(capfd):
    errors_test(capfd, QualityFactor)


def test_base_refpoint_existence():
    base_refpoint_existence_test(QualityFactor)
