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
from kqcircuits.simulations.port import InternalPort
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.parameters import add_parameters_from, Param, pdt

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import export_simulation_oas
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)


@add_parameters_from(Swissmon)
class SwissmonFluxlineSim(Simulation):
    flux_simulation = Param(pdt.TypeBoolean, "Setup for magnetic flux simulations", True)

    def build(self):
        params = self.get_parameters()
        if not self.flux_simulation:
            params["junction_type"] = "Sim"

        qubit_cell = self.add_element(Swissmon, **params)
        qubit_trans = pya.DTrans(0, False, self.box.center())
        _, refp = self.insert_cell(qubit_cell, qubit_trans, rec_levels=None)

        # Add internal port next to edge
        self.produce_waveguide_to_port(refp["port_flux"], refp["port_flux_corner"], 1, use_internal_ports="at_edge")

        if self.flux_simulation:
            # Setup squid and refinement boxes for magnetic flux simulations
            self.partition_regions = [
                {"name": "squid", "face": "1t1", "vertical_dimensions": 0.0, "region": pya.DBox(995, 840, 1005, 850)},
                {"name": "refine", "face": "1t1", "vertical_dimensions": 5.0, "region": pya.DBox(985, 825, 1015, 855)},
            ]
        else:
            # Add qubit port
            self.ports.append(InternalPort(2, *self.etched_line(refp["port_squid_a"], refp["port_squid_b"])))


# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
sim_parameters = {
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(2000, 2000)),
}
export_parameters = {
    "mut_ind": {
        "ansys_tool": "current",
        "exit_after_run": True,
        "max_delta_e": 0.01,
        "frequency": 0.1,
        "maximum_passes": 20,
        "integrate_magnetic_flux": True,
        "mesh_size": {"squid": 2, "vacuumrefine": 4, "substraterefine": 4},
    },
    "decay": {
        "ansys_tool": "hfss",
        "exit_after_run": True,
        "max_delta_s": 0.005,
        "frequency": 4.5,
        "maximum_passes": 20,
        "sweep_enabled": False,
        "post_process": PostProcess("calculate_q_from_s.py"),
    },
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

simulations = []
for key, export_params in export_parameters.items():
    sim_params = {
        **sim_parameters,
        "name": f"fluxline_{key}",
        "flux_simulation": export_params["ansys_tool"] == "current",
    }
    sims = [SwissmonFluxlineSim(layout, **sim_params)]

    # Export simulation files
    export_ansys(sims, path=dir_path, file_prefix=f"simulation_{key}", **export_params)
    simulations += sims

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
