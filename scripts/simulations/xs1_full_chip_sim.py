# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from pathlib import Path
import subprocess
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import export_simulation_oas
from kqcircuits.simulations.single_xmons_full_chip_sim import SingleXmonsFullChipSim
from kqcircuits.util.export_helper import create_or_empty_tmp_directory

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
sim_class = SingleXmonsFullChipSim
sim_parameters = {
    'use_ports': True,
    'launchers': True,  # True includes bonding pads and tapers, false includes only waveguides
    'use_test_resonators': True,  # True makes XS1, false makes XS2
    'n': 16,  # Reduce number of point in waveguide corners
    'port_width': 200
}
export_parameters = {
    'path': dir_path
}

# Create simulation
simulations = [sim_class(pya.Layout(), **sim_parameters)]

# Export Ansys files
export_ansys(simulations, **export_parameters)

# Write and open oas file
subprocess.call(export_simulation_oas(simulations, dir_path), shell=True)
