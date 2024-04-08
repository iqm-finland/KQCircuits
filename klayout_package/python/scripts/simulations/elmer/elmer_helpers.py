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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).
# pylint: disable=too-many-lines
import csv
import json
import logging
import time
import shutil
from pathlib import Path
from typing import Union, Sequence, Any, Dict, List
from scipy.constants import epsilon_0
from scipy.signal import find_peaks
import numpy as np


def read_mesh_names(path):
    """Returns names from mesh.names file"""
    list_of_names = []
    with open(path.joinpath("mesh.names")) as file:
        for line in file:
            if line.startswith("$ "):
                eq_sign = line.find(" =")
                if eq_sign > 2:
                    list_of_names.append(line[2:eq_sign])
    return list_of_names


def coordinate_scaling(json_data: Dict[str, Any]) -> float:
    """
    Returns coordinate scaling, which is determined by parameters 'units' in json_data.

    Args:
        json_data(json): all the model data produced by `export_elmer_json`

    Returns:
        (float): unit multiplier
    """
    units = json_data.get("units", "").lower()
    return {"nm": 1e-9, "um": 1e-6, "µm": 1e-6, "mm": 1e-3}.get(units, 1.0)


def sif_common_header(
    json_data: Dict[str, Any],
    folder_path: Union[Path, str],
    angular_frequency=None,
    def_file=None,
    dim="3",
    discontinuous_boundary=False,
) -> str:
    """
    Returns common header and simulation blocks of a sif file in string format.
    Optional definition file name is given in 'def_file'.

    """
    res = "Check Keywords Warn\n"
    res += "INCLUDE {}/{}\n".format(folder_path, "mesh.names")
    if def_file:
        res += "INCLUDE {}/{}\n".format(folder_path, def_file)
    res += sif_block("Header", ['Mesh DB "." "{}"'.format(folder_path), 'Results Directory "{}"'.format(folder_path)])

    if json_data.get("maximum_passes", 1) > 1:
        reset_adaptive_remesh_str = ["Reset Adaptive Mesh = Logical True"]
    else:
        reset_adaptive_remesh_str = []

    res += sif_block(
        "Run Control",
        [
            "Constraint Modes Analysis = True",
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
                else f'Coordinate System = "Cartesian {dim}D"'
            ),
            'Simulation Type = "Steady State"',
            f'Steady State Max Iterations = {json_data.get("maximum_passes", 1)}',
            f'Steady State Min Iterations = {json_data.get("minimum_passes", 1)}',
            ("" if angular_frequency is None else "Angular Frequency = {}".format(angular_frequency)),
            "Coordinate Scaling = {}".format(coordinate_scaling(json_data)),
            f'Mesh Levels = {json_data.get("mesh_levels", 1)}',
            "Discontinuous Boundary Full Angle = Logical True" if discontinuous_boundary else "",
        ],
    )
    return res


def sif_block(block_name: str, data: Sequence[str]) -> str:
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


def sif_matc_block(data: Sequence[str]) -> str:
    """Returns several matc statements to be used in sif (user does not need to type $-sign in front of lines).
    The block is of shape:
      $ data[0]
      $ data[1]
          .
          .
          .
      $ data[n]
    """
    res = ""
    for line in data:
        res += f"$  {line}\n"
    return res


def sif_linsys(method="mg", p_element_order=3, steady_state_error=None) -> Sequence[str]:
    """
    Returns a linear system definition in sif format.

    Args:
        method(str): linear system method (options: 1. bicgstab, 2. mg)
        p_element_order(int): p-element order (usully order 3 is quite ok for a regular solution)

    Returns:
        (str): linear system definitions in sif file format
    """
    linsys = ["$pn={}".format(p_element_order)]
    if method == "bicgstab":
        linsys += [
            "Linear System Solver = Iterative",
            "Linear System Iterative Method = BiCGStab",
            "Linear System Max Iterations = 500",
            "Linear System Convergence Tolerance = 1.0e-10",
            "Linear System Preconditioning = ILU1",
            "Linear System ILUT Tolerance = 1.0e-03",
            f"Steady State Convergence Tolerance = {1e-9 if steady_state_error is None else steady_state_error*1e-1}",
        ]
    elif method == "mg":
        linsys += [
            "Linear System Solver = Iterative",
            "Linear System Iterative Method = GCR ",
            "Linear System Max Iterations = 200",
            "Linear System Convergence Tolerance = 1.0e-10",
            "Linear System Abort Not Converged = False",
            "Linear System Residual Output = 10",
            "Linear System Preconditioning = multigrid !ILU2",
            "Linear System Refactorize = False",
            "MG Method = p",
            "MG Levels = $pn",
            "MG Smoother = SGS ! cg",
            "MG Pre Smoothing iterations = 2",
            "MG Post Smoothing Iterations = 2",
            "MG Lowest Linear Solver = iterative",
            "mglowest: Linear System Scaling = False",
            "mglowest: Linear System Iterative Method = CG !BiCGStabl",
            "mglowest: Linear System Preconditioning = ILU0",
            "mglowest: Linear System Max Iterations = 1000",
            "mglowest: Linear System Convergence Tolerance = 1.0e-4",
            f"Steady State Convergence Tolerance = {1e-9 if steady_state_error is None else steady_state_error*1e-1}",
        ]
    return linsys


def sif_adaptive_mesh(
    percent_error=0.005, max_error_scale=2, max_outlier_fraction=1e-3, minimum_passes=1
) -> Sequence[str]:
    """Returns a definition of adaptive meshing settings in sif format.

    Args:
        percent_error(float): Stopping criterion in adaptive meshing.
        max_error_scale(float): Maximum element error, relative to percent_error, allowed in individual elements.
        max_outlier_fraction(float): Maximum fraction of outliers from the total number of elements

    Returns:
        (str): adaptive meshing definitions in sif format.

    Note:
        ``maximum_passes`` is already set in :func:`~sif_common_header`
    """
    adaptive_lines = [
        "Run Control Constraint Modes = Logical True",
        "Adaptive Mesh Refinement = True",
        "Adaptive Remesh = True",
        f"Adaptive Error Limit = {percent_error}",
        "Adaptive Remesh Use MMG = Logical True",
        "Adaptive Mesh Numbering = False",
        f"Adaptive Min Depth = {minimum_passes}",
        f"Adaptive Max Error Scale = Real {max_error_scale}",
        f"Adaptive Max Outlier Fraction = Real {max_outlier_fraction}",
        "MMG niter = Integer 1",
    ]
    return adaptive_lines


