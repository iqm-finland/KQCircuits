# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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
# pylint: disable=too-many-lines
import csv
import re
import json
import logging
import time
import shutil
from pathlib import Path
from typing import Any
from gmsh_helpers import get_elmer_layers, MESH_LAYER_PREFIX, get_metal_layers, apply_elmer_layer_prefix

from scipy.constants import epsilon_0
from scipy.signal import find_peaks
import numpy as np
import pandas as pd


def use_london_equations(json_data):
    return any(m.get("london_penetration_depth", 0) > 0 for m in json_data["material_dict"].values())


def read_mesh_names(path: Path) -> tuple[list[str], list[str]]:
    """Returns names of bodies and boundaries, respectively, from mesh.names file"""
    list_of_bodies = []
    list_of_boundaries = []
    current_list = list_of_bodies
    with open(path.joinpath("mesh.names"), encoding="utf-8") as file:
        for line in file:
            if "! ----- names for bodies -----" in line:
                current_list = list_of_bodies
            elif "! ----- names for boundaries -----" in line:
                current_list = list_of_boundaries
            elif line.startswith("$ "):
                eq_sign = line.find(" =")
                if eq_sign > 2:
                    current_list.append(line[2:eq_sign])
    return list_of_bodies, list_of_boundaries


def coordinate_scaling(json_data: dict[str, Any]) -> float:
    """
    Returns coordinate scaling, which is determined by parameters 'units' in json_data.

    Args:
        json_data: all the model data produced by `export_elmer_json`

    Returns:
        unit multiplier
    """
    units = json_data.get("units", "").lower()
    return {"nm": 1e-9, "um": 1e-6, "µm": 1e-6, "mm": 1e-3}.get(units, 1.0)


def sif_common_header(
    json_data: dict[str, Any],
    folder_path: Path | str,
    mesh_path: Path | str,
    angular_frequency: str | float | None = None,
    def_file: str | None = None,
    dim: int = 3,
    discontinuous_boundary: bool = False,
    constraint_modes_analysis: bool = True,
    output_file: str | None = None,
    restart_file: str | None = None,
    restart_position: int | None = None,
) -> str:
    """
    Returns common header and simulation blocks of a sif file in string format.
    Optional definition file name is given in 'def_file'.

    """
    res = "Check Keywords Warn\n"
    res += f"INCLUDE {mesh_path}/mesh.names\n"
    if def_file:
        res += f"INCLUDE {mesh_path}/{def_file}\n"
    res += sif_block("Header", [f'Mesh DB "." "{mesh_path}"', f'Results Directory "{folder_path}"'])

    if json_data.get("maximum_passes", 1) > 1:
        reset_adaptive_remesh_str = ["Reset Adaptive Mesh = Logical True"]
    else:
        reset_adaptive_remesh_str = []

    res += sif_block(
        "Run Control",
        [
            f"Constraint Modes Analysis = {constraint_modes_analysis}",
        ]
        + reset_adaptive_remesh_str,
    )

    res += sif_block(
        "Simulation",
        [
            "Max Output Level = 6",
            (
                'Coordinate System = "Axi Symmetric"'
                if json_data.get("is_axisymmetric", False)
                else f'Coordinate System = "Cartesian {str(dim)}D"'
            ),
            'Simulation Type = "Steady State"',
            f'Steady State Max Iterations = {json_data.get("maximum_passes", 1)}',
            f'Steady State Min Iterations = {json_data.get("minimum_passes", 1)}',
            f"Coordinate Scaling = {coordinate_scaling(json_data)}",
            f'Mesh Levels = {json_data.get("mesh_levels", 1)}',
        ]
        + ("Discontinuous Boundary Full Angle = Logical True" if discontinuous_boundary else [])
        + ([] if angular_frequency is None else [f"Angular Frequency = {angular_frequency}"])
        + ([f'Output File = "{output_file}"', "Binary Output = True", "Output Intervals(1) = 1"] if output_file else [])
        + ([f'Restart File = "{restart_file}"'] if restart_file else [])
        + ([f"Restart Position = {restart_position}"] if restart_position is not None else []),
    )
    return res


def sif_block(block_name: str, data: list[str]) -> str:
    """Returns block segment of sif file in string format. Argument data is list of lines inside the block.
    The block is of shape:

    'block_name'
      data[0]
      data[1]
      .
      .
    End
    """
    res = block_name + "\n"
    for line in data:
        res += f"  {line}\n"
    res += "End\n"
    return res


def sif_matc_block(data: list[str]) -> str:
    """Returns several matc statements to be used in sif (user does not need to type $-sign in front of lines).
    The block is of shape:
      $ data[0]
      $ data[1]
          .
          .
          .
      $ data[n]
    """
    return "".join(f"$  {line}\n" for line in data)


def sif_linsys(json_data: dict) -> list[str]:
    """
    Returns a linear system definition in sif format.

    Args:
        json_data: all the model data produced by `export_elmer_json`
            See kqcircuits/simulations/export/elmer/elmer_solution.py for docstring of the parameters used from the json

    Returns:
        linear system definitions in sif file format
    """
    linsys = [
        f"$pn={json_data['p_element_order']}",
        "Element = p:$pn",
        "Vector Assembly = True",
    ]
    linsys_method = json_data["linear_system_method"].lower()
    preconditioner = json_data["linear_system_preconditioning"]

    if linsys_method in ["umfpack", "mumps", "pardiso", "superlu"]:
        # direct methods
        linsys += [
            'Linear System Solver = String "Direct"',
            f'Linear system direct method = "{linsys_method}"',
        ]

    else:
        # iterative methods
        linsys += [
            "Linear System Solver = Iterative",
            f"Linear System Max Iterations = Integer {json_data['max_iterations']}",
            f"Linear System Convergence Tolerance = {json_data['convergence_tolerance']}",
            "Linear System Abort Not Converged = False",
        ]

        if linsys_method == "mg":
            linsys += [
                "Linear System Iterative Method = GCR ",
                "Linear System Residual Output = 10",
                "Linear System Preconditioning = multigrid !ILU2",
                "Linear System Refactorize = False",
                "MG Method = p",
                "MG Levels = $pn",
                # SGS has some problems with parallel performance. As an alternative, more reliable
                # CG could be used, but on average it seems to lead to even worse convergence
                "MG Smoother = SGS",
                "MG Pre Smoothing iterations = 2",
                "MG Post Smoothing Iterations = 2",
                "MG Lowest Linear Solver = iterative",
                "mglowest: Linear System Scaling = False",
                "mglowest: Linear System Iterative Method = CG !BiCGStabl",
                f"mglowest: Linear System Preconditioning = {preconditioner}",
                "mglowest: Linear System Max Iterations = 1000",
                "mglowest: Linear System Convergence Tolerance = 1.0e-4",
            ]
        else:
            linsys += [
                f"Linear System Iterative Method = {linsys_method}",
                f"Linear System Preconditioning = {preconditioner}",
                "Linear System ILUT Tolerance = 1.0e-03",
            ]

    # Adaptive meshing
    percent_error = json_data["percent_error"]
    linsys += [f"Steady State Convergence Tolerance = {1e-9 if percent_error is None else percent_error*1e-1}"]

    return linsys


def sif_adaptive_mesh(json_data: dict) -> list[str]:
    """Returns a definition of adaptive meshing settings in sif format.

    Args:
        json_data: all the model data produced by `export_elmer_json`
            See kqcircuits/simulations/export/elmer/elmer_solution.py for docstring of the parameters used from the json

    Returns:
        adaptive meshing definitions in sif format.

    Note:
        ``maximum_passes`` is already set in :func:`~sif_common_header`
    """
    adaptive_lines = [
        "Run Control Constraint Modes = Logical True",
        "Adaptive Mesh Refinement = True",
        "Adaptive Remesh = True",
        f"Adaptive Error Limit = {json_data['percent_error']}",
        "Adaptive Remesh Use MMG = Logical True",
        "Adaptive Mesh Numbering = False",
        f"Adaptive Min Depth = {json_data['minimum_passes']}",
        f"Adaptive Max Error Scale = Real {json_data['max_error_scale']}",
        f"Adaptive Max Outlier Fraction = Real {json_data['max_outlier_fraction']}",
        "MMG niter = Integer 1",
    ]
    return adaptive_lines


def get_port_solver(json_data: dict[str, Any], ordinate: int | str) -> str:
    """
    Returns a port solver for wave equation in sif format.

    Args:
        json_data: all the model data produced by `export_elmer_json`
            See kqcircuits/simulations/export/elmer/elmer_solution.py for docstring of the parameters used from the json
        ordinate: solver ordinate

    Returns:
        port solver in sif format.
    """
    solver_lines = [
        'Equation = "port-calculator"',
        'Procedure = "StatElecSolve" "StatElecSolver"',
        'variable = "potential"',
        "Variable DOFs = 1",
        "Calculate Electric Field = false",
        "calculate electric energy = false",
        "Linear System Solver = Iterative",
        "Linear System Iterative Method = BiCGStab",
        "! linear system use trilinos = true",
        "Linear System Convergence Tolerance = 1.0e-5",
        "Linear System Residual Output = 0",
        "Linear System Max Iterations = 5000",
        "linear system abort not converged = false",
    ]
    if json_data["maximum_passes"] > 1:
        solver_lines += sif_adaptive_mesh(json_data)

    return sif_block(f"Solver {ordinate}", solver_lines)


