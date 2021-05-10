# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import pytest
from kqcircuits.pya_resolver import pya
from autologging import TRACE

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


def test_produce_impl():
    layout = pya.Layout()
    pcell = Airbridge.create(layout, r=123, airbridge_type="Airbridge Rectangular")
    parameters = pcell.pcell_parameters_by_name()
    assert parameters["r"] == 123