def get_port_solver(
    ordinate, percent_error=0.005, max_error_scale=2, max_outlier_fraction=1e-3, maximum_passes=1, minimum_passes=1
) -> str:
    """
    Returns a port solver for wave equation in sif format.

    Args:
        ordinate(int): solver ordinate
        percent_error(float): Stopping criterion in adaptive meshing.
        max_error_scale(float): Maximum element error, relative to percent_error, allowed in individual elements.
        max_outlier_fraction(float): Maximum fraction of outliers from the total number of elements
        maximum_passes(int): Maximum number of adaptive meshing iterations.
        minimum_passes(int): Minimum number of adaptive meshing iterations.

    Returns:
        (str): port solver in sif format.
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
    if maximum_passes > 1:
        solver_lines += sif_adaptive_mesh(
            percent_error=percent_error,
            max_error_scale=max_error_scale,
            max_outlier_fraction=max_outlier_fraction,
            minimum_passes=minimum_passes,
        )
    return sif_block(f"Solver {ordinate}", solver_lines)


def get_vector_helmholtz(ordinate, angular_frequency, result_file, solver_options) -> str:
    """
    Returns a vector Helmholtz equation solver in sif file format.

    Args:
        ordinate(int): solver ordinate
        angular_frequency(float): angular frequency of the solution
        result_file(str): filename for the result S-matrix
        solver_options(dict): Additional solver options dict

    Returns:
        (str): vector Helmholtz in sif file format
    """
    nested_iteration = solver_options.get("nested_iteration", False)
    use_AV = solver_options.get("use_av", False)
    second_kind_basis = solver_options.get("second_kind_basis", False)
    quadratic_approximation = solver_options.get("quadratic_approximation", False)
    tol = solver_options.get("convergence_tolerance", 1.0e-10)
    max_iterations = solver_options.get("max_iterations", 2000)

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

    if use_AV:
        if nested_iteration:
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
                f"Outer: Linear System Convergence Tolerance = {tol}",
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
                f"Linear System Max Iterations = Integer {max_iterations}",
                f"Linear System Convergence Tolerance = {tol}",
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
        "" if use_AV else "Variable = E[E re:1 E im:1]",
        f"Optimize Bandwidth = Logical {not use_AV}",
        f"Use Gauss Law = Logical {use_AV}",
        f"Apply Conservation of Charge = Logical {use_AV}",
        "Calculate Energy Norm = Logical True",
        f"Angular Frequency = Real {angular_frequency}",
        f"Second Kind Basis = Logical {second_kind_basis}",
        f"Quadratic Approximation = Logical {quadratic_approximation}",
        *linear_system_lines,
        *lumping_lines,
    ]
    return sif_block(f"Solver {ordinate}", solver_lines)


def get_vector_helmholtz_calc_fields(ordinate: Union[str, int], angular_frequency: Union[str, float]) -> str:
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
        "Calculate Div of Poynting Vector = Logical True",
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
    ordinate: Union[str, int],
    capacitance_file: Union[Path, str],
    method="mg",
    p_element_order=3,
    percent_error=0.005,
    max_error_scale=2,
    max_outlier_fraction=1e-3,
    maximum_passes=1,
    minimum_passes=1,
):
    """
    Returns electrostatics solver in sif file format.

    Args:
        ordinate(int): solver ordinate
        capacitance_file(str): name of the capacitance matrix data file
        method(str): linear system method, see `sif_linsys`
        p_element_order(int): p-element order, see `sif_linsys`
        percent_error(float): Stopping criterion in adaptive meshing.
        max_error_scale(float): Maximum element error, relative to percent_error, allowed in individual elements.
        max_outlier_fraction(float): Maximum fraction of outliers from the total number of elements
        minimum_passes(int): Maximum number of adaptive meshing iterations.
        minimum_passes(int): Minimum number of adaptive meshing iterations.

    Returns:
        (str): electrostatics solver in sif file format
    """
    # Adaptive meshing not yet working with vectorised version (github.com/ElmerCSC/elmerfem/issues/401)
    useVectorised = p_element_order > 1
    solver = "StatElecSolveVec" if useVectorised else "StatElecSolve"
    solver_lines = [
        "Equation = Electro Statics",
        f'Procedure = "{solver}" "StatElecSolver"',
        "Variable = Potential",
        "Calculate Capacitance Matrix = True",
        "Calculate Electric Field = True",
        "Calculate Elemental Fields = True",
        "Average Within Materials = False",
        f"Capacitance Matrix Filename = {capacitance_file}",
        "Nonlinear System Max Iterations = 1",
        "Nonlinear System Consistent Norm = True",
    ]

    solver_lines += sif_linsys(method=method, p_element_order=p_element_order, steady_state_error=percent_error)
    if maximum_passes > 1:
        solver_lines += sif_adaptive_mesh(
            percent_error=percent_error,
            max_error_scale=max_error_scale,
            max_outlier_fraction=max_outlier_fraction,
            minimum_passes=minimum_passes,
        )
    if useVectorised:
        solver_lines += ["Vector Assembly = True"]
        solver_lines += ["Element = p:$pn"]
        solver_lines += ["Calculate Elemental Fields = True"]

    return sif_block(f"Solver {ordinate}", solver_lines)


def get_circuit_solver(ordinate: Union[str, int], p_element_order: int, exec_solver="Always"):
    """
    Returns circuit solver in sif file format.

    Args:
        ordinate(int): solver ordinate
        p_element_order(int): p-element order, see `sif_linsys`
        exec_solver(str): Execute solver (options: 'Always', 'After Timestep')

    Returns:
        (str): circuit solver in sif file format
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