def get_vector_helmholtz(
    json_data: dict[str, Any],
    ordinate: str | int,
    angular_frequency: str | int,
    result_file: str | Path,
) -> str:
    """
    Returns a vector Helmholtz equation solver in sif file format.

    Args:
        json_data: all the model data produced by `export_elmer_json`
            See kqcircuits/simulations/export/elmer/elmer_solution.py for docstring of the parameters used from the json
        ordinate: solver ordinate
        angular_frequency: angular frequency of the solution
        result_file: filename for the result S-matrix

    Returns:
        vector Helmholtz in sif file format
    """
    use_av = json_data["use_av"]

    lumping_lines = [
        "! Model lumping",
        "  Constraint Modes Analysis = Logical True",
        "  Run Control Constraint Modes = Logical True",
        "  Constraint Modes Lumped = Logical True",
        "  Constraint Modes Fluxes = Logical True",
        "  Constraint Modes EM Wave = Logical True",
        "  Constraint Modes Fluxes Results = Logical True",
        "  Constraint Modes Fluxes Symmetric = Logical False",
        f'  Constraint Modes Fluxes Filename = File "{result_file}"',
    ]

    linear_system_lines = [
        "Linear System Symmetric = Logical False",
        "Steady State Convergence Tolerance = 1e-09",
    ]

    if use_av:
        if json_data["nested_iteration"]:
            linear_system_lines += [
                "! Activate nested iteration:",
                "!-----------------------------------------",
                "Linear System Block Mode = True",
                "Block Nested System = True",
                "Block Preconditioner = True",
                "Block Scaling = True",
                "! Specify the perturbation:",
                "!-----------------------------------------",
                "Linear System Preconditioning Damp Coefficient = 0.0",
                "Linear System Preconditioning Damp Coefficient im = -1.0",
                "Mass-proportional Damping = True",
                "! Linear system solver for the outer loop:",
                "!-----------------------------------------",
                'Outer: Linear System Solver = "Iterative"',
                f"Outer: Linear System Convergence Tolerance = {json_data['convergence_tolerance']}",
                "Outer: Linear System Normwise Backward Error = True",
                "Outer: Linear System Iterative Method = gcr",
                "Outer: Linear System GCR Restart =  100",
                "Outer: Linear System Residual Output =  1",
                "Outer: Linear System Max Iterations = 20",
                "Outer: Linear System Pseudo Complex = True",
                "! Linear system solver for the inner solution:",
                "!---------------------------------------------",
                "$blocktol = 5.0e-3",
                'block 11: Linear System Solver = "Iterative"',
                "block 11: Linear System Complex = True",
                "block 11: Linear System Scaling = True	",
                "block 11: Linear System Row Equilibration = False",
                "block 11: Linear System Preconditioning = Diagonal",
                "block 11: Linear System ILUT Tolerance = 5.0e-1",
                "block 11: Linear System Residual Output = 1",
                "block 11: Linear System Max Iterations = 100",
                "block 11: Linear System Iterative Method = GCR !BiCGStabl",
                "block 11: Linear System GCR Restart = 50",
                "block 11: BiCGstabl polynomial degree = 4",
                "block 11: Linear System Normwise Backward Error = False",
                "block 11: Linear System Convergence Tolerance = $blocktol",
            ]
        else:
            linear_system_lines += [
                "Linear system complex = Logical True",
                "Linear System Preconditioning Damp Coefficient im = -0.5",
                "Mass-proportional Damping = Logical True",
                'Linear System Solver = String "iterative"',
                'Linear System Iterative Method = String "GCR"',
                "Linear System GCR Restart = 200",
                "Linear System Row Equilibration = Logical True",
                "linear system normwise backward error = Logical True",
                "Linear System Preconditioning = ILUT",
                "Linear System ILUT Tolerance = 1.5e-1",
                f"Linear System Max Iterations = Integer {json_data['max_iterations']}",
                f"Linear System Convergence Tolerance = {json_data['convergence_tolerance']}",
                "linear system abort not converged = Logical False",
                "Linear System Residual Output = 1",
            ]

        linear_system_lines += [
            "linear system abort not converged = false",
            "Linear System Nullify Guess = Logical True",
        ]

    else:
        linear_system_lines += [
            "Linear system complex = Logical True",
            'Linear System Solver = String "Direct"',
            'Linear system direct method = "mumps"',
        ]

    solver_lines = [
        "exec solver = Always",
        'Equation = "VectorHelmholtz"',
        'Procedure = "VectorHelmholtz" "VectorHelmholtzSolver"',
        "" if use_av else "Variable = E[E re:1 E im:1]",
        f"Optimize Bandwidth = Logical {not use_av}",
        f"Use Gauss Law = Logical {use_av}",
        f"Apply Conservation of Charge = Logical {use_av}",
        "Calculate Energy Norm = Logical True",
        f"Angular Frequency = Real {angular_frequency}",
        f"Second Kind Basis = Logical {json_data['second_kind_basis']}",
        f"Quadratic Approximation = Logical {json_data['quadratic_approximation']}",
        *linear_system_lines,
        *lumping_lines,
    ]
    return sif_block(f"Solver {ordinate}", solver_lines)


def get_vector_helmholtz_calc_fields(ordinate: str | int, angular_frequency: str | float) -> str:
    solver_lines = [
        'Equation = "calcfields"',
        "Optimize Bandwidth = False",
        'Procedure = "VectorHelmholtz" "VectorHelmholtzCalcFields"',
        "Linear System Symmetric = False",
        'Field Variable =  String "E"',
        f"Angular Frequency = Real {angular_frequency}",
        "Calculate Elemental Fields = Logical True",
        "Calculate Magnetic Field Strength = Logical True",
        "Calculate Magnetic Flux Density = Logical True",
        "Calculate Poynting vector = Logical True",
        "Calculate Div of Poynting Vector = Logical False",
        "Calculate Electric field = Logical True",
        "Calculate Energy Functional = Logical True",
        "Steady State Convergence Tolerance = 1",
        'Linear System Solver = "Iterative"',
        "Linear System Preconditioning = None",
        "Linear System Residual Output = 0",
        "Linear System Max Iterations = 5000",
        "Linear System Iterative Method = CG",
        "Linear System Convergence Tolerance = 1.0e-9",
    ]
    return sif_block(f"Solver {ordinate}", solver_lines)


def get_electrostatics_solver(
    json_data: dict[str, Any],
    ordinate: str | int,
    capacitance_file: Path | str,
    c_matrix_output: bool = True,
    exec_solver: str = "Always",
) -> str:
    """
    Returns electrostatics solver in sif file format.

    Args:
        json_data: all the model data produced by `export_elmer_json`
            See kqcircuits/simulations/export/elmer/elmer_solution.py for docstring of the parameters used from the json
        ordinate: solver ordinate
        capacitance_file: name of the capacitance matrix data file
        c_matrix_output: Can be used to turn off capacitance matrix output

    Returns:
        electrostatics solver in sif file format
    """
    solver_lines = [
        f"Exec Solver = {exec_solver}",
        "Equation = Electro Statics",
        'Procedure = "StatElecSolveVec" "StatElecSolver"',
        "Variable = Potential",
        f"Calculate Capacitance Matrix = {c_matrix_output}",
        "Calculate Electric Field = True",
        "Calculate Elemental Fields = True",
        "Average Within Materials = False",
        f"Capacitance Matrix Filename = {capacitance_file}",
        "Nonlinear System Max Iterations = 1",
        "Nonlinear System Consistent Norm = True",
    ]

    solver_lines += sif_linsys(json_data)

    if json_data["maximum_passes"] > 1:
        solver_lines += sif_adaptive_mesh(json_data)

    return sif_block(f"Solver {ordinate}", solver_lines)


def get_circuit_solver(ordinate: str | int, p_element_order: int, exec_solver="Always") -> str:
    """
    Returns circuit solver in sif file format.

    Args:
        ordinate: solver ordinate
        p_element_order: p-element order
        exec_solver: Execute solver (options: 'Always', 'After Timestep', 'Never')

    Returns:
        circuit solver in sif file format
    """
    solver_lines = [
        f"Exec Solver = {exec_solver}",
        "Equation = Circuits",
        "Variable = X",
        "No Matrix = Logical True",
        'Procedure = "CircuitsAndDynamics" "CircuitsAndDynamicsHarmonic"',
        f"$pn={p_element_order}",
        "Element = p:$pn",
    ]
    return sif_block(f"Solver {ordinate}", solver_lines)


def get_circuit_output_solver(ordinate: str | int, exec_solver="Always") -> str:
    """
    Returns circuit output solver in sif file format.
    This solver writes the circuit variables.

    Args:
        ordinate: solver ordinate
        exec_solver: Execute solver (options: 'Always', 'After Timestep', 'Never')

    Returns:
        circuit output solver in sif file format
    """
    solver_lines = [
        f"Exec Solver = {exec_solver}",
        "Equation = Circuits Output",
        'Procedure = "CircuitsAndDynamics" "CircuitsOutput"',
    ]
    return sif_block(f"Solver {ordinate}", solver_lines)


