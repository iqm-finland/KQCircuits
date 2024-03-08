# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not, see
# https://www.gnu.org/licenses/gpl-3.0.html.
#
# The software distribution should follow IQM trademark policy for open-source software
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


from kqcircuits.pya_resolver import pya

"""
    Module containing base unit tests to be used by all chips.

    The functions in this module are not pytest unit tests by themselves, but must be called by test functions in the
    modules for individual chip tests.

    Typical usage example:

        from tests.chips.chip_base_tests import errors_test, box_existence_test
        from kqcircuits.chips.single_xmons import SingleXmons

        def test_errors(capfd):
            errors_test(capfd, SingleXmons)

        def test_box_existence():
            box_existence_test(SingleXmons)

"""


def errors_test(capfd, cls):
    """Test if exceptions happen during creation of an element.

    When an element is created using create(), it calls the element's produce_impl(). Exceptions
    happening in produce_impl() are caught by KLayout and output to stderr. Thus we can't detect the exceptions
    directly, but we can check stderr for errors. NOTE: This assumes that there are no unrelated errors output to stderr
    by klayout. This may also not catch every possible error.
    """
    layout = pya.Layout()
    cell = cls.create(layout)
    out, err = capfd.readouterr()
    assert err == "", err


def box_existence_test(cls):
    layout = pya.Layout()
    cell = cls.create(layout)
    parameters = cell.pcell_parameters_by_name()
    assert type(parameters["box"]) is pya.DBox