def get_circuit_output_solver(ordinate: Union[str, int], exec_solver="Always"):
    """
    Returns circuit output solver in sif file format.
    This solver writes the circuit variables.

    Args:
        ordinate(int): solver ordinate
        exec_solver(str): Execute solver (options: 'Always', 'After Timestep')

    Returns:
        (str): circuit output solver in sif file format
    """
    solver_lines = [
        f"Exec Solver = {exec_solver}",
        "Equation = Circuits Output",
        'Procedure = "CircuitsAndDynamics" "CircuitsOutput"',
    ]
    return sif_block(f"Solver {ordinate}", solver_lines)


def get_magneto_dynamics_2d_harmonic_solver(
    ordinate: Union[str, int],
    percent_error=0.005,
    max_error_scale=2,
    max_outlier_fraction=1e-3,
    maximum_passes=1,
    minimum_passes=1,
):
    """
    Returns magneto-dynamics 2d solver in sif file format.

    Args:
        ordinate(int): solver ordinate
        percent_error(float): Stopping criterion in adaptive meshing.
        max_error_scale(float): Maximum element error, relative to percent_error, allowed in individual elements.
        max_outlier_fraction(float): Maximum fraction of outliers from the total number of elements
        maximum_passes(int): Maximum number of adaptive meshing iterations.
        minimum_passes(int): Minimum number of adaptive meshing iterations.

    Returns:
        (str): magneto-dynamics 2d solver in sif file format
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
        "Linear System Max Iterations = 3000",
        "Linear System Residual Output = 10",
        "Linear System Abort not Converged = False",
        "Linear System ILUT Tolerance=1e-8",
        "BicgStabL Polynomial Degree = 6",
        "Steady State Convergence Tolerance = 1e-05",
    ]
    if maximum_passes > 1:
        solver_lines += sif_adaptive_mesh(
            percent_error=percent_error,
            max_error_scale=max_error_scale,
            max_outlier_fraction=max_outlier_fraction,
            minimum_passes=minimum_passes,
        )
    solver_lines += [
        "Vector Assembly = True",
        "Element = p:$pn",
    ]

    return sif_block(f"Solver {ordinate}", solver_lines)


def get_magneto_dynamics_calc_fields(ordinate: Union[str, int], p_element_order: int):
    """
    Returns magneto-dynamics calculate fields solver in sif file format.

    Args:
        ordinate(int): solver ordinate
        p_element_order(int): p-element order, see `sif_linsys`

    Returns:
        (str): magneto-dynamics calculate fields solver in sif file format
    """
    solver_lines = [
        "Exec Solver = Always",
        'Equation = "MGDynamicsCalc"',
        'Procedure = "MagnetoDynamics" "MagnetoDynamicsCalcFields"',
        "Linear System Symmetric = True",
        'Potential Variable = String "A"',
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


def get_result_output_solver(ordinate, output_file_name, exec_solver="Always"):
    """
    Returns result output solver in sif file format.

    Args:
        ordinate(int): solver ordinate
        output_file_name(Path): output file name

    Returns:
        (str): result ouput solver in sif file format
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


def get_save_data_solver(ordinate, result_file="results.dat"):
    """
    Returns save data solver in sif file format.

    Args:
        ordinate(int): solver ordinate
        result_file(str): data file name for results

    Returns:
        (str): save data solver in sif file format
    """
    solver_lines = [
        "Exec Solver = After All",
        'Equation = "sv"',
        'Procedure = "SaveData" "SaveScalars"',
        f"Filename = {result_file}",
    ]
    return sif_block(f"Solver {ordinate}", solver_lines)


def get_save_energy_solver(ordinate, energy_file, bodies):
    """
    Returns save energy solver in sif file format.

    Args:
        ordinate(int): solver ordinate
        energy_file(str): data file name for energy results
        bodies(list(str)): body names for energy calculation

    Returns:
        (str): save energy solver in sif file format
    """
    solver_lines = [
        "Exec Solver = Always",
        'Equation = "SaveEnergy"',
        'Procedure = "SaveData" "SaveScalars"',
        f"Filename = {energy_file}",
        "Parallel Reduce = Logical True",
        # Add all target bodies to the solver
        *(
            line
            for layer_props in (
                (
                    f"Variable {i} = Potential",
                    f"Operator {i} = body diffusive energy",
                    f"Mask Name {i} = {interface}",
                    f"Coefficient {i} = Relative Permittivity",
                )
                for i, interface in enumerate(bodies, 1)
            )
            for line in layer_props
        ),
    ]
    return sif_block(f"Solver {ordinate}", solver_lines)


def get_equation(ordinate, solver_ids, keywords=None):
    """
    Returns equation in sif file format.

    Args:
        ordinate(int): equation ordinate
        solver_ids(list(int)): list of active solvers (ordinates)
        keywords(list(str)): keywords for equation

    Returns:
        (str): equation in sif file format
    """
    keywords = [] if keywords is None else keywords
    equation_lines = [f'Active Solvers({len(solver_ids)}) = {" ".join([str(sid) for sid in solver_ids])}']
    return sif_block(f"Equation {ordinate}", equation_lines + keywords)


def sif_body(ordinate, target_bodies, equation, material, keywords=None):
    """
    Returns body in sif file format.

    Args:
        ordinate(int): equation ordinate
        target_bodies(list(int)): list of target bodies
        equation(int): active equations
        material(int): assigned material
        keywords(list(str)): keywords for body

    Returns:
        (str): body in sif file format
    """
    keywords = [] if keywords is None else keywords
    value_list = [
        f'Target Bodies({len(target_bodies)}) = $ {" ".join(target_bodies)}',
        f"Equation = {str(equation)}",
        f"Material = {str(material)}",
    ]
    return sif_block(f"Body {ordinate}", value_list + keywords)


def sif_component(ordinate, master_bodies, coil_type, keywords=None):
    """
    Returns component in sif file format.

    Args:
        ordinate(int): equation ordinate
        master_bodies(list(int)): list of bodies
        coil_type(str): coil type (options: 'stranded', 'massive', 'foil')
        keywords(list(str)): keywords for body

    Returns:
        (str): component in sif file format
    """
    keywords = {} if keywords is None else keywords
    value_list = [
        f'Master Bodies({len(master_bodies)}) = $ {" ".join([str(body) for body in master_bodies])}',
        f"Coil Type = {str(coil_type)}",
    ]
    return sif_block(f"Component {ordinate}", value_list + keywords)