def get_magneto_dynamics_2d_harmonic_solver(
    json_data: dict[str, Any],
    ordinate: str | int,
) -> str:
    """
    Returns magneto-dynamics 2d solver in sif file format.

    Args:
        json_data: all the model data produced by `export_elmer_json`
            See kqcircuits/simulations/export/elmer/elmer_solution.py for docstring of the parameters used from the json
        ordinate: solver ordinate

    Returns:
        magneto-dynamics 2d solver in sif file format
    """
    solver_lines = [
        'Equation = "Mag"',
        "Variable = A[A re:1 A im:1]",
        'Procedure = "MagnetoDynamics2D" "MagnetoDynamics2DHarmonic"',
        "Linear System Symmetric = True",
        "NonLinear System Relaxation Factor = 1",
        "Export Lagrange Multiplier = Logical True",
        'Linear System Solver = "Iterative"',
        "Linear System Iterative Method = BicgStabL",
        "Linear System Preconditioning = None",
        "Linear System Complex = Logical True",
        "Linear System Convergence Tolerance = 1.e-10",
        "Linear System Max Iterations = 3000",  # TODO inductanceSolution
        "Linear System Residual Output = 10",
        "Linear System Abort not Converged = False",
        "Linear System ILUT Tolerance=1e-8",
        "BicgStabL Polynomial Degree = 6",
        "Steady State Convergence Tolerance = 1e-05",
    ]
    if json_data["maximum_passes"] > 1:
        solver_lines += sif_adaptive_mesh(json_data)

    solver_lines += [
        "Vector Assembly = True",
        "Element = p:$pn",
    ]

    return sif_block(f"Solver {ordinate}", solver_lines)


def get_magneto_dynamics_calc_fields(ordinate: str | int, p_element_order: int) -> str:
    """
    Returns magneto-dynamics calculate fields solver in sif file format.

    Args:
        ordinate: solver ordinate
        p_element_order: p-element order

    Returns:
        magneto-dynamics calculate fields solver in sif file format
    """
    solver_lines = [
        "Exec Solver = Always",
        'Equation = "MGDynamicsCalc"',
        'Procedure = "MagnetoDynamics" "MagnetoDynamicsCalcFields"',
        "Linear System Symmetric = True",
        'Potential Variable = String "A"',
        "Skip Nodal Fields = True",
        "Calculate Current Density = Logical True",
        "Calculate Magnetic Vector Potential = Logical True",
        "Steady State Convergence Tolerance = 0",
        'Linear System Solver = "Iterative"',
        "Linear System Preconditioning = None",
        "Linear System Residual Output = 0",
        "Linear System Max Iterations = 5000",
        "Linear System Iterative Method = CG",
        "Linear System Convergence Tolerance = 1.0e-8",
        f"$pn={p_element_order}",
        "Element = p:$pn",
    ]
    return sif_block(f"Solver {ordinate}", solver_lines)


def get_result_output_solver(ordinate: str | int, output_file_name: str | Path, exec_solver: str = "Always") -> str:
    """
    Returns result output solver in sif file format.

    Args:
        ordinate: solver ordinate
        output_file_name: output file name
        exec_solver: Execute solver (options: 'Always', 'After Timestep', 'Never')

    Returns:
        result ouput solver in sif file format
    """
    solver_lines = [
        f"Exec Solver = {exec_solver}",
        'Equation = "ResultOutput"',
        'Procedure = "ResultOutputSolve" "ResultOutputSolver"',
        f'Output File Name = "{output_file_name}"',
        "Vtu format = Logical True",
        "Discontinuous Bodies = Logical True",
        "!Save All Meshes = Logical True",
        "Save Geometry Ids = Logical True",
    ]

    return sif_block(f"Solver {ordinate}", solver_lines)


def get_save_data_solver(
    ordinate: str | int,
    result_file: str = "results.dat",
    save_coordinates: list[list] | None = None,
    coordinate_file: str | None = None,
) -> str:
    """
    Returns save data solver in sif file format.

    Args:
        ordinate: solver ordinate
        result_file: data file name for results
        save_coordinates: list of coordinates to extract the field values at
        coordinate_file: If provided, writes the coordinates in an additional file instead of
                          the sif file.

    Returns:
        save data solver in sif file format
    """
    solver_lines = [
        "Exec Solver = After All",
        'Equation = "sv"',
        'Procedure = "SaveData" "SaveScalars"',
        f"Filename = {result_file}",
    ]
    if save_coordinates:
        if coordinate_file:
            np.savetxt(coordinate_file, np.array(save_coordinates))
            coords_str = f'Real \n   include "{coordinate_file}"'
        else:
            coords_str = " ".join([str(c) for clist in save_coordinates for c in clist])

        solver_lines += [
            f"Save Coordinates({len(save_coordinates)}, {len(save_coordinates[0])}) = {coords_str}",
            "Exact Coordinates = Logical True",
            "Parallel Reduce = Logical True",
        ]

    return sif_block(f"Solver {ordinate}", solver_lines)


def get_save_energy_solver(
    ordinate: str | int, energy_file: str, bodies: list[str], sheet_bodies: list[str] | None = None
) -> str:
    """
    Returns save energy solver in sif file format.

    Args:
        ordinate: solver ordinate
        energy_file: data file name for energy results
        bodies: body names for energy calculation
        sheet_bodies: boundary names for energy calculation in 3D simulation

    Returns:
        save energy solver in sif file format
    """
    solver_lines = [
        "Exec Solver = Always",
        'Equation = "SaveEnergy"',
        'Procedure = "SaveData" "SaveScalars"',
        f"Filename = {energy_file}",
        "Parallel Reduce = Logical True",
    ]
    # Add all target bodies to the solver
    for i, interface in enumerate(bodies, 1):
        solver_lines += [
            f"Variable {i} = Potential",
            f"Operator {i} = body diffusive energy",
            f"Mask Name {i} = {interface}",
            f"Coefficient {i} = Relative Permittivity",
        ]

    # Add sheet body energies using a custom energy solver separating the energy into normal and tangential components
    if sheet_bodies is not None:
        i = len(bodies) + 1
        for interface in sheet_bodies:
            solver_lines += [
                f"Variable {i} = {interface}_norm_component",
                f"Variable {i+1} = {interface}_tan_component",
            ]
            i += 2

    return sif_block(f"Solver {ordinate}", solver_lines)


def get_equation(ordinate: str | int, solver_ids: list[int], keywords: list[str] | None = None) -> str:
    """
    Returns equation in sif file format.

    Args:
        ordinate: equation ordinate
        solver_ids: list of active solvers (ordinates)
        keywords: keywords for equation

    Returns:
        equation in sif file format
    """
    keywords = [] if keywords is None else keywords
    equation_lines = [f'Active Solvers({len(solver_ids)}) = {" ".join([str(sid) for sid in solver_ids])}']
    return sif_block(f"Equation {ordinate}", equation_lines + keywords)


def sif_body(
    ordinate: str | int,
    target_bodies: list[str],
    equation: int,
    material: int,
    keywords: list[str] | None = None,
) -> str:
    """
    Returns body in sif file format.

    Args:
        ordinate: equation ordinate
        target_bodies: list of target bodies
        equation: active equations
        material: assigned material
        keywords: keywords for body

    Returns:
        body in sif file format
    """
    keywords = [] if keywords is None else keywords
    value_list = [
        f'Target Bodies({len(target_bodies)}) = $ {" ".join(target_bodies)}',
        f"Equation = {str(equation)}",
        f"Material = {str(material)}",
    ]
    return sif_block(f"Body {ordinate}", value_list + keywords)


def sif_component(
    ordinate: str | int, master_bodies: list[int], coil_type: str, keywords: list[str] | None = None
) -> str:
    """
    Returns component in sif file format.

    Args:
        ordinate: equation ordinate
        master_bodies: list of bodies
        coil_type: coil type (options: 'stranded', 'massive', 'foil')
        keywords: keywords for body

    Returns:
        component in sif file format
    """
    keywords = [] if keywords is None else keywords
    value_list = [
        f'Master Bodies({len(master_bodies)}) = $ {" ".join([str(body) for body in master_bodies])}',
        f"Coil Type = {str(coil_type)}",
    ]
    return sif_block(f"Component {ordinate}", value_list + keywords)


def sif_boundary_condition(ordinate: str | int, target_boundaries: list[str], conditions: list[str]) -> str:
    """
    Returns boundary condition in sif file format.

    Args:
        ordinate: equation ordinate
        target_boundaries: list of target boundaries
        conditions: keywords for boundary condition

    Returns:
        boundary condition in sif file format
    """
    value_list = [
        f'Target Boundaries({len(target_boundaries)}) = $ {" ".join(target_boundaries)}',
    ] + conditions

    return sif_block(f"Boundary Condition {ordinate}", value_list)


def produce_sif_files(json_data: dict[str, Any], path: Path) -> list[Path]:
    """
    Exports an elmer simulation model to the simulation path.

    Args:

        json_data: Complete parameter json for simulation
        path: Location where to output the simulation model

    Returns:

        sif_filepaths: Paths to exported sif files

    """
    path.mkdir(exist_ok=True, parents=True)
    sif_names = json_data["sif_names"]
    tool = json_data["tool"]
    if tool == "capacitance" and len(sif_names) != 1:
        logging.warning(f"Capacitance tool only supports 1 sif name, given {len(sif_names)}")

    sif_filepaths = []
    for ind, sif in enumerate(sif_names):
        if tool == "capacitance":
            content = sif_capacitance(json_data, path, vtu_name=path, angular_frequency=0, dim=3, with_zero=False)
        elif tool == "epr_3d":
            content = sif_epr_3d(json_data, path, vtu_name=path)
        elif tool == "wave_equation":
            freqs = json_data["frequency"]
            if len(freqs) != len(sif_names):
                logging.warning(
                    f"Number of sif names ({len(sif_names)}) does not match the number of frequencies ({len(freqs)})"
                )
            content = sif_wave_equation(json_data, path, frequency=freqs[ind])
        else:
            logging.warning(f"Unkown tool: {tool}. No sif file created")
            return []

        sif_filepath = path.joinpath(f"{sif}.sif")
        with open(sif_filepath, "w", encoding="utf-8") as f:
            f.write(content)
        sif_filepaths.append(sif_filepath)

    return sif_filepaths


