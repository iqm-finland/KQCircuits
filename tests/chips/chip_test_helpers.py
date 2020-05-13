from kqcircuits.pya_resolver import pya

"""
    Module containing base unit tests to be used by all chips.
    
    The functions in this module are not pytest unit tests by themselves, but must be called by test functions in the 
    modules for individual chip tests.
    
    Typical usage example:
    
        from tests.chips.chip_base_tests import errors_test, base_refpoint_existence_test
        from kqcircuits.chips.single_xmons import SingleXmons
    
        def test_errors(capfd):
            errors_test(capfd, SingleXmons)
            
        def test_base_refpoint_existence():
            base_refpoint_existence_test(SingleXmons)

"""


def errors_test(capfd, cls):
    """Test if exceptions happen during creation of an element.

    When an element is created using create_cell(), it calls the element's produce_impl(). Exceptions
    happening in produce_impl() are caught by KLayout and output to stderr. Thus we can't detect the exceptions
    directly, but we can check stderr for errors. NOTE: This assumes that there are no unrelated errors output to stderr
    by klayout. This may also not catch every possible error.
    """
    layout = pya.Layout()
    cell = cls.create_cell(layout, {})
    out, err = capfd.readouterr()
    assert err == ""


def base_refpoint_existence_test(cls):
    layout = pya.Layout()
    cell = cls.create_cell(layout, {})
    parameters = cell.pcell_parameters_by_name()
    assert "base" in parameters["refpoints"]