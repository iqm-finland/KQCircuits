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

import sys
import logging
from pathlib import Path

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import export_simulation_oas, cross_sweep_simulation
from kqcircuits.simulations.airbridges_sim import AirbridgesSim
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)

# Simulation parameters
sim_class = AirbridgesSim  # pylint: disable=invalid-name

dir_path = Path(Path(__file__).stem + "_output")
created_dir = create_or_empty_tmp_directory(dir_path)

export_parameters = {
    "ansys_tool": "q3d",
    "post_process": PostProcess("produce_cmatrix_table.py"),
    "percent_error": 0.2,
    "minimum_converged_passes": 2,
    "maximum_passes": 40,
    "exit_after_run": True,
}
sim_parameters = {
    "name": "airbridges",
    "use_internal_ports": True,
    "use_ports": True,
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(1000, 500)),
    "waveguide_length": 100,
    "a": 10,
    "b": 6,
    "n_bridges": 2,
}

# ** Different line impedances **
waveguide_parameters = [
    {"name": "airbridges_51", "a": 10, "b": 6},  # 51 Ohm
    {"name": "airbridges_86", "a": 5, "b": 20},  # 86 Ohm
    {"name": "airbridges_100", "a": 4, "b": 30},  # 100 Ohm
]

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Sweep simulations
simulations = []
for wg_params in waveguide_parameters:
    simulations += cross_sweep_simulation(
        layout,
        sim_class,
        {
            **sim_parameters,
            **wg_params,
        },
        {
            "n_bridges": range(15),
        },
    )

# Export Ansys files
sub_path = create_or_empty_tmp_directory(dir_path.joinpath("airbridges_sim"))

# Write and open oas file
export_ansys(simulations, path=sub_path, **export_parameters)
open_with_klayout_or_default_application(export_simulation_oas(simulations, sub_path))