def get_layer_list(json_data: dict[str, Any], mesh_names: list[str]) -> list[str]:
    """
    Returns layer list included in mesh_names.

    Args:
        json_data: all the model data produced by `export_elmer_json`
        mesh_names: list of physical group names from the mesh.names file

    Returns:
        list of model layers
    """
    layer_names = {apply_elmer_layer_prefix(k) for k in json_data["layers"]}
    return [n for n in mesh_names if n in layer_names]


def get_permittivities(json_data: dict[str, Any], with_zero: bool, mesh_names: list[str]) -> list[float]:
    """
    Returns permittivities of bodies.

    If permittivity for the body with name "abcd_1_extra" is not found, check the available permittivities in json
    and if a key corresponding to beginning of the searched permittivity is found use that.

    If such hit is also not found default to 1.0

    Args:
        json_data: all the model data produced by `export_elmer_json`
        with_zero: without dielectrics if true
        mesh_names: list of physical group names from the mesh.names file

    Returns:
        list of body permittivities
    """
    if with_zero:
        return [1.0 for _ in mesh_names]
    layers = get_elmer_layers(json_data["layers"])
    material_dict = json_data["material_dict"]
    return [material_dict.get(layers.get(n, {}).get("material"), {}).get("permittivity", 1.0) for n in mesh_names]


def sif_placeholder_boundaries(groups: list[str], n_boundaries: int) -> str:
    boundary_conditions = ""
    for i, s in enumerate(groups, 1):
        boundary_conditions += sif_boundary_condition(
            ordinate=i + n_boundaries,
            target_boundaries=[s],
            conditions=[
                "! This BC does not do anything, but",
                "! MMG does not conserve GeometryIDs if there is no BC defined.",
            ],
        )
    return boundary_conditions


def sif_epr_3d(json_data: dict[str, Any], folder_path: Path, vtu_name: str | Path) -> str:
    """
    Returns 3D EPR simulation sif

    This solution assumes that signals and grounds are 3d bodies
    Also mesh boundaries are assumed to contain only tls layers and no ports

    Args:
        json_data: all the model data produced by `export_elmer_json`
            See kqcircuits/simulations/export/elmer/elmer_solution.py for docstring of the parameters used from the json
        folder_path: folder path of the model files
        vtu_name: name of the paraview file

    Returns:
        Elmer solver input file for 3D EPR simulation
    """

    voltage_exc = json_data["voltage_excitations"]
    c_matrix_output = not bool(voltage_exc)
    mesh_path = Path(json_data["mesh_name"])

    header = sif_common_header(
        json_data,
        folder_path,
        mesh_path,
        angular_frequency=0,
        dim=3,
        constraint_modes_analysis=c_matrix_output,
        output_file=(f"{folder_path}.result" if json_data["save_elmer_data"] else None),
    )
    constants = sif_block("Constants", [f"Permittivity Of Vacuum = {epsilon_0}"])

    solvers = get_electrostatics_solver(
        json_data,
        ordinate=1,
        capacitance_file=folder_path / "capacitance.dat",
        c_matrix_output=c_matrix_output,
    )
    solvers += get_result_output_solver(
        ordinate=2,
        output_file_name=vtu_name,
        exec_solver="Always" if json_data["vtu_output"] else "Never",
    )
    equations = get_equation(
        ordinate=1,
        solver_ids=[1],
    )

    body_names, boundary_names = read_mesh_names(mesh_path)
    mesh_boundaries = get_layer_list(json_data, boundary_names)

    metal_layers = {n: l for n, l in get_elmer_layers(get_metal_layers(json_data["layers"])).items() if n in body_names}
    mesh_bodies = get_layer_list(json_data, [n for n in body_names if n not in metal_layers])

    permittivity_list = get_permittivities(json_data, False, mesh_bodies)

    # Solver(s) with masks for saving energy
    solver_lines = [
        "Exec Solver = " + ("Always" if len(mesh_boundaries) > 0 else "Never"),
        'Equation = "SaveBoundaryEnergy"',
        'Procedure = "SaveBoundaryEnergy" "SaveBoundaryEnergyComponents"',
    ]
    solvers += sif_block("Solver 3", solver_lines)

    solvers += get_save_energy_solver(
        ordinate=4,
        energy_file="energy.dat",
        bodies=mesh_bodies,
        sheet_bodies=mesh_boundaries,
    )

    bodies = ""
    materials = ""
    body_forces = ""
    n_bodies = 0
    for i, (body, perm) in enumerate(zip(mesh_bodies, permittivity_list), 1):
        bodies += sif_body(
            ordinate=i, target_bodies=[body], equation=1, material=i, keywords=[f"{body} = Logical True"]
        )
        materials += sif_block(f"Material {i}", [f"Relative Permittivity = {perm}"])
        n_bodies += 1

    # add material for pec
    pec_material_index = n_bodies + 1
    materials += sif_block(f"Material {pec_material_index}", ["Relative Permittivity = 1.0"])

    n_capacitance_bodies = 0
    n_body_forces = 0
    excitation_str = "Capacitance Body = integer" if c_matrix_output else "Potential = Real"
    excitations = {d["excitation"] for n, d in metal_layers.items()}
    if None in excitations:
        raise RuntimeError("Floating excitation is not supported. Use only integer excitation values.")
    for excitation in sorted(excitations):
        excitation_bodies = [n for n, d in metal_layers.items() if d["excitation"] == excitation]

        n_bodies += 1
        n_body_forces += 1
        bodies += sif_body(
            ordinate=n_bodies,
            target_bodies=excitation_bodies,
            equation=1,
            material=pec_material_index,
            keywords=[f"Body Force = {n_body_forces}"],
        )
        if excitation == 0:  # ground
            body_forces += sif_block(f"Body Force {n_body_forces}", [f"{excitation_str} 0"])
        else:  # signal
            n_capacitance_bodies = n_capacitance_bodies + 1
            # If too few excitations given in voltage_exc, repeat the last voltage
            condition = voltage_exc[min(excitation, len(voltage_exc)) - 1] if voltage_exc else n_capacitance_bodies
            body_forces += sif_block(f"Body Force {n_body_forces}", [f"{excitation_str} {condition}"])

    boundary_conditions = ""
    n_bcs = 1

    boundary_conditions += sif_boundary_condition(
        ordinate=n_bcs,
        target_boundaries=["domain_boundary"],
        conditions=[
            "Electric Infinity BC = Logical True" if json_data.get("electric_infinity_bc", False) else "! Placeholder"
        ],
    )

    # tls bcs
    for s in mesh_boundaries:
        n_bcs += 1
        boundary_conditions += sif_boundary_condition(
            ordinate=n_bcs,
            target_boundaries=[s],
            conditions=[f'Boundary Energy Name = String "{s}"'],
        )

    return header + constants + solvers + equations + materials + bodies + body_forces + boundary_conditions


