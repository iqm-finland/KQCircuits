# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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


import logging
import pytest
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from, add_parameter
from kqcircuits.elements.element import Element


log = logging.getLogger(__name__)

# define test classes


class A(Element):
    pa1 = Param(pdt.TypeInt, "", 1)
    pa2 = Param(pdt.TypeInt, "", 10)


class B(A):
    pb1 = Param(pdt.TypeInt, "", 2)
    pb2 = Param(pdt.TypeInt, "", 20)


class C(Element):
    pc1 = Param(pdt.TypeInt, "", 3)
    pc2 = Param(pdt.TypeInt, "", 30)


class D(C):
    pd1 = Param(pdt.TypeInt, "", 4)
    pd2 = Param(pdt.TypeInt, "", 40)


# normal cases


def test_param_basics():
    a = A()
    assert a.pa1 == 1 and a.pa2 == 10

    b = B()
    assert a.pa1 == 1 and a.pa2 == 10
    assert b.pb1 == 2 and b.pb2 == 20


def test_param_choices():
    class Test(Element):
        cp1 = Param(pdt.TypeInt, "", "One", choices=["One", "Two"])
        cp2 = Param(pdt.TypeInt, "", 2, choices=[["One", 1], ["Two", 2]])
        pass

    t = Test()
    assert t.cp2 == 2 and t.cp1 == "One"


def test_param_override():
    class Test(A):
        pa1 = Param(pdt.TypeInt, "", 2)
        pass

    t = Test()
    assert t.pa1 == 2


def test_add_parameters_from_get_all():
    @add_parameters_from(A)
    class Test(Element):
        pass

    t = Test()
    assert t.pa1 == 1 and t.pa2 == 10


def test_add_parameters_from_get_one():
    @add_parameters_from(A, "pa2")
    class Test(Element):
        pass

    t = Test()
    assert not hasattr(t, "pa1")
    assert t.pa2 == 10


def test_add_parameters_from_change_one():
    @add_parameters_from(A, pa2=-10)
    class Test(Element):
        pass

    t = Test()
    assert not hasattr(t, "pa1")
    assert t.pa2 == -10


def test_add_parameters_from_get_and_change():
    @add_parameters_from(A, "pa1", pa2=-10)
    class Test(Element):
        pass

    t = Test()
    assert t.pa1 == 1
    assert t.pa2 == -10


def test_add_parameters_from_overrides_both():
    @add_parameters_from(A, "pa1", pa2=20)
    class Test(A):
        pa1 = Param(pdt.TypeInt, "", 666)
        pa2 = Param(pdt.TypeInt, "", 666)
        pass

    t = Test()
    # Note that add_parameters_from() overrides existing params
    assert t.pa1 == 1 and t.pa2 == 20


def test_add_parameters_from_override_with_same_default():
    @add_parameters_from(A, pa1=1)
    class Test(Element):
        pass

    t = Test()
    assert t.pa1 == 1


# test inherited parameters


def test_add_parameters_from_everything_inherited():
    @add_parameters_from(D)
    class Test(B):
        pass

    t = Test()
    params = set(t.pcell_params_by_name().keys())
    abcd12 = set(["pa1", "pa2", "pb1", "pb2", "pc1", "pc2", "pd1", "pd2"])
    assert abcd12.issubset(params)


def test_add_parameters_from_inheritance_chain():
    @add_parameters_from(C)
    class Source(A):
        pass

    @add_parameters_from(Source)
    class Test(Element):
        pass

    p = Source()
    t = Test()
    assert p.pa1 == t.pa1 and p.pc1 == t.pc1


def test_add_parameters_from_longer_inheritance_chain():
    @add_parameters_from(C)
    class SourceParent(A):
        pass

    class Source(SourceParent):
        pass

    @add_parameters_from(Source)
    class Test(Element):
        pass

    p = SourceParent()
    s = Source()
    t = Test()
    assert p.pa2 == s.pa2 == t.pa2
    assert p.pc2 == s.pc2 == t.pc2


# test wildcard and parameter removal


def test_add_parameters_from_get_all_change_one():
    @add_parameters_from(A, "*", pa2=-1)
    class Test(Element):
        pass

    t = Test()
    assert t.pa1 == 1 and t.pa2 == -1


def test_add_parameters_from_remove_two():
    @add_parameters_from(B, "*", "pa1", "pb1")
    class Test(Element):
        pass

    t = Test()
    assert not hasattr(t, "pa1") and not hasattr(t, "pb1")
    assert hasattr(t, "pa2") and hasattr(t, "pb2")


def test_add_parameters_from_syntax_sugar():
    @add_parameters_from(B)
    class Test1(Element):
        pass

    @add_parameters_from(B, "*")
    class Test2(Element):
        pass

    t1 = Test1()
    t2 = Test2()
    assert t1.pcell_params_by_name() == t2.pcell_params_by_name()


def test_add_parameters_from_change_overrides_removal():
    @add_parameters_from(A, "*", "pa1", pa1=-1)
    class Test(Element):
        pass

    t = Test()
    assert t.pa1 == -1 and t.pa2 == 10


# test error handling


def test_add_parameters_from_detect_bad_param():
    try:

        @add_parameters_from(A, "unknown_parameter")
        class Test(Element):
            pass

    except ValueError:
        pass
    else:
        assert False


def test_add_parameters_from_detect_bad_param_change():
    try:

        @add_parameters_from(A, unknown_parameter=123)
        class Test(Element):
            pass

    except ValueError:
        pass
    else:
        assert False


def test_add_parameters_from_detect_bad_param_removal():
    try:

        @add_parameters_from(A, "*", "unknown_parameter")
        class Test(Element):
            pass

    except ValueError:
        pass
    else:
        assert False


# test add_parameter


def test_add_param_unchanged():
    @add_parameter(A, "pa1")
    class Test(Element):
        pass

    t = Test()
    assert t.pa1 == 1
    assert not hasattr(t, "pa2")


def test_add_param_hide():
    @add_parameter(A, "pa2", hidden=True)
    @add_parameter(A, "pa1")
    class Test(Element):
        pass

    s = Test.get_schema()
    assert "hidden" not in s["pa1"].kwargs
    assert s["pa2"].kwargs["hidden"]


def test_add_param_default():
    @add_parameter(A, "pa1", default=123, hidden=False)
    class Test(Element):
        pass

    t = Test()
    s = Test.get_schema()
    assert not s["pa1"].kwargs["hidden"] and t.pa1 == 123
    assert A.pa1 == 1


def test_add_param_choices_description_and_unit():
    test_choices = [["One", 1], ["Two", 2]]

    @add_parameter(A, "pa1", choices=test_choices, unit="nm", description="FooBar")
    class Test(Element):
        pass

    s = Test.get_schema()
    assert s["pa1"].kwargs["choices"] == test_choices
    assert s["pa1"].kwargs["unit"] == "nm"
    assert s["pa1"].description == "FooBar"


def test_add_param_inherited():
    @add_parameter(A, "pa1", hidden=True)
    class Parent(Element):
        pass

    class Test(Parent):
        pass

    assert Test.get_schema()["pa1"].kwargs["hidden"]
