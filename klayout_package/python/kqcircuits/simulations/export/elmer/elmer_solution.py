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
from dataclasses import dataclass, field
from typing import ClassVar
from kqcircuits.simulations.export.solution import Solution


@dataclass(kw_only=True, frozen=True)
class ElmerSolution(Solution):
    """
    A Base class for Elmer Solution parameters

    Args:
        percent_error: Stopping criterion in adaptive meshing.
        max_error_scale: Maximum element error, relative to percent_error, allowed in individual elements.
        max_outlier_fraction: Maximum fraction of outliers from the total number of elements
        maximum_passes: Maximum number of adaptive meshing iterations.
        minimum_passes: Minimum number of adaptive meshing iterations.
        is_axisymmetric: Simulate with Axi Symmetric coordinates along :math:`y\\Big|_{x=0}` (Default: False)
        mesh_levels: If set larger than 1 Elmer will make the mesh finer by dividing each element
                     into 2^(dim) elements mesh_levels times. Default 1.
        mesh_size: Dictionary to determine mesh size where key (string) denotes material and value (double) denotes the
            maximal length of mesh element. Additional mesh size terms can be determined, if the value type is
            list. Then, term[0] is the maximal mesh element length inside at the entity and its expansion,
            term[1] is expansion distance in which the maximal mesh element length is constant (default=term[0]),
            and term[2] is the slope of the increase in the maximal mesh element length outside the entity.
            To refine material interface the material names by should be separated by '&' in the key. Key 'global_max'
            is reserved for setting global maximal element length. For example, if the dictionary is given as
            {'substrate': 10, 'substrate&vacuum': [2, 5], 'global_max': 100}, then the maximal mesh element length is 10
            inside the substrate and 2 on region which is less than 5 units away from the substrate-vacuum interface.
            Outside these regions, the mesh element size can increase up to 100. mesh_size can contain a sub dict
            called optimize that contains keys: 'method', 'force', 'niter' and 'dimTags', see Gmsh manual for details,
            api used is gmsh.model.mesh.optimize. By default there is no optimization, but if "optimize" key exists,
            then "Netgen" is used by default as method.
        vtu_output: Output vtu files to view fields in Paraview.
                    Turning this off will make the simulations slightly faster

    """

    tool: ClassVar[str] = ""

    percent_error: float = 0.005
    max_error_scale: float = 2.0
    max_outlier_fraction: float = 1e-3
    maximum_passes: int = 1
    minimum_passes: int = 1
    is_axisymmetric: bool = False
    mesh_levels: int = 1
    mesh_size: dict = field(default_factory=dict)
    vtu_output: bool = True

    def get_solution_data(self):
        """Return the solution data in dictionary form."""
        sol_dict = {**self.__dict__, "tool": self.tool}
        sol_dict["solution_name"] = sol_dict.pop("name")
        return sol_dict


@dataclass(kw_only=True, frozen=True)
class ElmerVectorHelmholtzSolution(ElmerSolution):
    """
    Class for Elmer wave-equation solution parameters

    Args:
        frequency: Units are in GHz. Give a list of frequencies if using interpolating sweep.
        frequency_batch: Number of frequencies calculated between each round of fitting in interpolating sweep
        sweep_type: Type of frequency sweep. Options "explicit" and "interpolating".
        max_delta_s: Convergence tolerance in interpolating sweep
        london_penetration_depth: Allows supercurrent to flow on the metal boundaries within a layer
                                  of thickness `london_penetration_depth`
        quadratic_approximation: Use edge finite elements of second degree
        second_kind_basis: Use Nedelec finite elements of second kind

        use_av: Use a formulation of VectorHelmHoltz equation based on potentials A-V instead of electric field E.
                For details see https://www.nic.funet.fi/pub/sci/physics/elmer/doc/ElmerModelsManual.pdf
                WARNING: This option is experimental and might lead to poor convergence.
        conductivity: Adds a specified film conductivity on metal boundaries. Applies only when `use_av=True`
        nested_iteration: Enables alternative nested iterative solver to be used. Applies only when `use_av=True`
        convergence_tolerance: Convergence tolerance of the iterative solver. Applies only when `use_av=True`
        max_iterations: Maximum number of iterations for the iterative solver.
                        Applies only when `use_av=True` and only to the main solver (not to calc fields or port solver)
    """

    tool: ClassVar[str] = "wave_equation"

    frequency: float | list[float] = 5
    frequency_batch: int = 3
    sweep_type: str = "explicit"
    max_delta_s: float = 0.01
    london_penetration_depth: float = 0
    quadratic_approximation: bool = False
    second_kind_basis: bool = False

    use_av: bool = False
    conductivity: float = 0
    nested_iteration: bool = False
    convergence_tolerance: float = 1.0e-10
    max_iterations: int = 2000

    def __post_init__(self):
        """Cast frequency to list. Automatically called after init"""
        if isinstance(self.frequency, (float, int)):
            # hack to modify the attributes of frozen dataclass
            object.__setattr__(self, "frequency", [float(self.frequency)])
        elif not isinstance(self.frequency, list):
            object.__setattr__(self, "frequency", list(self.frequency))


