# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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
import sys
from pathlib import Path

from kqcircuits.qubits.swissmon import Swissmon
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import export_simulation_oas
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)


sim_class = get_single_element_sim_class(Swissmon)  # pylint: disable=invalid-name

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
sim_parameters = {
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(1000, 1000)),
    "partition_regions": [{"face": "1t1", "vertical_dimensions": 1.0, "metal_edge_dimensions": 1.0}],
    "tls_sheet_approximation": True,
    "tls_layer_thickness": 0.01,
    "n": 24,
}
export_parameters = {
    "eigenmode": {
        "ansys_tool": "eigenmode",
        "exit_after_run": True,
        "max_delta_f": 0.05,
        "n_modes": 1,
        "frequency": 1.0,
        "maximum_passes": 20,
        "integrate_energies": True,
    },
    "voltage": {
        "ansys_tool": "voltage",
        "exit_after_run": True,
        "max_delta_e": 0.001,
        "frequency": 4.8,
        "maximum_passes": 20,
        "integrate_energies": True,
    },
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

simulations = []
for key, export_params in export_parameters.items():
    sim_params = {
        **sim_parameters,
        "name": f"swissmon_epr_{key}",
    }
    sims = [sim_class(layout, **sim_params)]

    exp_params = {
        **export_params,
        "post_process": PostProcess(
            "produce_epr_table.py",
            sheet_approximations={
                "MA": {"thickness": 1e-8, "eps_r": 8, "background_eps_r": 1.0},
                "SA": {"thickness": 1e-8, "eps_r": 4, "background_eps_r": 11.45},
                "MS": {"thickness": 1e-8, "eps_r": 11.4, "background_eps_r": 11.45},
            },
        ),
    }

    # Export simulation files
    export_ansys(sims, path=dir_path, file_prefix=f"simulation_{key}", **exp_params)
    simulations += sims

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