def sif_boundary_condition(ordinate, target_boundaries, conditions):
    """
    Returns boundary condition in sif file format.

    Args:
        ordinate(int): equation ordinate
        target_boundaries(list(int)): list of target boundaries
        conditions(list(str)): keywords for boundary condition

    Returns:
        (str): boundary condition in sif file format
    """
    value_list = [
        f'Target Boundaries({len(target_boundaries)}) = $ {" ".join(target_boundaries)}',
    ] + conditions

    return sif_block(f"Boundary Condition {ordinate}", value_list)


def produce_sif_files(json_data: dict, path: Path) -> List[Path]:
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

    if json_data["tool"] == "capacitance" and len(sif_names) != 1:
        logging.warning(f"Capacitance tool only supports 1 sif name, given {len(sif_names)}")

    sif_filepaths = []
    for ind, sif in enumerate(sif_names):
        if json_data["tool"] == "capacitance":
            content = sif_capacitance(json_data, path, vtu_name=path, angular_frequency=0, dim=3, with_zero=False)
        elif json_data["tool"] == "wave_equation":
            freqs = json_data["frequency"]
            if len(freqs) != len(sif_names):
                logging.warning(
                    f"Number of sif names ({len(sif_names)}) does not match the number of frequencies ({len(freqs)})"
                )
            content = sif_wave_equation(json_data, path, frequency=freqs[ind])
        else:
            logging.warning(f"Unkown tool: {json_data['tool']}. No sif file created")
            return []

        sif_filepath = path.joinpath(f"{sif}.sif")
        with open(sif_filepath, "w") as f:
            f.write(content)
        sif_filepaths.append(sif_filepath)

    return sif_filepaths


def get_body_list(json_data, dim, mesh_names):
    """
    Returns body list for 2d or 3d model.

    Args:
        json_data(json): all the model data produced by `export_elmer_json`
        dim(int): dimensionality of the model (options: 2 or 3)
        mesh_names(list): list of physical group names from the mesh.names file

    Returns:
        (list(str)): list of model bodies
    """
    body_list = []
    if dim == 2:
        body_list = [n for n in ["vacuum", *json_data["layers"].keys()] if n in mesh_names]
    elif dim == 3:
        body_list = [n for n in ["vacuum", "pec", *json_data["material_dict"].keys()] if n in mesh_names]

    unique_bodies = set()
    return [n for n in body_list if not (n in unique_bodies or unique_bodies.add(n))]


def get_permittivities(json_data, with_zero, dim, mesh_names):
    """
    Returns permittivities of bodies.

    If permittivity for the body with name "abcd_1_extra" is not found, check the available permittivities in json
    and if a key corresponding to beginning of the searched permittivity is found use that.

    If such hit is also not found default to 1.0

    Args:
        json_data(json): all the model data produced by `export_elmer_json`
        with_zero(bool): without dielectrics if true
        dim(int): dimensionality of the model (options: 2 or 3)
        mesh_names(list): list of physical group names from the mesh.names file

    Returns:
        (list(str)): list of body permittivities
    """

    def _search_permittivity(json_data, body):
        json_bodies = [k[:-13] for k in json_data.keys() if k.endswith("_permittivity")]
        for p in json_bodies:
            if body.startswith(p):
                used_perm = json_data[f"{p}_permittivity"]
                return used_perm
        return 1.0

    bodies = get_body_list(json_data, dim, mesh_names)
    if dim == 2:
        return [
            1.0 if with_zero else json_data.get(f"{s}_permittivity", _search_permittivity(json_data, s)) for s in bodies
        ]
    elif dim == 3:
        return [
            1.0 if with_zero else json_data["material_dict"].get(n, dict()).get("permittivity", 1.0) for n in bodies
        ]
    return []


def get_signals(json_data, dim, mesh_names):
    """
    Returns model signals.

    Args:
        json_data(json): all the model data produced by `export_elmer_json`
        dim(int): dimensionality of the model (options: 2 or 3)
        mesh_names(list): list of physical group names from the mesh.names file

    Returns:
        (list(str)): list of signals
    """
    if dim == 2:
        return [n for n in json_data["layers"].keys() if "signal" in n and n in mesh_names]
    elif dim == 3:
        port_numbers = sorted([port["number"] for port in json_data["ports"]])
        return [n for n in [f"signal_{i}" for i in port_numbers] if n in mesh_names]
    return []


def get_grounds(json_data, dim, mesh_names):
    """
    Returns model grounds.

    Args:
        json_data(json): all the model data produced by `export_elmer_json`
        dim(int): dimensionality of the model (options: 2 or 3)
        mesh_names(list): list of physical group names from the mesh.names file

    Returns:
        (list(str)): list of grounds
    """
    if dim == 2:
        signals = get_signals(json_data, dim, mesh_names)
        return [n for n in json_data["layers"].keys() if "ground" in n and n not in signals and n in mesh_names]
    elif dim == 3:
        return [n for n in mesh_names if n.startswith("ground")]
    return []


