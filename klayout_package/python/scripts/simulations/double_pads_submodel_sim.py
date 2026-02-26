# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
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

from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.simulation_export import export_simulation_oas
from kqcircuits.simulations.post_process import PostProcess
from kqcircuits.simulations.single_element_simulation import get_single_element_sim_class
from kqcircuits.util.export_helper import (
    create_or_empty_tmp_directory,
    get_active_or_new_layout,
    open_with_klayout_or_default_application,
)
from kqcircuits.simulations.export.elmer.elmer_solution import ElmerEPR3DSolution
from kqcircuits.simulations.export.elmer.mesh_size_helpers import refine_metal_edges
from kqcircuits.qubits.double_pads import DoublePads
from kqcircuits.util.refpoints import RefpointToInternalPort, WaveguideToSimPort


dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

parallel_elmer = False

sim_parameters = {
    "use_internal_ports": True,
    "use_ports": True,
    "tls_sheet_approximation": True,
    "tls_layer_thickness": 0.01,
    "name": "double_pads",
    "box": pya.DBox(pya.DPoint(0, 0), pya.DPoint(2000, 2000)),
    "face_stack": ["1t1"],
    "metal_height": 0.2,
    "coupler_a": 5,
    "a": 5,
    "b": 20,
    "island1_taper_junction_width": 8.0,
    "island2_taper_junction_width": 8.0,
    "island1_taper_width": 8.0,
    "island2_taper_width": 8.0,
    "detach_tls_sheets_from_body": False,
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Override the default simulation ports which use refpoints that only exist with Sim junction
DoublePads.get_sim_ports = lambda sim: [
    RefpointToInternalPort("probe_island_1"),
    RefpointToInternalPort("probe_island_2"),
    WaveguideToSimPort("port_cplr", side="top", a=sim.coupler_a),
]
voltages = [1, -1, 0.1]

SimClassManhattan = get_single_element_sim_class(DoublePads, sim_junction_type="Manhattan")
simulation = SimClassManhattan(layout, **sim_parameters)

# Enable additional details in the submodel
submodel_params = {
    # 3D TLS layers
    "tls_sheet_approximation": False,
    "tls_layer_material": ["oxideMA", "oxideMS", "oxideSA"],
    "material_dict": {
        **simulation.get_material_dict(),
        "oxideMA": {"permittivity": 8},
        "oxideMS": {"permittivity": 11.4},
        "oxideSA": {"permittivity": 4},
    },
    # Finer junction structures
    "finger_overshoot": -0.5,
    "base_metal_addition_layers": ["base_metal_addition", "SIS_junction", "SIS_junction_2"],
}

# Submodel centered at the junction
junction_sim = simulation.create_submodel(
    "junction_submodel",
    pya.DBox(pya.DPoint(975, 975), pya.DPoint(1025, 1025)),
    z_limits=[-5, 5],
    magnification_order=1,
    override_parameters=submodel_params,
)
# Submodel of the submodel
junction_sim_zoomed = junction_sim.create_submodel(
    "junction_submodel_zoomed",
    pya.DBox(pya.DPoint(989, 993), pya.DPoint(993, 997)),
    z_limits=[-2, 2],
    magnification_order=1,  # NOTE: This magnifies 1 more level from the larger submodel
    override_parameters=submodel_params,
)

# Main model solution settings
solution = ElmerEPR3DSolution(
    voltage_excitations=voltages,
    mesh_size=refine_metal_edges(5.0, 0.5),
    p_element_order=1,
    save_elmer_data=True,
    mg_smoother="CG" if parallel_elmer else "SGS",
)

# Updated solutions with finer meshing
submodel_solution = solution.updated(
    mesh_size={**refine_metal_edges(0.2, 0.5), "*layerMA*": 1, "*layerMS*": 1, "*layerSA*": 1},
    linear_system_preconditioning="ILU3",  # For better convergence
)
submodel_solution_zoomed = solution.updated(
    mesh_size={**refine_metal_edges(0.02, 0.5), "*layerMA*": 0.1, "*layerMS*": 0.1, "*layerSA*": 0.1},
    linear_system_preconditioning="ILU3",
    save_elmer_data=False,
)

# Export main simulation and submodels as a sweep
junction_sim_sol = [
    (simulation, solution),
    (junction_sim, submodel_solution),
    (junction_sim_zoomed, submodel_solution_zoomed),
]

workflow = {"elmer_n_processes": -1 if parallel_elmer else 1, "gmsh_n_threads": -1}

pp = PostProcess(
    "produce_epr_table.py",
    sheet_approximations={
        "MA": {"thickness": 1e-8, "eps_r": 8},
        "SA": {"thickness": 1e-8, "eps_r": 4},
        "MS": {"thickness": 1e-8, "eps_r": 11.4},
    },
)

export_elmer(junction_sim_sol, path=dir_path, workflow=workflow, post_process=pp)

open_with_klayout_or_default_application(export_simulation_oas([simulation], dir_path))
open_with_klayout_or_default_application(export_simulation_oas([junction_sim], dir_path, file_prefix=junction_sim.name))
open_with_klayout_or_default_application(
    export_simulation_oas([junction_sim_zoomed], dir_path, file_prefix=junction_sim_zoomed.name)
)
