# This code is part of KQCircuits
# Copyright (C) 2026 IQM Finland Oy
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
from math import sqrt

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.simulation_export import export_simulation_oas
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.waveguides_sim import WaveGuidesSim
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)
from kqcircuits.simulations.export.elmer.elmer_solution import ElmerEigenmodeSolution
from kqcircuits.simulations.export.elmer.mesh_size_helpers import refine_metal_edges
from kqcircuits.simulations.export.ansys.ansys_solution import AnsysEigenmodeSolution
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from scipy.constants import speed_of_light

SimClass = WaveGuidesSim
path = create_or_empty_tmp_directory("eigenmode_test")

box_size_x = 6000
box_size_y = 1000

boxmode_box_size_x = 8000
boxmode_box_size_y = 8000
use_elmer = True

sim_parameters = {
    "name": "waveguide",
    "use_internal_ports": True,
    "use_edge_ports": False,
    "port_termination_end": False,
    "use_ports": True,
    "box": pya.DBox(pya.DPoint(-box_size_x / 2.0, -box_size_y / 2.0), pya.DPoint(box_size_x / 2.0, box_size_y / 2.0)),
    "cpw_length": 4000,  # if edge_ports then this has to be box_size_x
    "a": 10,
    "b": 6,
    "add_bumps": False,
    "face_stack": ["1t1"],
    "n_guides": 1,
    "port_size": 50,
    "substrate_height": [1000, 1000],
    "upper_box_height": 1000,
}
# lets make another simulation for calculating boxmodes only
# (for 8000x8000x1000 chip + 8000x8000x1000 substrate geometry)
sim_box = sim_parameters.copy()
sim_box["name"] = "box"
sim_box["box"] = pya.DBox(
    pya.DPoint(-boxmode_box_size_x / 2.0, -boxmode_box_size_y / 2.0),
    pya.DPoint(boxmode_box_size_x / 2.0, boxmode_box_size_y / 2.0),
)
sim_box["cpw_length"] = 10

# Get layout
logging.basicConfig(level=logging.INFO, stream=sys.stdout, force=True)
layout = get_active_or_new_layout()
eps_silicon = 11.45
eps_eff = (eps_silicon + 1) / 2  # silicon and vacuum
cpw_fundamental_f = speed_of_light / 2 / sim_parameters["cpw_length"] / sqrt(eps_eff)
box_fundamental_f = (
    speed_of_light / 2 / sqrt(eps_silicon) * sqrt((1 / boxmode_box_size_x) ** 2 + (1 / boxmode_box_size_y) ** 2)
)  # lower box is silicon and lower fundamental
logging.info("Calculating two example cases:")
logging.info(
    f"1. cpw of length {sim_parameters['cpw_length']} whose fundamental frequency is {cpw_fundamental_f/1000:.2f} GHz"
)
logging.info(
    f"2. silicon box of size {boxmode_box_size_x}x{boxmode_box_size_y}x{sim_box['substrate_height'][0]} "
    f"whose fundamental frequency is {box_fundamental_f/1000:.2f} GHz"
)

if use_elmer:
    logging.info(
        f"You can compare these to the results in {path}/{sim_parameters['name']}/f.dat and "
        f"{path}/{sim_box['name']}/f.dat"
    )
    solution = ElmerEigenmodeSolution(
        mesh_size={
            "global_max": 1000,
            **refine_metal_edges(10.0, 0.5),
        },
        linear_system_method="mumps",  # umfpack could work if you don't have mumps
        use_multigrid_solver=False,
        n_modes=10,
        min_frequency=1,
    )
    simulations = [(SimClass(layout, **sim_parameters), solution), (SimClass(layout, **sim_box), solution)]
    workflow = {
        "run_gmsh_gui": True,
        "run_elmergrid": True,
        "run_elmer": True,
        "run_paraview": False,
        "python_executable": "python",
        "gmsh_n_threads": -1,  #  Number of omp threads in gmsh
        "elmer_n_processes": 1,  # Number of dependent processes (tasks) in elmer
        "elmer_n_threads": 1,  # Number of omp threads per process in elmer
    }

    export_elmer(simulations, path=path, workflow=workflow)
else:
    solution = AnsysEigenmodeSolution(
        name="_eigenmode",
        max_delta_f=0.05,
        n_modes=10,
        min_frequency=1.0,
        maximum_passes=20,
        integrate_energies=True,
        mesh_size={"*gap": 20},
    )
    simulations = [(SimClass(layout, **sim_parameters), solution), (SimClass(layout, **sim_box), solution)]
    export_ansys(
        simulations,
        path=path,
        exit_after_run=True,
    )


# Create simulation
open_with_klayout_or_default_application(export_simulation_oas(simulations, path))