def sif_capacitance(
    json_data: dict[str, Any],
    folder_path: Path,
    vtu_name: str | Path,
    angular_frequency: float,
    dim: int,
    with_zero: bool = False,
) -> str:
    """
    Returns the capacitance solver sif. If `with_zero` is true then all the permittivities are set to 1.0.
    It is used in computing capacitances without dielectrics (so called 'capacitance0')

    Args:
        json_data: all the model data produced by `export_elmer_json`
            See kqcircuits/simulations/export/elmer/elmer_solution.py for docstring of the parameters used from the json
        folder_path: folder path of the model files
        vtu_name: name of the paraview file
        angular_frequency: angular frequency of the solution
        dim: model dimensionality (2 or 3)
        with_zero: without dielectrics if true

    Returns:
        elmer solver input file for capacitance
    """

    name = "capacitance0" if with_zero else "capacitance"
    mesh_path = Path(json_data["mesh_name"])

    voltage_exc = json_data.get("voltage_excitations", None)
    c_matrix_output = not bool(voltage_exc)

    header = sif_common_header(
        json_data,
        folder_path,
        mesh_path,
        angular_frequency=angular_frequency,
        dim=dim,
        constraint_modes_analysis=c_matrix_output,
        output_file=(f"{folder_path}.result" if json_data["save_elmer_data"] else None),
    )

    constants = sif_block("Constants", [f"Permittivity Of Vacuum = {epsilon_0}"])

    solvers = get_electrostatics_solver(
        json_data, ordinate=1, capacitance_file=folder_path / f"{name}.dat", c_matrix_output=c_matrix_output
    )

    solvers += get_result_output_solver(
        ordinate=2,
        output_file_name=vtu_name,
        exec_solver="Always" if json_data["vtu_output"] else "Never",
    )

    equations = get_equation(
        ordinate=1,
        solver_ids=[1],
        keywords=["Calculate Electric Energy = True"] if dim == 2 else [],
    )

    body_names, boundary_names = read_mesh_names(mesh_path)
    body_list = get_layer_list(json_data, body_names)
    permittivity_list = get_permittivities(json_data, with_zero, body_list)

    if json_data.get("integrate_energies", False) and not with_zero:  # no EPR for inductance
        solvers += get_save_energy_solver(ordinate=3, energy_file="energy.dat", bodies=body_list)

    bodies = ""
    materials = ""
    for i, (body, perm) in enumerate(zip(body_list, permittivity_list), 1):
        bodies += sif_body(
            ordinate=i, target_bodies=[body], equation=1, material=i, keywords=[f"{body} = Logical True"]
        )

        materials += sif_block(f"Material {i}", [f"Relative Permittivity = {perm}"])

    # Boundary conditions
    n_capacitance_bodies = 0
    boundary_conditions = ""
    n_boundaries = 0
    excitation_names = [n for n in boundary_names if n.startswith("excitation_") and n.endswith("_boundary")]
    if "excitation_None_boundary" in excitation_names:
        raise RuntimeError("Floating excitation is not supported. Use only integer excitation values.")
    excitations = sorted([(int(n[11:-9]), n) for n in excitation_names])
    for excitation, excitation_name in excitations:
        if excitation == 0:  # ground
            condition = "Potential = 0.0"
        elif voltage_exc:  # signal with specified voltage
            condition = f"Potential = {voltage_exc[min(excitation, len(voltage_exc)) - 1]}"
        else:  # signal for capacitance simulation
            n_capacitance_bodies += 1
            condition = f"Capacitance Body = {n_capacitance_bodies}"

        n_boundaries += 1
        boundary_conditions += sif_boundary_condition(n_boundaries, [excitation_name], [condition])

    outer_bc_names = []
    if dim == 2:
        bc_dict = json_data.get("boundary_conditions")
        for bc in ["xmin", "xmax", "ymin", "ymax"]:
            bc_name = f"{bc}_boundary"

            conditions = ["Electric Infinity BC = Logical True"] if json_data["electric_infinity_bc"] else []
            if bc_dict is not None:
                potential = bc_dict.get(bc, {}).get("potential")
                if potential is not None:
                    conditions += [f"Potential = {potential}"]

            if conditions:
                n_boundaries += 1
                boundary_conditions += sif_boundary_condition(
                    ordinate=n_boundaries, target_boundaries=[bc_name], conditions=conditions
                )
                outer_bc_names.append(bc_name)
    else:
        if json_data["electric_infinity_bc"]:
            n_boundaries += 1
            boundary_conditions += sif_boundary_condition(
                ordinate=n_boundaries,
                target_boundaries=["domain_boundary"],
                conditions=["Electric Infinity BC = Logical True"],
            )
            outer_bc_names.append("domain_boundary")

    # Add place-holder boundaries (if additional physical groups are given)
    other_groups = [n for n in body_names + boundary_names if n not in body_list + excitation_names + outer_bc_names]
    boundary_conditions += sif_placeholder_boundaries(other_groups, n_boundaries)
    n_boundaries += len(other_groups)

    return header + constants + solvers + equations + materials + bodies + boundary_conditions


def sif_inductance(
    json_data: dict[str, Any], folder_path: Path, angular_frequency: float | str, circuit_definitions_file: str
) -> str:
    """
    Returns inductance sif file content for a cross section model
    in string format. The sif file corresponds to the mesh produced by
    `produce_cross_section_mesh`

    TODO: Allow multiple traces and for each trace multiple metal layers

    Args:
        json_data: all the model data produced by `export_elmer_json`
        folder_path: folder path for the sif file
        angular_frequency: angular frequency of the solution
        circuit_definitions_file: file name for circuit definitions

    Returns:
        elmer solver input file for inductance computation
    """
    mesh_path = Path(json_data["mesh_name"])
    header = sif_common_header(
        json_data,
        folder_path,
        mesh_path,
        angular_frequency,
        circuit_definitions_file,
        dim=2,
        output_file=("inductance.result" if json_data["save_elmer_data"] else None),
    )
    equations = get_equation(ordinate=1, solver_ids=[1, 2, 3])

    solvers = get_circuit_solver(ordinate=1, p_element_order=json_data["p_element_order"], exec_solver="Always")

    solvers += get_magneto_dynamics_2d_harmonic_solver(
        json_data,
        ordinate=2,
    )

    solvers += get_magneto_dynamics_calc_fields(ordinate=3, p_element_order=json_data["p_element_order"])

    solvers += get_result_output_solver(
        ordinate=4,
        output_file_name="inductance",
        exec_solver="Always" if json_data["vtu_output"] else "Never",
    )

    solvers += get_circuit_output_solver(ordinate=5, exec_solver="Always")
    solvers += get_save_data_solver(ordinate=6, result_file="inductance.dat")

    # Divide layers into different materials
    body_names, boundary_names = read_mesh_names(mesh_path)
    body_list = get_layer_list(json_data, body_names)
    metal_layers = get_elmer_layers(get_metal_layers(json_data["layers"]))
    non_metal_bodies = list(set(body_list) - set(metal_layers))

    bodies = sif_body(
        ordinate=1,
        target_bodies=non_metal_bodies,
        equation=1,
        material=1,
        keywords=["Body Force = 1 ! No effect. Set to suppress warnings"],
    )

    materials = sif_block(
        "Material 1",
        [
            "Relative Permeability = 1",
            "Relative Permittivity = 1 ! No effect. Set to suppress warnings",
            "Electric Conductivity = 1",
        ],
    )

    n_bodies = 1
    master_bodies = []
    max_excitation = 0
    material_dict = json_data["material_dict"]
    for name, data in metal_layers.items():
        if name not in body_list:
            continue

        n_bodies += 1
        bodies += sif_body(ordinate=n_bodies, target_bodies=[name], equation=1, material=n_bodies)

        excitation = data["excitation"]
        if excitation is None:
            raise RuntimeError("Floating excitation is not supported. Use only integer excitation values.")
        max_excitation = max(max_excitation, excitation)
        if excitation == 1:
            master_bodies.append(n_bodies)  # apply only the first signal to the master bodies

        lambda_l = material_dict.get(data.get("material"), {}).get("london_penetration_depth", 0)
        if lambda_l > 0:
            opt_params = [
                "Electric Conductivity = 0",
                f"$ lambda_l = {lambda_l}",
                "$ mu_0 = 4e-7*pi",
                "London Lambda = Real $ mu_0 * lambda_l^2",
            ]
        else:
            opt_params = ["Electric Conductivity = 1e10"]

        materials += sif_block(
            f"Material {n_bodies}",
            [
                "Relative Permeability = 1  ! No effect. Set to suppress warnings",
                "Relative Permittivity = 1000",
                *opt_params,
            ],
        )

    if max_excitation == 0:
        logging.warning("No excitations found in inductance simulation!")
    elif max_excitation > 1:
        logging.warning(f"Multiple excitations ({max_excitation}) found in inductance simulation!")
        logging.warning("Treating excitation 1 as signal and other excitations as grounds.")

    london_param = ["London Equations = Logical True"] if use_london_equations(json_data) else []
    components = sif_component(
        ordinate=1,
        master_bodies=master_bodies,
        coil_type="Massive",
        keywords=london_param,
    )

    body_force = sif_block("Body Force 1", ['Name = "Circuit"', "testsource Re = Real 1.0", "testsource Im = Real 0.0"])

    # Add place-holder boundaries (if additional physical groups are given)
    other_groups = [n for n in body_names + boundary_names if n not in body_list]
    boundary_conditions = "" + sif_placeholder_boundaries(other_groups, 0)

    return header + equations + solvers + materials + bodies + components + body_force + boundary_conditions


def sif_circuit_definitions(json_data: dict[str, Any]) -> str:
    """
    Returns content of circuit definitions in string format.

    Args:
        json_data: all the model data produced by `export_elmer_json`
    """
    res = "$ Circuits = 1\n"

    # Define variable count and initialize circuit matrices.
    use_london_eq = use_london_equations(json_data)

    n_equations = 4 + int(use_london_eq)
    res += f"\n$ C.1.perm = zeros({n_equations})\n"
    for i in range(n_equations):
        res += f"$ C.1.perm({i % (n_equations - 1) + 1 if i > 0 and n_equations == 4 else i}) = {i}\n"

    res += f"\n$ C.1.variables = {n_equations}\n"
    for n in ["A", "B", "Mre", "Mim"]:
        res += f"$ C.1.{n} = zeros({n_equations},{n_equations})\n"

    # Define variables
    res += "\n"
    var_names = ["i_testsource", "v_testsource", "i_component(1)", "v_component(1)"]
    if use_london_eq:
        # If London equations are activated, phi_component(1) takes the role and place of v_component(1).
        # Then v_component(1) becomes nothing but a conventional circuit variable and the user has to write d_t phi = v,
        # if he wishes to drive the SC with voltage.
        var_names.insert(3, "phi_component(1)")
    for i, var_name in enumerate(var_names):
        res += f'$ C.1.name.{i + 1} = "{var_name}"\n'

    # 1st equation
    res += f"\n$ C.1.B(0,{n_equations - 4}) = 1\n"
    res += '$ C.1.source.1 = "testsource"\n'

    # 2nd equation: Voltage relations (v_testsource + v_component(1) = 0)
    res += "\n$ C.1.B(1,1) = 1\n"
    res += f"$ C.1.B(1,{n_equations - 1}) = 1\n"

    # 3rd equation: Current relations (i_testsource - i_component(1) = 0)
    res += "\n$ C.1.B(2,0) = 1\n"
    res += "$ C.1.B(2,2) = -1\n"

    # 4th equation: (d_t phi_component(1) - v_component(1) = 0)
    if use_london_eq:
        res += "\n$ C.1.A(4,3) = 1\n"
        res += "$ C.1.B(4,4) = -1\n"

    # 1 component equation, linking phi and i of the component 1, written by elmer at the row 4
    # (beta a, phi') + phi_component(1) (beta grad phi_0, grad phi') = i_component(1)
    return res


