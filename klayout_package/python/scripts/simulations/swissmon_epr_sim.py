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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

import logging
import sys
from pathlib import Path

from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.cross_section.epr_correction_export import get_epr_correction_simulations

from kqcircuits.qubits.swissmon import Swissmon
from kqcircuits.simulations.epr.swissmon import partition_regions, correction_cuts
from kqcircuits.simulations.export.ansys.ansys_solution import AnsysEigenmodeSolution, AnsysVoltageSolution
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import export_simulation_oas, cross_combine
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)

use_xsection = True

# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
sim_class = get_single_element_sim_class(Swissmon, partition_region_function=partition_regions)
sim_parameters = {
    "name": "swissmon_epr",
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(1000, 1000)),
    "tls_sheet_approximation": True,
    "tls_layer_thickness": 0.01,
    "n": 24,
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Sweep solution type
simulations = cross_combine(
    sim_class(layout, **sim_parameters),
    [
        AnsysEigenmodeSolution(
            name="_eigenmode",
            max_delta_f=0.05,
            n_modes=1,
            min_frequency=1.0,
            maximum_passes=20,
            integrate_energies=True,
        ),
        AnsysVoltageSolution(
            name="_voltage", max_delta_e=0.001, frequency=4.8, maximum_passes=20, integrate_energies=True
        ),
    ],
)

# Export simulation files
export_ansys(
    simulations,
    path=dir_path,
    exit_after_run=True,
    post_process=(
        PostProcess("epr.sh", command="sh", folder="") if use_xsection else PostProcess("produce_epr_table.py")
    ),
)

# produce EPR correction simulations
if use_xsection:
    correction_simulations, post_process = get_epr_correction_simulations(
        simulations, correction_cuts, metal_height=0.2
    )
    export_elmer(
        correction_simulations,
        dir_path,
        file_prefix="epr",
        post_process=post_process,
    )

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
if use_xsection:
    open_with_klayout_or_default_application(export_simulation_oas(correction_simulations, dir_path, "epr"))
