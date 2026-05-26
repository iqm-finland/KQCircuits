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
        mesh_size: Dictionary to determine the mesh refinement. The keys (string) denote the entities where to apply the
            refinement and values (double) denote the maximal length of the mesh elements.
            Optionally, the values can be set as a lists of doubles. Then, value[0] is the maximal mesh element length
            inside at the entity and its expansion, value[1] is expansion distance in which the maximal mesh element
            length is constant (default=value[0]), and value[2] is the slope of the increase in the maximal mesh element
            length outside the entity.
            The key can be a single layer name, or it can consist of multiple layer names separated with the & symbol,
            meaning the entity will be an intersection of listed layers. Optionally, one can use a pattern for layer
            names with the * symbol representing any string in a layer name. The ! symbol before the layer name or
            pattern means that the complement of layer(s) is used instead.
            The key 'global_max' is reserved for setting global maximal element length.
            For example, if the dictionary is {'substrate*': 10, 'substrate*&vacuum': [2, 5], 'global_max': 100}, then
            the maximal mesh element length is 10 inside the substrates and 2 on region which is less than 5 units away
            from any substrate-vacuum interface. Outside these regions, the mesh element size can increase up to 100.
        mesh_optimizer: Dictionary to determine mesh optimization, or None to ignore optimization. The dictionary can
            contain keywords 'method', 'force', 'niter' and 'dimTags'. See Gmsh manual (gmsh.model.mesh.optimize) for
            details. The default value is {'method': 'Netgen'}.
        mesh_options: Dictionary of additional meshing options. The key of every item must be the full name of the gmsh
            option and the value is then the corresponding option value to be set. For a list of available options,
            refer to https://gmsh.info/doc/texinfo/gmsh.html#Gmsh-options.
        vtu_output: Output vtu files to view fields in Paraview.
                    Turning this off will make the simulations slightly faster
        save_elmer_data: Save the full Elmer model after simulation. This can be used to restart the simulation
                         or extract result field values as a post-processing step.
        min_mesh_quality: If the initial Gmsh mesh contains elements with quality below this limit, a local mesh
            refinement around those elements is applied. This causes the whole mesh to be recomputed and can therefore
            cause performance issues if set too high. The aim of the remeshing is to prevent fatal errors due
            to degenerate elements in Elmer. The default value of 5e-7 is determined experimentally and might need
            adjustment. Setting this to 0 disables the feature.

        linear_system_method: Method for solving the FEM linear system of equations in Elmer. For iterative methods use
                "GCR", "bicgstab" or any other iterative solver mentioned in ElmerSolver manual section 4.3.1.
                For direct methods "umfpack", "mumps", "pardiso" or "superlu" can be used, but note that other
                methods than "umfpack" require Elmer to be explicitly compiled with the corresponding solver software.
                If a direct method is used the parameters "convergence_tolerance", "max_iterations",
                "linear_system_preconditioning", "abort_not_converged" and all multigrid options ("mg_*") are redundant.
        convergence_tolerance: Convergence tolerance of the iterative solver.
        max_iterations: Maximum number of iterations for the iterative solver.
        linear_system_preconditioning: Choice of preconditioner before using an iterative linear system solver.
                        If using multigrid, the preconditioning is applied on the lowest iteration level.
        abort_not_converged: Stop Elmer execution immediately if an iterative linear system solver fails to reach
            convergence. If False, a warning is printed after the simulation finishes.
        parent_solution: parent solution name to be used together with Simulation.parent_simulation

        use_multigrid_solver: Use hierarchical iterative multigrid solver.
        mg_smoother: Choice of smoother in multigrid solver. Tested options for electrostatic simulations are
                     "SGS", "CG" and "wjacobi". VectorHelmholtzSolution support "cjacobi".
        mg_smoothing_iterations: Number of smoothing iterations.
        mg_relaxation_factor: Parameter for tuning the smoothers "wjacobi" and "cjacobi".
        mg_lowest_method: Linear system method used for solving the smallest/lowest order linear system in multigrid.
                          See `linear_system_method` for options.

    """

    tool: ClassVar[str] = ""
    # Adaptive meshing settings
    percent_error: float = 0.005
    max_error_scale: float = 2.0
    max_outlier_fraction: float = 1e-3
    maximum_passes: int = 1
    minimum_passes: int = 1
    # general
    is_axisymmetric: bool = False
    mesh_levels: int = 1
    mesh_size: dict = field(default_factory=dict)
    mesh_optimizer: dict | None = field(default_factory=lambda: {"method": "Netgen"})
    mesh_options: dict = field(default_factory=dict)
    vtu_output: bool = True
    save_elmer_data: bool = False
    min_mesh_quality: float = 5e-7

    linear_system_method: str = "GCR"
    convergence_tolerance: float = 1.0e-9
    max_iterations: int = 500
    linear_system_preconditioning: str = "ILU0"
    abort_not_converged: bool = False
    parent_solution: str = ""

    # Multigrid solver settings
    use_multigrid_solver: bool = True
    mg_smoother: str = "SGS"
    mg_smoothing_iterations: int | None = None  # default depends on mg_smoother
    mg_relaxation_factor: float = 0.28
    mg_lowest_method: str = "CG"

    def get_solution_data(self):
        """Return the solution data in dictionary form."""
        sol_dict = {**self.__dict__, "tool": self.tool}
        sol_dict["solution_name"] = sol_dict.pop("name")
        return sol_dict

    def __post_init__(self):
        """Used for automatically setting default values depending on other parameters"""
        if self.mg_smoothing_iterations is None:
            defaults = {"sgs": 1, "wjacobi": 4, "cjacobi": 4, "cg": 12}
            object.__setattr__(self, "mg_smoothing_iterations", defaults.get(self.mg_smoother.lower(), 1))
        if self.mesh_optimizer == {}:
            object.__setattr__(self, "mesh_optimizer", {"method": "Netgen"})


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
        quadratic_approximation: Use edge finite elements of second order. Otherwise use first order.
                                 If False, a direct solver such as `linear_system_method=zmumps` should be used.
        second_kind_basis: Use Nedelec finite elements of second kind.

        use_av: Use a formulation of VectorHelmHoltz equation based on potentials A-V instead of electric field E.
                For details see https://www.nic.funet.fi/pub/sci/physics/elmer/doc/ElmerModelsManual.pdf
                WARNING: This option is experimental and might lead to poor convergence.
        conductivity: Adds a specified film conductivity on metal boundaries. Applies only when `use_av=True`
        nested_iteration: Enables alternative nested iterative solver to be used. Applies only when `use_av=True`
    """

    tool: ClassVar[str] = "wave_equation"

    frequency: float | list[float] = 5
    frequency_batch: int = 3
    sweep_type: str = "explicit"
    max_delta_s: float = 0.01
    london_penetration_depth: float = 0
    quadratic_approximation: bool = True
    second_kind_basis: bool = False
    # Experimental options
    use_av: bool = False
    conductivity: float = 0
    nested_iteration: bool = False

    # override defaults
    mg_smoother: str = "cjacobi"
    convergence_tolerance: float = 1.0e-6
    max_iterations: int = 200
    linear_system_preconditioning: str = "none"
    mg_lowest_method: str = "zmumps"

    def __post_init__(self):
        """Cast frequency to list. Automatically called after init"""
        super().__post_init__()
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
        integrate_energies: Calculate energy integrals over each object. Used in EPR simulations
        electric_infinity_bc: effectively extend the model domain to infinity using spherical boundary conditions
    """

    tool: ClassVar[str] = "capacitance"

    p_element_order: int = 3
    integrate_energies: bool = False
    electric_infinity_bc: bool = False


@dataclass(kw_only=True, frozen=True)
class ElmerCrossSectionSolution(ElmerSolution):
    """
    Class for Elmer cross-section solution parameters. By default both 2D Capacitance and 2D Inductance simulation
    will be run when using this Solution type. The linear system solver parameters are hardcoded for the inductance
    simulation and the solver related parameters in ElmerSolution only have effect on the Capacitance simulation.

    Args:
        p_element_order: polynomial order of p-elements
        integrate_energies: Calculate energy integrals over each object. Used in EPR simulations
        boundary_conditions: Parameters to determine boundary conditions for potential on the edges
                             of simulation box. Supported keys are `xmin` , `xmax` ,`ymin` and `ymax`
                             Example: `boundary_conditions = {"xmin": {"potential": 0}}`
        run_inductance_sim: Can be used to skip running the inductance simulation and just do 2D capacitance.
                            No impendance can then be calculated but useful for making EPR simulations faster
        voltage_excitations: Can be used to excite signals with arbitrary voltages, instead of 1V. If this parameter is
                             used, no capacitances will be computed.
        electric_infinity_bc: effectively extend the model domain to infinity using spherical boundary conditions
    """

    tool: ClassVar[str] = "cross-section"

    p_element_order: int = 3
    integrate_energies: bool = False
    boundary_conditions: dict = field(default_factory=dict)
    run_inductance_sim: bool = True
    voltage_excitations: list[float] | None = None
    electric_infinity_bc: bool = False


@dataclass(kw_only=True, frozen=True)
class ElmerEPR3DSolution(ElmerSolution):
    """
    Class for Elmer 3D EPR simulations. Similar to electrostatics simulations done with ElmerCapacitanceSolution,
    but supports separating energies by PartitionRegions. Always reports energies for each layer.

    Args:
        p_element_order: polynomial order of p-elements
        voltage_excitations: Can be used to excite signals with arbitrary voltages, instead of 1V. If this parameter is
                             used, no capacitances will be computed.
        electric_infinity_bc: effectively extend the model domain to infinity using spherical boundary conditions
    """

    tool: ClassVar[str] = "epr_3d"

    p_element_order: int = 3
    voltage_excitations: list[float] | None = None
    electric_infinity_bc: bool = False


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