def get_port_from_boundary_physical_names(ports, name):
    # TODO remove deprecated
    for port in ports:
        logging.info(f"{name} {port['physical_names']}")
        if name in [t[1] for t in port["physical_names"]]:
            return port
    return None


def _get_smatrix_filename(name: str, f: float | int) -> str:
    return f'SMatrix_{name}_f{str(float(f)).replace(".", "_")}.dat'


def _get_f_from_smatrix_filename(filename: str | Path, name: str) -> float:
    return float(str(filename).removeprefix(f"SMatrix_{name}_f").removesuffix(".dat").replace("_", "."))


def sif_wave_equation(
    json_data: dict[str, Any],
    folder_path: Path,
    frequency: float = 10,
) -> str:
    """
    Returns the wave equation solver sif.

    Args:
        json_data: All the model data produced by `export_elmer_json`
            See kqcircuits/simulations/export/elmer/elmer_solution.py for docstring of the parameters used from the json
        folder_path: Folder path of the model files
        frequency: Frequency used in simulation in GHz

    Returns:
        elmer solver input file for wave equation
    """

    london_penetration_depth = json_data["london_penetration_depth"]
    conductivity = json_data["conductivity"]
    use_av = json_data["use_av"]
    metal_heights = [data["thickness"] for name, data in json_data["layers"].items() if "signal" in name]
    if len(set(metal_heights)) > 1:
        logging.warning(
            "Simulation contains multiple metal layers with varying thicknesses, This is not supported with"
            f"elmer wave-equation tool. Using thickness {metal_heights[0]}um for all ports"
        )
    metal_height = metal_heights[0]

    smatrix_filename = _get_smatrix_filename(json_data["name"], frequency)
    uniq_name = smatrix_filename.removeprefix("SMatrix_").removesuffix(".dat")

    mesh_path = Path(json_data["mesh_name"])
    header = sif_common_header(
        json_data,
        folder_path,
        mesh_path,
        discontinuous_boundary=(use_av and metal_height == 0),
        output_file=(f"{uniq_name}.result" if json_data["save_elmer_data"] else None),
    )
    constants = sif_block("Constants", [f"Permittivity Of Vacuum = {epsilon_0}"])

    # Bodies and materials
    body_names, boundary_names = read_mesh_names(mesh_path)
    mesh_names = body_names + boundary_names
    body_list = get_layer_list(json_data, body_names)
    metal_layers = get_elmer_layers(get_metal_layers(json_data["layers"]))
    permittivity_list = get_permittivities(json_data, False, body_list)

    bodies = ""
    materials = ""
    betas = []

    for i, (body, perm) in enumerate(zip(body_list, permittivity_list), 1):
        material_parameters = [f'Name = "{body}"']
        if body in metal_layers and use_av:
            bodies += sif_block(f"Body {i}", [f"Target Bodies(1) = $ {body}", f"Material = {i}"])
        else:
            bodies += sif_body(ordinate=i, target_bodies=[body], equation=1, material=i)
            material_parameters += [f"Relative Permittivity = {perm}"]

        materials += sif_block(f"Material {i}", material_parameters)
        if body not in metal_layers:
            betas.append(f"beta_{body} = w*sqrt({perm}*eps0*mu0)")

    n_bodies = len(body_list)

    # Matc block
    matc_list = [
        f"f0 = {1e9*frequency}",
        "w=2*pi*(f0)",
        "mu0=4e-7*pi",
        "eps0 = 8.854e-12",
    ]

    def _port_polygon_area_3d(polygon: list[list[float]]) -> float:
        """Assumes that the polygon is rectangle with the listed coordinates in order"""
        len1 = sum((p1 - p2) * (p1 - p2) for p1, p2 in zip(polygon[0], polygon[1]))
        len2 = sum((p1 - p2) * (p1 - p2) for p1, p2 in zip(polygon[0], polygon[-1]))
        return (len1 * len2) ** 0.5

    if london_penetration_depth != 0:
        matc_list += [
            f"lambda_l = {london_penetration_depth}",
            "sigma = 1/(w*mu0*lambda_l^2)",
        ]
    if use_av:
        # TODO generalise for other shapes and ports having different sizes
        port_area = _port_polygon_area_3d(json_data["ports"][0]["polygon"]) * 1e-12
        # Use 200nm thickness for impedance calculation when using sheet metal
        signal_height = 200e-9 if metal_height == 0 else metal_height
        # TODO how to get trace width "a" without taking it from "parameters"
        signal_area = signal_height * json_data["parameters"].get("a", 10) * 1e-12
        matc_list += [
            "V0 = 1",
            "Z0 = 50",
            f"port_area = {port_area}",
            f"signal_area = {signal_area}",
        ]
    else:
        matc_list += [*betas]

    if conductivity != 0:
        matc_list += [f"film_conductivity = {conductivity}"]

    matc_blocks = sif_matc_block(matc_list)

    # Solvers & Equations
    result_file = folder_path / smatrix_filename
    solvers = ""
    solver_ordinate = 1
    if not use_av:
        solvers += get_port_solver(
            json_data,
            ordinate=solver_ordinate,
        )
        solver_ordinate += 1

    solvers += get_vector_helmholtz(
        json_data,
        ordinate=solver_ordinate,
        angular_frequency="$ w",
        result_file=result_file,
    )
    solvers += get_vector_helmholtz_calc_fields(ordinate=solver_ordinate + 1, angular_frequency="$ w")

    solvers += get_result_output_solver(
        ordinate=solver_ordinate + 2,
        output_file_name=uniq_name,
        exec_solver="Always" if json_data["vtu_output"] else "Never",
    )

    # Equations
    equations = get_equation(ordinate=1, solver_ids=[solver_ordinate, solver_ordinate + 1])
    if not use_av:
        equations += get_equation(ordinate=2, solver_ids=[1])

    # Boundary conditions
    boundary_conditions = ""
    sc_grounds = ["excitation_0_boundary"]
    pec_box = "domain_boundary"
    grounds = sc_grounds + [pec_box]

    if use_av:
        pec_conditions = ["AV re {e} = 0", "AV im {e} = 0", "AV re = Real 0", "AV im = Real 0"]
        if london_penetration_depth > 0:
            sc_metal_conditions = [
                "Layer Thickness = $ lambda_l",
                "Layer Electric Conductivity Im = $ sigma",
                "Apply Conservation of Charge = Logical True",
            ]
        elif conductivity > 0:
            sc_metal_conditions = [
                "Good Conductor BC = True",
                "Layer Relative Reluctivity = Real 1.0",
                "Layer Electric Conductivity = $ film_conductivity",
                "Apply Conservation of Charge = Logical True",
            ]
        else:
            logging.warning("AV without cond or london penetration depth not supported")
            sc_metal_conditions = ["AV re {e} = 0", "AV im {e} = 0", "AV re = Real 0", "AV im = Real 0"]
    else:
        pec_conditions = ["Potential = 0", "E re {e} = 0", "E im {e} = 0"]
        if london_penetration_depth > 0:
            sc_metal_conditions = ["Layer Thickness = $ lambda_l", "Layer Electric Conductivity Im = $ sigma"]
        else:
            sc_metal_conditions = ["E re {e} = 0", "E im {e} = 0"]

    boundary_conditions += sif_boundary_condition(ordinate=1, target_boundaries=[pec_box], conditions=pec_conditions)
    n_boundaries = 1

    sc_ground_conditions = sc_metal_conditions + ([] if use_av else ["Potential = 0"])
    sc_signal_conditions = sc_metal_conditions + ([] if use_av else ["Potential = 1"])

    boundary_conditions += sif_boundary_condition(
        ordinate=2, target_boundaries=sc_grounds, conditions=sc_ground_conditions
    )
    n_boundaries += 1

    signal_bc_inds = []
    signals = [
        n for n in boundary_names if n.startswith("excitation_") and n.endswith("_boundary") and n not in sc_grounds
    ]
    for i, s in enumerate(signals, 1):
        signal_bc_inds.append(i + n_boundaries)
        boundary_conditions += sif_boundary_condition(
            ordinate=i + n_boundaries, target_boundaries=[s], conditions=sc_signal_conditions
        )
    n_boundaries += len(signals)

    # Port boundaries
    body_ids: dict[str, Any] = {b: None for b in body_list}
    constraint_ind = 1  # for enumerating edge port constraint modes in av
    for i, port in enumerate(json_data["ports"], 1):
        port_name = f'port_{port["number"]}'
        if port["type"] == "EdgePort":
            # The edge port is split by dielectric materials
            port_parts = [
                (n, apply_elmer_layer_prefix(n[len(port_name + "_") :]))
                for n in boundary_names
                if n.startswith(port_name + "_")
            ]
        else:
            # The material is assumed to be homogeneous throughout the internal port, so any material can be used.
            # We pick 'vacuum' by default if it exists.
            any_material = "vacuum" if "vacuum" in body_list else body_list[0]
            port_parts = [(port_name, any_material)] if port_name in boundary_names else []

        port_part_bc_indices = {}
        for name, mat in port_parts:
            n_boundaries += 1
            port_part_bc_indices[mat] = n_boundaries
            # Add boundary condition for the port
            if use_av:
                conditions = ["AV re {e} = 0", "AV im {e} = 0"]
            else:
                # Add body for the port equation, if it doesn't exist yet
                if mat not in metal_layers:
                    if body_ids[mat] is None:
                        n_bodies += 1
                        body_ids[mat] = n_bodies
                        bodies += sif_body(
                            ordinate=body_ids[mat],
                            target_bodies=[],
                            equation=2,
                            material=body_list.index(mat) + 1,
                        )

                    conditions = [f"Body Id = {body_ids[mat]}"]
                    conditions += [
                        f'Constraint Mode = Integer {port["number"]}',
                        "TEM Potential im = variable potential",
                        f'  real matc "2*beta_{mat}*tx"',
                        f"electric robin coefficient im = real $ -beta_{mat}",
                    ]
                else:
                    conditions = [
                        "E re {e} = 0",
                        "E im {e} = 0",
                    ]
            boundary_conditions += sif_boundary_condition(
                ordinate=n_boundaries, target_boundaries=[name], conditions=conditions
            )

        # 1D excitation for Av-solver, This will now totally skip internal ports
        if use_av and port["type"] == "EdgePort":
            vacuum_bc_ind = port_part_bc_indices["vacuum"]

            if metal_height == 0:
                signal_port_bc_inds = signal_bc_inds
                signal_intersection_bc_inds = [vacuum_bc_ind]
                material_inds = [1, 2]  # material indices hardcoded for now
            else:
                if "silicon" in json_data["material_dict"]:
                    substrate_bc_ind = port_part_bc_indices["silicon"]
                else:
                    first_material = list(json_data["material_dict"].keys())[0]
                    logging.warning(
                        '"silicon" not found in material dict, '
                        f"using for AV solver intersection ports instead {first_material}"
                    )
                    substrate_bc_ind = port_part_bc_indices[first_material]

                signal_port_bc_inds = [port_part_bc_indices["signal"]]
                signal_intersection_bc_inds = [vacuum_bc_ind, substrate_bc_ind]
                material_inds = [1, 3]

            for signal_ind in signal_port_bc_inds:
                for signal_edge_bc_ind, material_ind in zip(signal_intersection_bc_inds, material_inds):
                    conditions = [
                        f"Constraint Mode = Integer {constraint_ind}",
                        f"Intersection BC(2) = {signal_ind} {signal_edge_bc_ind}",
                        "Layer Thickness = Real $ lambda_l",
                        "Electric Transfer Coefficient = Real $ 1.0/(Z0*signal_area)",
                        "Incident Voltage = Real $ V0",
                        f"Material = Integer {material_ind}",
                    ]
                    n_boundaries += 1
                    boundary_conditions += sif_block(f"Boundary Condition {n_boundaries}", conditions)

            constraint_ind += 1

    # Add place-holder boundaries (if additional physical groups are given)
    other_groups = [n for n in mesh_names if n not in body_list + grounds + signals and not n.startswith("port_")]
    for i, s in enumerate(other_groups, 1):
        boundary_conditions += sif_boundary_condition(
            ordinate=i + n_boundaries,
            target_boundaries=[s],
            conditions=["! Default boundary for full wave (PEC)", "E re {e} = 0", "E im {e} = 0", "Potential = 1"],
        )
    n_boundaries += len(other_groups)

    return header + constants + matc_blocks + solvers + equations + materials + bodies + boundary_conditions