@dataclass(kw_only=True, frozen=True)
class ElmerCapacitanceSolution(ElmerSolution):
    """
    Class for Elmer capacitance solution parameters

    Args:
        p_element_order: polynomial order of p-elements
        linear_system_method: Options: 1. Iterative methods "mg" (multigrid), "bicgstab" or any other iterative
                solver mentioned in ElmerSolver manual section 4.3.1. 2. Direct methods "umfpack", "mumps", "pardiso" or
                "superlu". Note that the use of other methods than "umfpack" requires Elmer to be explicitly compiled
                with the corresponding solver software. If a direct method is used the parameters
                "convergence_tolerance", "max_iterations" and "linear_system_preconditioning" are redundant
        integrate_energies: Calculate energy integrals over each object. Used in EPR simulations
        convergence_tolerance: Convergence tolerance of the iterative solver.
        max_iterations: Maximum number of iterations for the iterative solver.
        linear_system_preconditioning: Choice of preconditioner before using an iterative linear system solver
    """

    tool: ClassVar[str] = "capacitance"

    p_element_order: int = 3
    linear_system_method: str = "mg"
    integrate_energies: bool = False
    convergence_tolerance: float = 1.0e-9
    max_iterations: int = 500
    linear_system_preconditioning: str = "ILU0"


@dataclass(kw_only=True, frozen=True)
class ElmerCrossSectionSolution(ElmerSolution):
    """
    Class for Elmer cross-section solution parameters.
    By default both 2D Capacitance and 2D Inductance simulation will be run when using this

    Args:
        p_element_order: polynomial order of p-elements
        linear_system_method: Options: 1. Iterative methods "mg" (multigrid), "bicgstab" or any other iterative
                solver mentioned in ElmerSolver manual section 4.3.1. 2. Direct methods "umfpack", "mumps", "pardiso" or
                "superlu". Note that the use of other methods than "umfpack" requires Elmer to be explicitly compiled
                with the corresponding solver software. If a direct method is used the parameters
                "convergence_tolerance", "max_iterations" and "linear_system_preconditioning" are redundant
        integrate_energies: Calculate energy integrals over each object. Used in EPR simulations
        boundary_conditions: Parameters to determine boundary conditions for potential on the edges
                             of simulation box. Supported keys are `xmin` , `xmax` ,`ymin` and `ymax`
                             Example: `boundary_conditions = {"xmin": {"potential": 0}}`
        convergence_tolerance: Convergence tolerance of the iterative solver.
                               Applies only to capacitance part of the simulation
        max_iterations: Maximum number of iterations for the iterative solver.
                        Applies only to capacitance part of the simulation
        run_inductance_sim: Can be used to skip running the inductance simulation and just do 2D capacitance.
                            No impendance can then be calculated but useful for making EPR simulations faster
        linear_system_preconditioning: Choice of preconditioner before using an iterative linear system solver
    """

    tool: ClassVar[str] = "cross-section"

    p_element_order: int = 3
    linear_system_method: str = "mg"
    integrate_energies: bool = False
    boundary_conditions: dict = field(default_factory=dict)
    convergence_tolerance: float = 1.0e-9
    max_iterations: int = 500
    run_inductance_sim: bool = True
    linear_system_preconditioning: str = "ILU0"


@dataclass(kw_only=True, frozen=True)
class ElmerEPR3DSolution(ElmerSolution):
    """
    Class for Elmer 3D EPR simulations. Similar to electrostatics simulations done with ElmerCapacitanceSolution,
    but supports separating energies by PartitionRegions. Produces no capacitance matrix if p_element_order==1.
    Always reports energies for each layer.

    Args:
        p_element_order: polynomial order of p-elements
        linear_system_method: Options: 1. Iterative methods "mg" (multigrid), "bicgstab" or any other iterative
                solver mentioned in ElmerSolver manual section 4.3.1. 2. Direct methods "umfpack", "mumps", "pardiso" or
                "superlu". Note that the use of other methods than "umfpack" requires Elmer to be explicitly compiled
                with the corresponding solver software. If a direct method is used the parameters
                "convergence_tolerance", "max_iterations" and "linear_system_preconditioning" are redundant
        convergence_tolerance: Convergence tolerance of the iterative solver.
        max_iterations: Maximum number of iterations for the iterative solver.
        linear_system_preconditioning: Choice of preconditioner before using an iterative linear system solver
        sequential_signal_excitation: If True, each separate signal is excited sequentially while grounding the others.
                                      If False, runs a single simulation with all signals set to 1V.

    """

    tool: ClassVar[str] = "epr_3d"

    p_element_order: int = 3
    linear_system_method: str = "mg"
    convergence_tolerance: float = 1.0e-9
    max_iterations: int = 1000
    linear_system_preconditioning: str = "ILU0"
    sequential_signal_excitation: bool = True


def get_elmer_solution(tool="capacitance", **solution_params):
    """Returns an instance of ElmerSolution subclass.

    Args:
        tool: Determines the subclass of ElmerSolution.
        solution_params: Arguments passed for  ElmerSolution subclass.
    """
    for c in [ElmerVectorHelmholtzSolution, ElmerCapacitanceSolution, ElmerCrossSectionSolution, ElmerEPR3DSolution]:
        if tool == c.tool:
            return c(**solution_params)
    raise ValueError(f"No ElmerSolution found for tool={tool}.")