def sif_capacitance(
    json_data: dict, folder_path: Path, vtu_name: str, angular_frequency: float, dim: int, with_zero: bool = False
):
    """
    Returns the capacitance solver sif. If `with_zero` is true then all the permittivities are set to 1.0.
    It is used in computing capacitances without dielectrics (so called 'capacitance0')

    Args:
        json_data(json): all the model data produced by `export_elmer_json`
        folder_path(Path): folder path of the model files
        vtu_name(str): name of the paraview file
        angular_frequency(float): angular frequency of the solution
        dim(int): model dimensionality (2 or 3)
        with_zero(bool): without dielectrics if true

    Returns:
        (str): elmer solver input file for capacitance
    """

    name = "capacitance0" if with_zero else "capacitance"

    header = sif_common_header(json_data, folder_path, angular_frequency=angular_frequency, dim=dim)
    constants = sif_block("Constants", [f"Permittivity Of Vacuum = {epsilon_0}"])

    solvers = get_electrostatics_solver(
        ordinate=1,
        capacitance_file=folder_path / f"{name}.dat",
        method=json_data["linear_system_method"],
        p_element_order=json_data["p_element_order"],
        maximum_passes=json_data["maximum_passes"],
        minimum_passes=json_data["minimum_passes"],
        percent_error=json_data["percent_error"],
        max_error_scale=json_data["max_error_scale"],
        max_outlier_fraction=json_data["max_outlier_fraction"],
    )
    solvers += get_result_output_solver(
        ordinate=2,
        output_file_name=vtu_name,
        exec_solver="Always",
    )
    solvers += get_save_data_solver(ordinate=3, result_file=name)
    equations = get_equation(
        ordinate=1,
        solver_ids=[1],
        keywords=["Calculate Electric Energy = True"] if dim == 2 else [],
    )

    mesh_names = read_mesh_names(folder_path)
    body_list = get_body_list(json_data, dim=dim, mesh_names=mesh_names)
    permittivity_list = get_permittivities(json_data, with_zero=with_zero, dim=dim, mesh_names=mesh_names)

    if json_data.get("integrate_energies", False) and not with_zero:  # no EPR for inductance
        solvers += get_save_energy_solver(ordinate=4, energy_file="energy.dat", bodies=body_list)

    bodies = ""
    materials = ""
    for i, (body, perm) in enumerate(zip(body_list, permittivity_list), 1):
        bodies += sif_body(
            ordinate=i, target_bodies=[body], equation=1, material=i, keywords=[f"{body} = Logical True"]
        )

        materials += sif_block(f"Material {i}", [f"Relative Permittivity = {perm}"])

    # Boundary conditions
    boundary_conditions = ""
    grounds = get_grounds(json_data, dim=dim, mesh_names=mesh_names)
    ground_boundaries = [f"{g}_boundary" for g in grounds] if dim == 2 else grounds
    n_boundaries = 0
    if len(ground_boundaries) > 0:
        boundary_conditions += sif_boundary_condition(
            ordinate=1, target_boundaries=ground_boundaries, conditions=["Potential = 0.0"]
        )
        n_boundaries = 1

    signals = get_signals(json_data, dim=dim, mesh_names=mesh_names)
    signals_boundaries = [f"{s}_boundary" for s in signals] if dim == 2 else signals

    cbody_map = {}
    for i, s in enumerate(signals_boundaries, 1):
        s_wo_mer = s.replace("_mer", "")
        if s_wo_mer in cbody_map.keys():
            cbody_map[s] = cbody_map[s_wo_mer]
        else:
            cbody_map[s] = len(cbody_map.keys()) + 1

    for i, s in enumerate(signals_boundaries, 1):
        boundary_conditions += sif_boundary_condition(
            ordinate=i + n_boundaries, target_boundaries=[s], conditions=[f"Capacitance Body = {cbody_map[s]}"]
        )
    n_boundaries += len(cbody_map)

    bc_dict = json_data.get("boundary_conditions", None)
    if bc_dict is not None:
        for bc in ["xmin", "xmax", "ymin", "ymax"]:
            bc_name = f"{bc}_boundary"
            b = bc_dict.get(bc, None)
            if b is not None:
                if "potential" in b:
                    conditions = [f"Potential = {b['potential']}"]
                    boundary_conditions += sif_boundary_condition(
                        ordinate=1 + n_boundaries, target_boundaries=[bc_name], conditions=conditions
                    )
                    n_boundaries += 1

    # Add place-holder boundaries (if additional physical groups are given)
    other_groups = [n for n in mesh_names if n not in body_list + grounds + signals and not n.startswith("port_")]
    for i, s in enumerate(other_groups, 1):
        boundary_conditions += sif_boundary_condition(
            ordinate=i + n_boundaries,
            target_boundaries=[s],
            conditions=[
                "! This BC does not do anything, but",
                "! MMG does not conserve GeometryIDs if there is no BC defined.",
            ],
        )
    n_boundaries += len(other_groups)

    return header + constants + solvers + equations + materials + bodies + boundary_conditions


def sif_inductance(json_data, folder_path, angular_frequency, circuit_definitions_file):
    """
    Returns inductance sif file content for a cross section model
    in string format. The sif file corresponds to the mesh produced by
    `produce_cross_section_mesh`

    TODO: Allow multiple traces and for each trace multiple metal layers

    Args:
        json_data(json): all the model data produced by `export_elmer_json`
        folder_path(Path): folder path for the sif file
        angular_frequency(float): angular frequency of the solution
        circuit_definitions_file(Path): file name for circuit definitions

    Returns:
        (str): elmer solver input file for inductance computation
    """
    header = sif_common_header(json_data, folder_path, angular_frequency, circuit_definitions_file, dim=2)
    equations = get_equation(ordinate=1, solver_ids=[1, 2, 3])

    solvers = get_circuit_solver(ordinate=1, p_element_order=json_data["p_element_order"], exec_solver="Always")

    solvers += get_magneto_dynamics_2d_harmonic_solver(
        ordinate=2,
        maximum_passes=json_data["maximum_passes"],
        minimum_passes=json_data["minimum_passes"],
        percent_error=json_data["percent_error"],
        max_error_scale=json_data["max_error_scale"],
        max_outlier_fraction=json_data["max_outlier_fraction"],
    )

    solvers += get_magneto_dynamics_calc_fields(ordinate=3, p_element_order=json_data["p_element_order"])

    solvers += get_result_output_solver(
        ordinate=4,
        output_file_name="inductance",
        exec_solver="Always",
    )

    solvers += get_circuit_output_solver(ordinate=5, exec_solver="Always")
    solvers += get_save_data_solver(ordinate=6, result_file="inductance.dat")

    # Divide layers into different materials
    mesh_names = read_mesh_names(folder_path)
    signals = get_signals(json_data, dim=2, mesh_names=mesh_names)
    grounds = get_grounds(json_data, dim=2, mesh_names=mesh_names)
    body_list = get_body_list(json_data, dim=2, mesh_names=mesh_names)
    others = list((set(body_list) - set(signals) - set(grounds)).union(["vacuum"]))

    bodies = sif_body(ordinate=1, target_bodies=others, equation=1, material=1)
    bodies += sif_body(ordinate=2, target_bodies=grounds, equation=1, material=2)
    bodies += sif_body(ordinate=3, target_bodies=signals, equation=1, material=2)

    materials = sif_block("Material 1", ["Relative Permeability = 1", "Electric Conductivity = 1"])

    london_penetration_depth = json_data.get("london_penetration_depth", 0.0)
    if london_penetration_depth > 0:
        opt_params = [
            "Electric Conductivity = 0",
            "$ lambda_l = {}".format(london_penetration_depth),
            "$ mu_0 = 4e-7*pi",
            "London Lambda = Real $ mu_0 * lambda_l^2",
        ]
    else:
        opt_params = ["Electric Conductivity = 1e10"]

    materials += sif_block("Material 2", ["Relative Permeability = 1", *opt_params])

    london_param = ["London Equations = Logical True"] if london_penetration_depth > 0 else []

    components = sif_component(ordinate=1, master_bodies=[3], coil_type="Massive", keywords=london_param)

    res = header + equations + solvers + materials + bodies + components

    res += sif_block("Body Force 1", ['Name = "Circuit"', "testsource Re = Real 1.0", "testsource Im = Real 0.0"])

    return res


