# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
from kqcircuits.simulations.finger_capacitor_sim import FingerCapacitorSim


def test_ansys_export_produces_output_files(layout, perform_test_ansys_export_produces_output_files):
    perform_test_ansys_export_produces_output_files(FingerCapacitorSim(layout))


def test_sonnet_export_produces_output_files(layout, perform_test_sonnet_export_produces_output_files):
        perform_test_sonnet_export_produces_output_files(FingerCapacitorSim(layout))
