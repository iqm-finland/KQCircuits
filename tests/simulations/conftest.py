# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
import pytest
from kqcircuits.simulations.empty_simulation import EmptySimulation
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.hfss.hfss_export import HfssExport
from kqcircuits.simulations.export.sonnet.sonnet_export import SonnetExport


@pytest.fixture
def layout():
    """ Return a new pya Layout """
    return pya.Layout()


@pytest.fixture
def empty_simulation(layout):
    """ Return an instance of EmptySimulation """
    return EmptySimulation(layout)


@pytest.fixture
def perform_test_hfss_export_produces_output_files(tmp_path):
    def perform_test_hfss_export_produces_output_implementation(simulation):
        hfss_export = HfssExport(simulation, path=tmp_path)
        hfss_export.write()

        assert hfss_export.oas_filename.exists()
        assert hfss_export.json_filename.exists()
        assert hfss_export.gds_filename.exists()

    return perform_test_hfss_export_produces_output_implementation


@pytest.fixture
def perform_test_sonnet_export_produces_output_files(tmp_path):
    def perform_test_sonnet_export_produces_output_implementation(simulation):
        sonnet_export = SonnetExport(simulation, path=tmp_path)
        sonnet_export.write()

        assert sonnet_export.son_filename.exists()

    return perform_test_sonnet_export_produces_output_implementation

