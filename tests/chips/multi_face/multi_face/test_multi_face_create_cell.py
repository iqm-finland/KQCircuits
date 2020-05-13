from tests.chips.chip_test_helpers import errors_test, base_refpoint_existence_test

from kqcircuits.chips.multi_face.multi_face import MultiFace


def test_errors(capfd):
    errors_test(capfd, MultiFace)


def test_base_refpoint_existence():
    base_refpoint_existence_test(MultiFace)