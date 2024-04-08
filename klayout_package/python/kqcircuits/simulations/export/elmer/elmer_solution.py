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
from dataclasses import dataclass, field
from typing import Union, List
from kqcircuits.simulations.export.solution import Solution


@dataclass
class ElmerSolution(Solution):
    """
    A Base class for Elmer Solution parameters

    Args:
        tool: Available: "capacitance", "wave_equation" and "cross-section"
        linear_system_method: Available: 'bicgstab', 'mg'. Currently only applies to Capacitance Solver
        p_element_order: polynomial order of p-elements
        percent_error: Stopping criterion in adaptive meshing.
        max_error_scale: Maximum element error, relative to percent_error, allowed in individual elements.
        max_outlier_fraction: Maximum fraction of outliers from the total number of elements
        maximum_passes: Maximum number of adaptive meshing iterations.
        minimum_passes: Minimum number of adaptive meshing iterations.
        is_axisymmetric: Simulate with Axi Symmetric coordinates along :math:`y\\Big|_{x=0}` (Default: False)
        mesh_levels: If set larger than 1 Elmer will make the mesh finer by dividing each element
                          into 2^(dim) elements mesh_levels times. Default 1.
        frequency: Units are in GHz. Give a list of frequencies if using interpolating sweep.
        frequency_batch: Number of frequencies calculated between each round of fitting in interpolating sweep
        sweep_type: Type of frequency sweep. Options "explicit" and "interpolating".
        max_delta_s: Convergence tolerance in interpolating sweep
        boundary_conditions: Parameters to determine boundary conditions
        integrate_energies: Calculate energy integrals over each object. Used in EPR simulations
        mesh_levels: If set larger than 1 Elmer will make the mesh finer by dividing each element
                          into 2^(dim) elements mesh_levels times. Default 1.
        mesh_size: Parameters to determine mesh element sizes
        solver_options: Can be used to set experimental solver options for Elmer wave-equation tool.
                        Supports the options `use_av` (bool), `london_penetration_depth` (float),
                        `conductivity` (float),`nested_iteration` (bool), `convergence_tolerance` (float),
                        `max_iterations` (int), `quadratic_approximation` (bool), `second_kind_basis` (bool)

    """

    tool: str = "capacitance"  # to be ClassVar
    linear_system_method: str = "bicgstab"
    p_element_order: int = 3
    percent_error: float = 0.005
    max_error_scale: float = 2.0
    max_outlier_fraction: float = 1e-3
    maximum_passes: int = 1
    minimum_passes: int = 1
    is_axisymmetric: bool = False
    mesh_levels: int = 1
    frequency: Union[float, List[float]] = 5
    frequency_batch: int = 3
    sweep_type: str = "explicit"
    max_delta_s: float = 0.01
    boundary_conditions: dict = field(default_factory=dict)
    integrate_energies: bool = False
    mesh_levels: int = 1
    mesh_size: dict = field(default_factory=dict)
    solver_options: dict = field(default_factory=dict)

    def __post_init__(self):
        """Cast frequency to list. Automatically called after init"""
        if isinstance(self.frequency, (float, int)):
            self.frequency = [self.frequency]
        elif not isinstance(self.frequency, list):
            self.frequency = list(self.frequency)

    def get_solution_data(self):
        """Return the solution data in dictionary form."""
        sol_dict = {**self.__dict__}
        sol_dict["solution_name"] = sol_dict.pop("name")
        return sol_dict
