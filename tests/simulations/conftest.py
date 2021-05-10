# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
from pathlib import Path

import pytest
from kqcircuits.simulations.empty_simulation import EmptySimulation
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.sonnet.sonnet_export import export_sonnet


@pytest.fixture
def layout():
    """ Return a new pya Layout """
    return pya.Layout()


@pytest.fixture
def empty_simulation(layout):
    """ Return an instance of EmptySimulation """
    return EmptySimulation(layout)


@pytest.fixture
def perform_test_ansys_export_produces_output_files(tmp_path):
    def perform_test_ansys_export_produces_output_implementation(simulation):
        bat_filename = export_ansys([simulation], path=tmp_path)
        assert Path(bat_filename).exists()

    return perform_test_ansys_export_produces_output_implementation


@pytest.fixture
def perform_test_sonnet_export_produces_output_files(tmp_path):
    def perform_test_sonnet_export_produces_output_implementation(simulation):
        son_filename = export_sonnet([simulation], path=tmp_path)[0]
        assert Path(son_filename).exists()

    return perform_test_sonnet_export_produces_output_implementation

