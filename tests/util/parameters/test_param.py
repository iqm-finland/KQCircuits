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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).


import logging
import pytest
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
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


# test inherited parameters

def test_add_parameters_from_everything_inherited():
    @add_parameters_from(D)
    class Test(B):
        pass

    t = Test()
    params = set(p for p in t.pcell_params_by_name().keys() if p.startswith('p'))
    assert params == set(["pa1", "pa2", "pb1", "pb2", "pc1", "pc2", "pd1", "pd2"])


def test_add_parameters_from_inheritance_chain():
    @add_parameters_from(B)
    class Source(A):
        pass
    @add_parameters_from(Source)
    class Test(Element):
        pass

    p = Source()
    t = Test()
    assert p.pa1 == 1 and p.pb1 == 2
    assert t.pa1 == 1 and t.pb1 == 2


def test_add_parameters_from_longer_inheritance_chain():
    @add_parameters_from(B)
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
    assert p.pa2 == 10 and p.pb2 == 20
    assert s.pa2 == 10 and s.pb2 == 20
    assert t.pa2 == 10 and t.pb2 == 20


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
