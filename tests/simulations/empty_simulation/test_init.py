# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
from kqcircuits.simulations.empty_simulation import EmptySimulation
from kqcircuits.pya_resolver import pya


def test_can_create(empty_simulation):
    pass


def test_simulation_has_name(empty_simulation):
    assert empty_simulation.name == "Simulation"


def test_can_create_with_parameter_argument(layout):
    simulation = EmptySimulation(layout, name="TEST")
    assert simulation.name == "TEST"


def test_simulation_has_box(empty_simulation):
    assert type(empty_simulation.box) == pya.DBox