def read_result_smatrix(s_matrix_filename: str | Path, path: Path | None = None, polar_form: bool = True) -> np.ndarray:
    """
    Read Elmer Smatrix output and transform the entries to polar format

    Args:
        s_matrix_filename: Relative Smatrix path
        path: Optional basename for the path if `s_matrix_filename` does not exist
                     Defaults to None.
        polar_form: Transform the entries to polar form. Defaults to True.

    Returns:
        np.array: Smatrix as 2D numpy array
    """
    if not Path(s_matrix_filename).exists() and path is not None:
        s_matrix_filename = path.joinpath(s_matrix_filename)

    with open(s_matrix_filename, "r", encoding="utf-8") as file:
        reader = csv.reader(file, delimiter=" ", skipinitialspace=True, quoting=csv.QUOTE_NONNUMERIC)
        s_matrix_re = np.array([[x for x in row if isinstance(x, float)] for row in reader])

    with open(str(s_matrix_filename) + "_im", "r", encoding="utf-8") as file:
        reader = csv.reader(file, delimiter=" ", skipinitialspace=True, quoting=csv.QUOTE_NONNUMERIC)
        s_matrix_im = np.array([[x for x in row if isinstance(x, float)] for row in reader])

    if polar_form:
        s_matrix_mag = np.hypot(s_matrix_re, s_matrix_im)
        s_matrix_angle = np.degrees(np.arctan2(s_matrix_im, s_matrix_re))

    smatrix_full = np.zeros(s_matrix_re.shape + (2,))
    for i1, i2 in np.ndindex(s_matrix_re.shape):
        if polar_form:
            smatrix_full[i1, i2, :] = np.array((s_matrix_mag[i1, i2], s_matrix_angle[i1, i2]))
        else:
            smatrix_full[i1, i2, :] = np.array((s_matrix_re[i1, i2], s_matrix_im[i1, i2]))

    return smatrix_full


def read_elmer_results(result_file: Path | str):
    """
    Args:
        result_file: path to the results including the filename and extension

    Returns:
        DataFrame with the results
    """
    try:
        data = np.loadtxt(result_file, ndmin=2)

        col_names = []
        with open(str(result_file) + ".names", encoding="utf-8") as fp:
            reached_data = False
            for line in fp:
                if not reached_data and "Variables in columns of matrix:" in line:
                    reached_data = True
                    continue

                if reached_data:
                    col_names.append(line.strip())

        return pd.DataFrame(data, columns=col_names)

    except FileNotFoundError:
        logging.warning(f"Elmer result file not found in {result_file}")
        return None


def get_energy_integrals(path: Path | str) -> dict:
    """
    Return electric energy integrals

    Args:
        path: folder path of the model result files

    Returns:
        energies formatted as dictionary
    """

    def _rename_energy_key(e_name: str) -> str:
        """Rename energy dictionary keys from Elmer results to correspond to the Ansys result format"""
        # Change 2-component energies to same naming as used in Ansys
        if e_name.endswith("_norm_component"):
            e_name = "Ez" + e_name.removesuffix("_norm_component").removeprefix("E")
        elif e_name.endswith("_tan_component"):
            e_name = "Exy" + e_name.removesuffix("_tan_component").removeprefix("E")

        # Elmer forces all keys to be lowercase so let's capitalise the interface abbreviations
        # to correspond to Ansys naming
        for k in ("MA", "MS", "SA"):
            elmer_int_key = "_layer" + k.lower()
            if elmer_int_key in e_name:
                e_name = e_name.replace(elmer_int_key, "_layer" + k)
                break

        return e_name

    res_df = read_elmer_results(Path(path) / "energy.dat")

    edict = {}
    for col, data_series in res_df.items():

        matches = [match.group(1) for match in re.finditer("diffusive energy: potential mask ([a-z_0-9]+)", col)]

        col_new = matches[0] if matches else col.strip().partition(": ")[2]
        # Discard any Elmer default results starting with "res: "
        if col_new and not col_new.startswith("res: "):
            col_new = _rename_energy_key(f"E_{col_new.removeprefix(MESH_LAYER_PREFIX)}")
            edict[col_new] = data_series.values.squeeze().tolist()

    return edict


def write_snp_file(
    filename: str | Path,
    frequencies: list[float] | np.ndarray,
    smatrix_arr: np.ndarray,
    polar_form: bool = True,
    renormalization: float = 50,
    port_data: list[str] | None = None,
) -> None:
    """
    Write Smatrix results in snp (toucstone) format

    Args:
        filename: filename
        frequencies: frequencies corresponding to smatrix_list
        smatrix_arr: Array of Smatrices at all frequencies. Has the form S[freq, row, col, component]
        polar_form: save Smatrix in polar or cartesian form.
                    Does no transformations so smatrix_arr needs to be given in the indicated format
        renormalization: renormalization impendance. Has currently no effect
        port_data: port data to be saved in the snp file as comments (start with ! Port)
    """
    if len(frequencies) != len(smatrix_arr):
        raise RuntimeError("Different number of frequencies and smatrix results in write_snp_file")
    with open(filename, "w", encoding="utf-8") as touchstone_file:
        touchstone_file.write("! Touchstone file exported from KQCircuits Elmer Simulation\n")
        touchstone_file.write(f"! Generated: {time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime())}\n")
        touchstone_file.write(
            "! Warning: Currently renormalization not implemented in Elmer "
            "(R on the next line might not correspond to the real port impedance)\n"
        )
        touchstone_file.write(f"# GHz S {'MA' if polar_form else 'IR'} R {renormalization} \n")
        if port_data:
            for p in port_data:
                if not p.startswith("! Port"):
                    logging.warning('port data in "write_snp_file" does not start with "! Port"')
                touchstone_file.write(p + "\n")
        else:
            touchstone_file.write("! Port: No port data given\n")

        for freq, smatrix_full in zip(frequencies, smatrix_arr):
            for row_ind, row in enumerate(smatrix_full):
                if row_ind == 0:
                    touchstone_file.write(f"{str(freq):30s} ")
                else:
                    touchstone_file.write(f"{' ':30s} ")
                for elem in row:
                    touchstone_file.write(f"{str(elem[0]):25s} {str(elem[1]):35s}")
                touchstone_file.write("\n")