def sif_circuit_definitions(json_data):
    """
    Returns content of circuit definitions in string format.

    Args:
        json_data(json): all the model data produced by `export_elmer_json`
    """
    res = "$ Circuits = 1\n"

    # Define variable count and initialize circuit matrices.
    london_penetration_depth = json_data.get("london_penetration_depth", 0.0)
    n_equations = 4 + int(london_penetration_depth > 0.0)
    res += f"\n$ C.1.perm = zeros({n_equations})\n"
    for i in range(n_equations):
        res += f"$ C.1.perm({i % (n_equations - 1) + 1 if i > 0 and n_equations == 4 else i}) = {i}\n"

    res += f"\n$ C.1.variables = {n_equations}\n"
    for n in ["A", "B", "Mre", "Mim"]:
        res += "$ C.1.{} = zeros({n_equations},{n_equations})\n".format(n, n_equations=n_equations)

    # Define variables
    res += "\n"
    var_names = ["i_testsource", "v_testsource", "i_component(1)", "v_component(1)"]
    if london_penetration_depth > 0.0:
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
    if london_penetration_depth > 0.0:
        res += "\n$ C.1.A(4,3) = 1\n"
        res += "$ C.1.B(4,4) = -1\n"

    # 1 component equation, linking phi and i of the component 1, written by elmer at the row 4
    # (beta a, phi') + phi_component(1) (beta grad phi_0, grad phi') = i_component(1)
    return res


def get_port_from_boundary_physical_names(ports, name):
    for port in ports:
        print(name, port["physical_names"])
        if name in [t[1] for t in port["physical_names"]]:
            return port
    return None


