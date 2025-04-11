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
import ast
import logging
import sys

# from itertools import product
from pathlib import Path

from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer

# from kqcircuits.simulations.export.elmer.elmer_solution import ElmerEPR3DSolution

from kqcircuits.simulations.export.simulation_export import export_simulation_oas, sweep_simulation
from kqcircuits.simulations.port import EdgePort
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)


class TlsWaveguideSim(Simulation):
    """A very short segment of waveguide."""

    def build(self):
        self.insert_cell(
            WaveguideCoplanar,
            path=pya.DPath(
                [pya.DPoint(self.box.left, self.box.center().y), pya.DPoint(self.box.right, self.box.center().y)], 0
            ),
        )
        self.ports.append(EdgePort(1, pya.DPoint(self.box.left, self.box.center().y), face=0))
        self.ports.append(EdgePort(2, pya.DPoint(self.box.right, self.box.center().y), face=0))


class TlsWaveguideSim2(Simulation):
    """A very short segment of 2 parallel waveguides."""

    def build(self):
        wg_ys = [(self.box.bottom + self.box.center().y) / 2, (self.box.top + self.box.center().y) / 2]

        for ind, wg_y in enumerate(wg_ys):
            self.insert_cell(
                WaveguideCoplanar,
                path=pya.DPath([pya.DPoint(self.box.left, wg_y), pya.DPoint(self.box.right, wg_y)], 0),
            )
            self.ports.append(EdgePort(2 * ind + 1, pya.DPoint(self.box.left, wg_y), face=0))
            self.ports.append(EdgePort(2 * ind + 2, pya.DPoint(self.box.right, wg_y), face=0))


# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")


# If True models the tls layers as sheets. Leads to computationally easier system especially with
# small interface thicknesses. sheet_approximations need to be set in post-processing to get correct EPRs.
# Uses a custom Elmer energy integration module
sheet_interfaces = True


dielectric_surfaces = {
    "MA": {"thickness": 4.8e-9, "eps_r": 8},
    "MS": {"thickness": 0.3e-9, "eps_r": 11.4},
    "SA": {"thickness": 2.4e-9, "eps_r": 4},
}
tls_layer_thickness = [dielectric_surfaces[layer]["thickness"] * 1e6 for layer in ("MA", "MS", "SA")]

# Simulation parameters
sim_class = TlsWaveguideSim2  # pylint: disable=invalid-name
sim_parameters = {
    "name": "tls_waveguide_sim",
    "face_stack": ["1t1"],  # single chip
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(10, 100)),
    "substrate_height": 50,  # limited simulation domain
    "upper_box_height": 50,  # limited simulation domain
    "metal_height": [0.2],
    "partition_regions": [
        {"name": "mer", "metal_edge_dimensions": 1.0, "vertical_dimensions": 1.0, "face": "1t1", "visualise": True}
    ],
    "tls_sheet_approximation": sheet_interfaces,
    "detach_tls_sheets_from_body": not sheet_interfaces,
    "extra_json_data": {f"{k}_thickness": t for t, k in zip(tls_layer_thickness, ("ma", "ms", "sa"))},
}

sol_parameters = {
    "tool": "epr_3d",
    "mesh_size": {"1t1_layerMAmer": 0.5, "1t1_layerMSmer": 0.5, "1t1_layerSAmer": 0.5},
    "linear_system_method": "mg",
    "voltage_excitations": [1.0, 0.5],  # Explicitly set the signal voltages
    "save_elmer_data": True,
}

post_process = [
    PostProcess(
        "tls_monte_carlo_points.py",
        arguments="--density-ma 200 --density-ms 200 --density-sa 200 --density-substrate 0.002",
    ),
    PostProcess("extract_field_values.py"),
]

if sheet_interfaces:
    post_process = [
        PostProcess(
            "produce_epr_table.py",
            sheet_approximations=dielectric_surfaces,
        )
    ] + post_process
else:
    # change TLS layer material and set their thicknesses
    sim_parameters.update(
        {
            "tls_layer_thickness": tls_layer_thickness,
            "tls_layer_material": ["oxideMA", "oxideMS", "oxideSA"],
            "material_dict": {
                **ast.literal_eval(Simulation.material_dict),
                "oxideMA": {"permittivity": dielectric_surfaces["MA"]["eps_r"]},
                "oxideMS": {"permittivity": dielectric_surfaces["MS"]["eps_r"]},
                "oxideSA": {"permittivity": dielectric_surfaces["SA"]["eps_r"]},
            },
        }
    )

    # Refine MA wall if using 3D interfaces
    sol_parameters["mesh_size"]["1t1_layerMAwallmer"] = 0.3

    post_process = [PostProcess("produce_epr_table.py")] + post_process

workflow = {
    "run_gmsh_gui": False,
    "run_elmergrid": True,
    "run_elmer": True,
    "run_paraview": False,
    "python_executable": "python",
    "gmsh_n_threads": -1,  #  Number of omp threads in gmsh
    "elmer_n_processes": 2,  # Number of dependent processes (tasks) in elmer
    "elmer_n_threads": 1,  # Number of omp threads per process in elmer
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

simulations = sweep_simulation(layout, sim_class, sim_parameters, {"a": [2, 10]})

export_elmer(simulations, path=dir_path, workflow=workflow, post_process=post_process, **sol_parameters)

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