def read_snp_file(filename: str | Path) -> tuple[np.ndarray, np.ndarray, bool, float, list[str]]:
    """
    Read an snp (touchstone file) in the same format as saved by "write_snp_file"

    Args:
        filename: snp filename to read

    Returns:
        tuple containg all inputs of "write_snp_file" except filename
    """
    port_data = []
    renormalization = -1.0
    polar_form = True
    data = []
    with open(filename, "r", encoding="utf-8") as touchstone_file:
        for line in touchstone_file:
            line = line.strip()
            if line.startswith("! Port"):
                port_data.append(line)
            elif line.startswith("!"):
                continue
            elif line.startswith("#"):
                partline = line.partition(" S ")[2]
                polar_str, _, re = partline.partition(" R ")
                if polar_str.strip() not in ("MA", "IR"):
                    logging.warning(f"No polar_form str found in {filename}")
                polar_form = polar_str.strip() == "MA"
                if not re.strip():
                    logging.warning(f"No renormalization found in {filename}")
                else:
                    renormalization = float(re.strip())
            elif line:  # not empty
                d = [float(s) for s in line.split()]
                if d:
                    data.append(d)

    max_elems = max((len(d) for d in data))
    min_elems = min((len(d) for d in data))
    if max_elems != min_elems + 1 or min_elems % 2 != 0:
        raise RuntimeError(
            f"Incorrect snp format: found rows with number of elements between {min_elems} and {max_elems}"
        )

    n_ports = int(min_elems / 2)
    n_matrices = int(len(data) / n_ports)

    frequencies = np.zeros([n_matrices])
    for i in range(n_matrices):
        frequencies[i] = data[n_ports * i][0]
        data[n_ports * i] = data[n_ports * i][1:]

    smatrix_arr = np.zeros([n_matrices, n_ports, n_ports, 2])

    for i, row, col, comp in np.ndindex(smatrix_arr.shape):
        smatrix_arr[i, row, col, comp] = data[n_ports * i + row][2 * col + comp]

    return frequencies, smatrix_arr, polar_form, renormalization, port_data


def write_project_results_json(json_data: dict[str, Any], path: Path, polar_form: bool = True) -> None:
    """
    Writes the solution data in '_project_results.json' format for one Elmer simulation.

    If tool is capacitance, writes capacitance matrix
    If tool is epr_3d or capacitance with integrate energies=True, writes energies
    If tool is wave_equation, writes S-matrix both in '_project_results.json' and touchstone format

    Args:
        json_data: Complete parameter json for simulation
        path: Location where to output the simulation model
        polar_form: Save Smatrix in polar or cartesian form
    """
    tool = json_data["tool"]
    simname = json_data["name"]
    sif_folder = path / simname
    result_json_path = path / (simname + "_project_results.json")

    if tool in ("capacitance", "epr_3d"):
        results = {}

        c_matrix_filename = sif_folder.joinpath("capacitance.dat")
        if c_matrix_filename.exists():

            with open(c_matrix_filename, "r", encoding="utf-8") as file:
                my_reader = csv.reader(file, delimiter=" ", skipinitialspace=True, quoting=csv.QUOTE_NONNUMERIC)
                c_matrix = list(my_reader)

            c_data = {
                f"C_Net{net_i + 1}_Net{net_j + 1}": [c_matrix[net_j][net_i]]
                for net_j in range(len(c_matrix))
                for net_i in range(len(c_matrix))
            }
            results.update(
                {
                    "CMatrix": c_matrix,
                    "Cdata": c_data,
                    "Frequency": [0],
                }
            )
        if tool == "epr_3d" or json_data["integrate_energies"]:
            results.update(get_energy_integrals(sif_folder))

        with open(result_json_path, "w", encoding="utf-8") as outfile:
            json.dump(
                results,
                outfile,
                indent=4,
            )

    elif tool == "wave_equation":

        frequencies = sorted([_get_f_from_smatrix_filename(sfile.name, simname) for sfile in sif_folder.glob("*.dat")])
        if json_data["sweep_type"] != "interpolating" and len(json_data["frequency"]) != len(frequencies):
            logging.warning("Different number of frequencies in json and result Smatrix files")

        ports = json_data["ports"]
        renormalizations = [p["renormalization"] for p in ports]

        if renormalizations[:-1] != renormalizations[1:]:
            logging.warning("Port renormalizations are not equal")
            logging.warning(f"Renormalizations: {renormalizations}")

        renormalization = renormalizations[0]

        smatrix_arr = np.zeros([len(frequencies), len(ports), len(ports), 2])
        results_list = []
        for f_ind, f in enumerate(frequencies):
            smatrix_full = read_result_smatrix(
                sif_folder / _get_smatrix_filename(simname, f),
                polar_form=polar_form,
            )
            results_list.append(
                {
                    "frequency": f,
                    "renormalization": renormalization,
                    "format": "polar" if polar_form else "cartesian",
                    "smatrix": smatrix_full.tolist(),
                }
            )
            smatrix_arr[f_ind] = smatrix_full

        with open(result_json_path, "w", encoding="utf-8") as outfile:
            json.dump(results_list, outfile, indent=4)

        # move Smatrix dat files to a separate folder
        data_folder = path.joinpath("elmer_data")
        data_folder.mkdir(parents=True, exist_ok=True)
        for dfile in path.rglob("*.dat*"):
            shutil.move(dfile, data_folder / dfile.name)

        # write touchstone
        port_data = [
            f"! Port {p['number']}: {p['type']} R {p['resistance']} "
            f"X {p['reactance']} L {p['inductance']} C {p['capacitance']}"
            for p in ports
        ]

        write_snp_file(
            f"{sif_folder}.s{len(ports)}p",
            frequencies,
            smatrix_arr,
            polar_form=polar_form,
            renormalization=renormalization,
            port_data=port_data,
        )
        filter_resonant_vtus(frequencies, smatrix_arr, sif_folder, simname, polar_form=polar_form)


def filter_resonant_vtus(
    frequencies: list[float] | np.ndarray, smatrix_arr: np.ndarray, sif_folder: Path, simname: str, polar_form=True
) -> None:
    """
    Roughly find vtus corresponding to resonances and move them to a separate
    folder `simname/resonant_vtus`. Also includes the ends of sweep interval. Rest of
    the vtus are moved to a folder `simname/filtered_vtus`

    Args:
        frequencies: frequencies of simulated smatrices
        smatrix_arr: simulated smatrices
        sif_folder: Folder containing sif and vtu files
        simname: simulation name
        polar_form: whether smatrix_arr is given in polar or cartesian format
    """
    available_vtus = list(sif_folder.glob("*.pvtu"))
    vtu_partitioned = len(available_vtus) != 0
    if not vtu_partitioned:
        available_vtus = list(sif_folder.glob("*.vtu"))

    if len(available_vtus) == 0:
        return

    s_f = np.array(frequencies)
    nports = smatrix_arr.shape[1]
    peak_inds = []
    # find peaks in diagonal entries
    for i in range(nports):
        s_mag = smatrix_arr[:, i, i, 0] if polar_form else np.hypot(smatrix_arr[:, i, i, 0], smatrix_arr[:, i, i, 1])
        peaksp, _ = find_peaks(s_mag)
        peaksm, _ = find_peaks(-s_mag)
        peak_inds += list(peaksp) + list(peaksm)
    peak_inds = list(set(peak_inds))
    f_peaks = s_f[peak_inds]

    extension_l = len("_t0001.pvtu") if vtu_partitioned else len("_t0001.vtu")
    available_f = np.array(
        list({float(str(v.name)[len(simname) + 2 : -extension_l].replace("_", ".")) for v in available_vtus})
    )
    available_f = np.sort(available_f)

    saved_f = [available_f[0], available_f[-1]]
    for f_p in f_peaks:
        saved_f.append(available_f[np.argmin(np.abs(available_f - f_p))])
    filtered_f = list(set(available_f) - set(saved_f))

    filter_folder = sif_folder.joinpath("filtered_vtus")
    resonant_folder = sif_folder.joinpath("resonant_vtus")
    filter_folder.mkdir(exist_ok=True)
    resonant_folder.mkdir(exist_ok=True)

    for f in available_f:
        for vtu in sif_folder.glob(simname + "_f" + str(f).replace(".", "_") + "*"):
            if str(vtu).endswith("vtu"):
                if f in filtered_f:
                    shutil.move(vtu, filter_folder / vtu.name)
                else:
                    shutil.move(vtu, resonant_folder / vtu.name)