def sif_wave_equation(
    json_data: dict,
    folder_path: Path,
    frequency: float = 10,
) -> str:
    """
    Returns the wave equation solver sif.

    Args:
        json_data: All the model data produced by `export_elmer_json`
        folder_path: Folder path of the model files
        frequency: Frequency used in simulation in GHz

    Returns:
        (str): elmer solver input file for wave equation
    """
    solver_options = json_data["solver_options"]

    lpd = solver_options.get("london_penetration_depth", 0)
    cond = solver_options.get("conductivity", 0)
    use_AV = solver_options.get("use_av", False)
    metal_height = json_data["parameters"].get("metal_height", 0)
    if len(metal_height) > 1:
        logging.warning(
            "Simulation contains multiple metal layers, This is not yet supported with"
            f"elmer wave-equation tool. Using thickness {metal_height[0]}um for all ports"
        )
    metal_height = metal_height[0]

    dim = 3
    header = sif_common_header(json_data, folder_path, discontinuous_boundary=(use_AV and metal_height == 0))
    constants = sif_block("Constants", [f"Permittivity Of Vacuum = {epsilon_0}"])

    # Bodies and materials
    mesh_names = read_mesh_names(folder_path)
    body_list = get_body_list(json_data, dim=dim, mesh_names=mesh_names)
    permittivity_list = get_permittivities(json_data, with_zero=False, dim=dim, mesh_names=mesh_names)

    bodies = ""
    materials = ""
    betas = []

    for i, (body, perm) in enumerate(zip(body_list, permittivity_list), 1):
        material_parameters = [f'Name = "{body}"']
        if body == "pec" and use_AV:
            bodies += sif_block(f"Body {i}", [f"Target Bodies(1) = $ {body}", f"Material = {i}"])
        else:
            bodies += sif_body(ordinate=i, target_bodies=[body], equation=1, material=i)
            material_parameters += [f"Relative Permittivity = {perm}"]

        materials += sif_block(f"Material {i}", material_parameters)
        betas.append(f"beta_{body} = w*sqrt({perm}*eps0*mu0)")

    n_bodies = len(body_list)

    # Matc block
    matc_list = [
        f"f0 = {1e9*frequency}",
        "w=2*pi*(f0)",
        "mu0=4e-7*pi",
        "eps0 = 8.854e-12",
    ]

    if lpd != 0:
        matc_list += [
            f"lambda_l = {lpd}",
            "sigma = 1/(w*mu0*lambda_l^2)",
        ]
    if use_AV:
        port_area = (json_data["parameters"]["port_size"] * 1e-6) ** 2
        # Use 200nm thickness for impedance calculation when using sheet metal
        signal_height = 200e-9 if metal_height == 0 else metal_height
        signal_area = signal_height * json_data["parameters"].get("a", 10) * 1e-12
        matc_list += [
            "V0 = 1",
            "Z0 = 50",
            f"port_area = {port_area}",
            f"signal_area = {signal_area}",
        ]
    else:
        matc_list += [*betas]

    if cond != 0:
        matc_list += [f"film_conductivity = {cond}"]

    matc_blocks = sif_matc_block(matc_list)

    # Solvers & Equations
    result_file = f'SMatrix_{json_data["name"]}_f{str(frequency).replace(".", "_")}.dat'
    solvers = ""
    solver_ordinate = 1
    if not use_AV:
        solvers += get_port_solver(
            ordinate=solver_ordinate,
            maximum_passes=json_data["maximum_passes"],
            minimum_passes=json_data["minimum_passes"],
            percent_error=json_data["percent_error"],
            max_error_scale=json_data["max_error_scale"],
            max_outlier_fraction=json_data["max_outlier_fraction"],
        )
        solver_ordinate += 1

    solvers += get_vector_helmholtz(
        ordinate=solver_ordinate, angular_frequency="$ w", result_file=result_file, solver_options=solver_options
    )
    solvers += get_vector_helmholtz_calc_fields(ordinate=solver_ordinate + 1, angular_frequency="$ w")

    solvers += get_result_output_solver(
        ordinate=solver_ordinate + 2,
        output_file_name=Path(str(folder_path) + "_f" + str(frequency).replace(".", "_")),
        exec_solver="Always",
    )

    # Equations
    equations = get_equation(ordinate=1, solver_ids=[solver_ordinate, solver_ordinate + 1])
    if not use_AV:
        equations += get_equation(ordinate=2, solver_ids=[1])

    # Boundary conditions
    boundary_conditions = ""
    grounds = get_grounds(json_data, dim=dim, mesh_names=mesh_names)

    pec_box = grounds[-1]
    sc_grounds = grounds[:-1]

    if use_AV:
        pec_conditions = ["AV re {e} = 0", "AV im {e} = 0", "AV re = Real 0", "AV im = Real 0"]
        if lpd > 0:
            sc_metal_conditions = [
                "Layer Thickness = $ lambda_l",
                "Layer Electric Conductivity Im = $ sigma",
                "Apply Conservation of Charge = Logical True",
            ]
        elif cond > 0:
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
        if lpd > 0:
            sc_metal_conditions = ["Layer Thickness = $ lambda_l", "Layer Electric Conductivity Im = $ sigma"]
        else:
            sc_metal_conditions = ["E re {e} = 0", "E im {e} = 0"]

    boundary_conditions += sif_boundary_condition(ordinate=1, target_boundaries=[pec_box], conditions=pec_conditions)
    n_boundaries = 1

    sc_ground_conditions = sc_metal_conditions + ([] if use_AV else ["Potential = 0"])
    sc_signal_conditions = sc_metal_conditions + ([] if use_AV else ["Potential = 1"])

    boundary_conditions += sif_boundary_condition(
        ordinate=2, target_boundaries=sc_grounds, conditions=sc_ground_conditions
    )
    n_boundaries += 1

    signal_bc_inds = []
    signals = get_signals(json_data, dim=dim, mesh_names=mesh_names)
    for i, s in enumerate(signals, 1):
        signal_bc_inds.append(i + n_boundaries)
        boundary_conditions += sif_boundary_condition(
            ordinate=i + n_boundaries, target_boundaries=[s], conditions=sc_signal_conditions
        )
    n_boundaries += len(signals)

    # Port boundaries
    body_ids = {b: None for b in body_list}
    constraint_ind = 1  # for enumerating edge port constraint modes in av
    for i, port in enumerate(json_data["ports"], 1):
        port_name = f'port_{port["number"]}'
        if port["type"] == "EdgePort":
            # The edge port is split by dielectric materials
            port_parts = [(n, n[len(port_name + "_") :]) for n in mesh_names if n.startswith(port_name + "_")]
        else:
            # The material is assumed to be homogeneous throughout the internal port, so any material can be used.
            # We pick 'vacuum' by default if it exists.
            any_material = "vacuum" if "vacuum" in body_list else body_list[0]
            port_parts = [(port_name, any_material)] if port_name in mesh_names else []

        port_part_bc_indices = {}
        for name, mat in port_parts:
            n_boundaries += 1
            port_part_bc_indices[mat] = n_boundaries
            # Add boundary condition for the port
            if use_AV:
                conditions = ["AV re {e} = 0", "AV im {e} = 0"]
            else:
                # Add body for the port equation, if it doesn't exist yet
                if mat not in ("signal", "ground"):
                    if body_ids[mat] is None:
                        n_bodies += 1
                        body_ids[mat] = n_bodies
                        bodies += sif_body(
                            ordinate=body_ids[mat],
                            target_bodies=[f"{body_ids[mat]}"],
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
        if use_AV and port["type"] == "EdgePort":
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
                        "Incident Voltage = $ V0",
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


def read_result_smatrix(s_matrix_filename: str, path: Path = None, polar_form: bool = True):
    """
    Read Elmer Smatrix output and transform the entries to polar format

    Args:
        s_matrix_filename: Relatvive Smatrix path
        path: Optional basename for the path if `s_matrix_filename` does not exist
                     Defaults to None.
        polar_form: Transform the entries to polar form. Defaults to True.

    Returns:
        np.array: Smatrix as 2D numpy array
    """
    if not Path(s_matrix_filename).exists() and path is not None:
        s_matrix_filename = path.joinpath(s_matrix_filename)

    with open(s_matrix_filename, "r") as file:
        reader = csv.reader(file, delimiter=" ", skipinitialspace=True, quoting=csv.QUOTE_NONNUMERIC)
        s_matrix_re = np.array([[x for x in row if isinstance(x, float)] for row in reader])

    with open(str(s_matrix_filename) + "_im", "r") as file:
        reader = csv.reader(file, delimiter=" ", skipinitialspace=True, quoting=csv.QUOTE_NONNUMERIC)
        s_matrix_im = np.array([[x for x in row if isinstance(x, float)] for row in reader])

    if polar_form:
        s_matrix_mag = np.hypot(s_matrix_re, s_matrix_im)
        s_matrix_angle = np.degrees(np.arctan2(s_matrix_im, s_matrix_re))

    smatrix_full = np.zeros_like(s_matrix_re).tolist()
    for i1, i2 in np.ndindex(s_matrix_re.shape):
        if polar_form:
            smatrix_full[i1][i2] = (s_matrix_mag[i1, i2], s_matrix_angle[i1, i2])
        else:
            smatrix_full[i1][i2] = (s_matrix_re[i1, i2], s_matrix_im[i1, i2])

    return smatrix_full


def write_project_results_json(json_data: dict, path: Path, msh_filepath, polar_form: bool = True):
    """
    Writes the solution data in '_project_results.json' format for one Elmer simulation.

    If tool is capacitance, writes capacitance matrix
    If tool is wave_equation, writes S-matrix both in '_project_results.json' and touchstone format

    Args:
        json_data(dict): Complete parameter json for simulation
        path(Path): Location where to output the simulation model
        msh_filepath(Path): Location of msh file in `Path` format
        polar_form  (bool): Save Smatrix in polar or cartesian form
    """
    tool = json_data["tool"]
    sif_folder = path.joinpath(msh_filepath.stem)
    main_sim_folder = sif_folder.parent
    json_filename = main_sim_folder / (sif_folder.name + "_project_results.json")
    simname = json_data["name"]

    if tool == "capacitance":
        c_matrix_filename = sif_folder.joinpath("capacitance.dat")

        if c_matrix_filename.exists():

            with open(c_matrix_filename, "r") as file:
                my_reader = csv.reader(file, delimiter=" ", skipinitialspace=True, quoting=csv.QUOTE_NONNUMERIC)
                c_matrix = list(my_reader)

            c_data = {
                "C_Net{}_Net{}".format(net_i + 1, net_j + 1): [c_matrix[net_j][net_i]]
                for net_j in range(len(c_matrix))
                for net_i in range(len(c_matrix))
            }

            with open(json_filename, "w") as outfile:
                json.dump(
                    {
                        "CMatrix": c_matrix,
                        "Cdata": c_data,
                        "Frequency": [0],
                    },
                    outfile,
                    indent=4,
                )
    elif tool == "wave_equation":

        frequencies = json_data["frequency"]

        ports = json_data["ports"]
        renormalizations = [p["renormalization"] for p in ports]

        if renormalizations[:-1] != renormalizations[1:]:
            logging.warning("Port renormalizations are not equal")
            logging.warning(f"Renormalizations: {renormalizations}")

        data_folder = main_sim_folder.joinpath("elmer_data")
        data_folder.mkdir(parents=True, exist_ok=True)

        results = []
        for f in frequencies:
            s_matrix_filename = main_sim_folder.joinpath(f'SMatrix_{simname}_f{str(f).replace(".", "_")}.dat')
            smatrix_full = read_result_smatrix(
                s_matrix_filename, path=path.joinpath(msh_filepath.stem), polar_form=polar_form
            )
            results.append(
                {
                    "frequency": f,
                    "renormalization": renormalizations[0],
                    "format": "polar" if polar_form else "cartesian",
                    "smatrix": smatrix_full,
                }
            )

        with open(json_filename, "w") as outfile:
            json.dump(results, outfile, indent=4)

        for f in main_sim_folder.rglob("*.dat*"):
            shutil.move(f, data_folder / f.name)
        # write touchstone
        touchstone_filename = f"{sif_folder}.s{len(ports)}p"
        with open(touchstone_filename, "w") as touchstone_file:
            touchstone_file.write("! Touchstone file exported from KQCircuits Elmer Simulation\n")
            touchstone_file.write(f"! Generated: {time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime())}\n")
            touchstone_file.write(
                "! Warning: Currently renormalization not implemented in Elmer "
                "(R on the next line might not correspond to the real port impedance)\n"
            )
            touchstone_file.write(f"# GHz S {'MA' if polar_form else 'IR'} R {renormalizations[0]} \n")
            for p in ports:
                touchstone_file.write(
                    f"! Port {p['number']}: {p['type']} R {p['resistance']} "
                    f"X {p['reactance']} L {p['inductance']} C {p['capacitance']}\n"
                )
            for res in results:
                smatrix_full = res["smatrix"]
                for row_ind, row in enumerate(smatrix_full):
                    if row_ind == 0:
                        touchstone_file.write("{:30s} ".format(str(res["frequency"])))
                    else:
                        touchstone_file.write("{:30s} ".format(" "))
                    for elem in row:
                        touchstone_file.write("{:25s} {:35s}".format(str(elem[0]), str(elem[1])))
                    touchstone_file.write("\n")

        filter_resonant_vtus(results, sif_folder, simname)


def filter_resonant_vtus(results, sif_folder, simname):
    """
    Roughly find vtus corresponding to resonances and move them to a separate
    folder `simname/resonant_vtus`. Also includes the ends of sweep interval. Rest of
    the vtus are moved to a folder `simname/filtered_vtus`

    Args:
        results (list[dict]): results in a list of dicts as saved to the json
        sif_folder (str): Folder containing sif and vtu files
        simname (str): simulation name
    """

    s_f = np.array([r["frequency"] for r in results])
    nports = len(results[0]["smatrix"])
    peak_inds = []
    # find peaks in diagonal entries
    for i in range(nports):
        s_mag = np.array([r["smatrix"][i][i][0] for r in results])
        peaksp, _ = find_peaks(s_mag)
        peaksm, _ = find_peaks(-s_mag)
        peak_inds += list(peaksp) + list(peaksm)
    peak_inds = list(set(peak_inds))
    f_peaks = s_f[peak_inds]

    available_vtus = list(sif_folder.glob("*.pvtu"))
    vtu_partitioned = len(available_vtus) != 0
    if not vtu_partitioned:
        available_vtus = sif_folder.glob("*.vtu")
    extension_l = len("_t0001.pvtu") if vtu_partitioned else len("_t0001.vtu")
    available_f = np.array(
        list({float(str(v.name)[len(simname) + 2 : -extension_l].replace("_", ".")) for v in available_vtus})
    )
    available_f = np.sort(available_f)

    saved_f = [available_f[0], available_f[-1]]
    for f_p in f_peaks:
        i = np.argmin(np.abs(available_f - f_p))
        saved_f.append(available_f[i])
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
