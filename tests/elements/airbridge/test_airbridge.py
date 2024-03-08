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


import pytest
from kqcircuits.pya_resolver import pya

from kqcircuits.elements.airbridges.airbridge import Airbridge


@pytest.fixture
def instance():
    instance = Airbridge()
    return instance


def test_display_text_impl(instance):
    assert instance.display_text_impl() == "Airbridge"


def test_coerce_parameters_impl(instance):
    assert instance.coerce_parameters_impl() is None


def test_can_create_from_shape_impl(instance):
    assert instance.can_create_from_shape_impl() is False


def test_parameters_from_shape_impl(instance):
    assert instance.parameters_from_shape_impl() is None


def test_transformation_from_shape_impl(instance):
    trans = instance.transformation_from_shape_impl()
    assert trans.rot == 0
    assert trans.disp.x == 0
    assert trans.disp.y == 0


def test_build():
    layout = pya.Layout()
    pcell = Airbridge.create(layout, r=123, airbridge_type="Airbridge Rectangular")
    parameters = pcell.pcell_parameters_by_name()
    assert parameters["r"] == 123
