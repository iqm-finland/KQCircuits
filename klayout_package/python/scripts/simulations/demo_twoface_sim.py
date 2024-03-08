# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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

from pathlib import Path

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.port import EdgePort, InternalPort
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.parameters import add_parameters_from
from kqcircuits.chips.demo_twoface import DemoTwoface
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import export_simulation_oas
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    open_with_klayout_or_default_application,
    get_active_or_new_layout,
)


# This script is to demonstrate a full flip-chip simulation export.
# First, we introduce the simulation class that is inherited from Simulation.
# Second, we process the export script.
@add_parameters_from(Simulation, face_stack=["1t1", "2b1", []], substrate_box=DemoTwoface.face_boxes)
class DemoTwofaceSim(Simulation):

    def build(self):

        chip = self.add_element(
            DemoTwoface,
            **{"junction_type": "Sim", "marker_types": [None] * 8, "name_mask": "", "name_chip": "", "name_brand": ""},
        )

        # Insert chip and get refpoints
        _, refpoints = self.insert_cell(chip, rec_levels=None)

        maximum_box = pya.DBox(pya.DPoint(200, 200), pya.DPoint(9800, 9800))
        port_shift = 480

        # Limit the size of the box to fit the ports
        self.box &= maximum_box

        # Define edge ports, shifted inward by port_shift w.r.t. launcher refpoints
        for i, (port, shift) in enumerate(
            [
                ("DL-QB1", [-port_shift, 0]),
                ("DL-QB2", [port_shift, 0]),
                ("DL-QB3", [-port_shift, 0]),
                ("DL-QB4", [port_shift, 0]),
            ]
        ):
            self.ports.append(EdgePort(i + 1, refpoints["{}_port".format(port)] + pya.DVector(*shift)))

        # Add squid internal ports
        for i, port in enumerate(["QB1", "QB2", "QB3", "QB4"]):
            self.ports.append(
                InternalPort(
                    5 + i,
                    *self.etched_line(
                        refpoints["{}_squid_port_squid_a".format(port)], refpoints["{}_squid_port_squid_b".format(port)]
                    ),
                )
            )


# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
sim_parameters = {
    "name": "demo_twoface",
    "use_ports": True,
    "port_size": 1000,
}
export_parameters = {"path": dir_path, "sweep_enabled": False, "exit_after_run": False}

# Get layout
layout = get_active_or_new_layout()

# Create simulation
simulations = [DemoTwofaceSim(layout, **sim_parameters)]

# Export Ansys files
export_ansys(simulations, **export_parameters)

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
