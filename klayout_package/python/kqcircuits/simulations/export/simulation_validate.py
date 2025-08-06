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
import logging

from kqcircuits.simulations.simulation import Simulation
from kqcircuits.simulations.cross_section_simulation import CrossSectionSimulation
from kqcircuits.simulations.export.ansys.ansys_solution import (
    AnsysEigenmodeSolution,
    AnsysCurrentSolution,
    AnsysVoltageSolution,
    AnsysHfssSolution,
    AnsysCrossSectionSolution,
    AnsysSolution,
)
from kqcircuits.simulations.export.elmer.elmer_solution import (
    ElmerVectorHelmholtzSolution,
    ElmerCapacitanceSolution,
    ElmerCrossSectionSolution,
    ElmerEPR3DSolution,
)


def validate_simulation(simulation, solution):
    """Analyses Simulation and Solution objects and raises an error if inconsistencies in configuration are found.

    Args:
        simulation: A Simulation object.
        solution: A Solution object.
    Raises:
        Errors when validation criteria are not met.
    """
    simulation_and_solution_types_match(simulation, solution)
    flux_integration_layer_exists_if_needed(simulation, solution)
    london_penetration_depth_with_ansys(simulation, solution)

    # Run these checks only for 3D simulations
    if isinstance(simulation, Simulation):
        has_no_ports_when_required(simulation, solution)
        has_edgeport_when_forbidden(simulation, solution)
        check_partition_region_naming(simulation, solution)
        check_tls_sheet_generation(simulation)
        check_tls_sheets_by_solution(simulation, solution)


def simulation_and_solution_types_match(simulation, solution):
    """Validation check: ensures that a simulation and solution types match.
    Args:
        simulation: A Simulation object.
        solution: A Solution object.
    Raises:
        Errors when validation criteria are not met.
    """
    if isinstance(simulation, CrossSectionSimulation) != isinstance(
        solution, (ElmerCrossSectionSolution, AnsysCrossSectionSolution)
    ):
        raise ValidateSimError(
            f"Simulation '{simulation.name}' is incompatible with {type(solution)}",
            validation_type=simulation_and_solution_types_match.__name__,
        )


def has_no_ports_when_required(simulation, solution):
    """Validation check: ensures that a simulation object has ports when the solution type requires it.
    Args:
        simulation: A Simulation object.
        solution: A Solution object.
    Raises:
        Errors when validation criteria are not met.
    """
    port_names = get_port_names(simulation)
    sim_name = simulation.name
    if not port_names and isinstance(
        solution,
        (
            AnsysHfssSolution,
            AnsysVoltageSolution,
            AnsysCurrentSolution,
            ElmerVectorHelmholtzSolution,
            ElmerCapacitanceSolution,
        ),
    ):
        raise ValidateSimError(
            f"Simulation '{sim_name}' has no ports assigned. This is incompatible with {type(solution)}",
            validation_type=has_no_ports_when_required.__name__,
        )


def has_edgeport_when_forbidden(simulation, solution):
    """Validation check: ensure that if at least one "EdgePort" is present, some solution types can't be chosen.
    Args:
        simulation: A Simulation object.
        solution: A Solution object.
    Raises:
        Errors when validation criteria are not met.
    """
    port_names = get_port_names(simulation)
    sim_name = simulation.name
    if "EdgePort" in port_names and isinstance(
        solution,
        (
            AnsysEigenmodeSolution,
            AnsysVoltageSolution,
            AnsysCurrentSolution,
        ),
    ):
        raise ValidateSimError(
            f"Simulation '{sim_name}' has at least one 'EdgePort'. This is incompatible with {type(solution)}",
            validation_type=has_edgeport_when_forbidden.__name__,
        )


def london_penetration_depth_with_ansys(simulation, solution):
    """Validation check: ensure that london penetration depth is not used with AnsysSolutions.
    Args:
        simulation: A Simulation object.
        solution: A Solution object.
    Raises:
        Errors when validation criteria are not met.
    """
    if not isinstance(solution, AnsysSolution):
        return

    material_dict = simulation.get_material_dict()
    for material, material_def in material_dict.items():
        if "london_penetration_depth" in material_def:
            raise ValidateSimError(
                f"Material {material} of simulation '{simulation.name}' defines London penetration "
                "depth, but the feature is not supported with Ansys solution."
            )


def flux_integration_layer_exists_if_needed(simulation, solution):
    """Validation check related to the presence of layers and magnetic flux integration.
    Args:
        simulation: A Simulation object.
        solution: A Solution object.
    Raises:
        Errors when validation criteria are not met.
    """
    sim_name = simulation.name
    has_integrate_flux = hasattr(solution, "integrate_magnetic_flux")
    integrate_flux = solution.integrate_magnetic_flux if has_integrate_flux else False

    # Ensures that a non-metal layer with thickness == 0 exists in the setup when "integrate_magnetic_flux" is True.
    if integrate_flux:
        layers = simulation.layers
        has_flux_integration_layer = False
        for layer in layers.values():
            if layer.get("thickness") == 0 and not simulation.is_metal(layer.get("material")):
                has_flux_integration_layer = True
                break
        if not has_flux_integration_layer:
            raise ValidateSimError(
                f"Simulation '{sim_name}' has 'integrate_magnetic_flux = True' "
                + "but the integration layer is missing.",
                validation_type=flux_integration_layer_exists_if_needed.__name__,
            )


def check_partition_region_naming(simulation, solution):
    """Validation check: Ensures that partition region names do not end with each other.

    Also checks that region names don't contain any of the common EPR groups.
    """

    integrate_energies = isinstance(solution, ElmerEPR3DSolution) or getattr(solution, "integrate_energies", False)

    if integrate_energies:
        common_groups = ["ma", "ms", "sa", "substrate", "vacuum"]
        regions = [p.name.lower() for p in simulation.get_partition_regions()]
        for i, r1 in enumerate(regions):
            for g in common_groups:
                if g in r1:
                    raise ValidateSimError(
                        f'Partition region names can not contain the common EPR group names ("{g}" in "{r1}")',
                        validation_type=check_partition_region_naming.__name__,
                    )
            for j, r2 in enumerate(regions):
                if i != j and r1.endswith(r2):
                    raise ValidateSimError(
                        f'Partition region names can not be suffixes of each other ("{r1}" ends with "{r2}")',
                        validation_type=check_partition_region_naming.__name__,
                    )


def check_tls_sheet_generation(simulation):
    """Validation check: Ensures that TLS sheets are correctly generated and not overlapping with sheet metals"""
    if simulation.tls_sheet_approximation:
        if simulation.detach_tls_sheets_from_body:
            if not recursive_all(simulation.tls_layer_thickness, lambda x: x > 0):
                raise ValidateSimError(
                    "Can't detach tls sheets from body if no positive `tls_layer_thickness` is given",
                    validation_type=check_tls_sheet_generation.__name__,
                )
        elif not recursive_all(simulation.metal_height, lambda x: x > 0):  # not detach_tls_sheets_from_body
            raise ValidateSimError(
                "TLS sheets can't be generated to overlap with sheet metals. Either use `metal_height > 0` "
                + "or `detach_tls_sheets_from_body=True`",
                validation_type=check_tls_sheet_generation.__name__,
            )


def check_tls_sheets_by_solution(simulation, solution):
    """Validation check: enforces solution type specific restrictions on TLS sheets"""
    if isinstance(solution, ElmerEPR3DSolution):
        # non-zero metal thickness and TLS sheets on metal boundary
        if simulation.tls_sheet_approximation and simulation.detach_tls_sheets_from_body:
            raise ValidateSimError(
                "ElmerEPR3DSolution requires simulation parameter `detach_tls_sheets_from_body` to be set False",
                validation_type=check_tls_sheets_by_solution.__name__,
            )

        m = simulation.metal_height
        if not recursive_all(m, lambda x: x > 0):
            raise ValidateSimError(
                f"ElmerEPR3DSolution requires non-zero `metal_height` to be used (found: {m})",
                validation_type=check_tls_sheets_by_solution.__name__,
            )
    elif isinstance(solution, (ElmerCapacitanceSolution, ElmerVectorHelmholtzSolution)):
        # TLS sheets detached from metal
        if simulation.tls_sheet_approximation and not simulation.detach_tls_sheets_from_body:
            raise ValidateSimError(
                "ElmerCapacitanceSolution and ElmerVectorHelmholtzSolution require simulation parameter "
                + "`detach_tls_sheets_from_body` to be set True",
                validation_type=check_tls_sheets_by_solution.__name__,
            )
    elif isinstance(solution, AnsysSolution):
        # TLS sheets detached from metal
        if simulation.tls_sheet_approximation and not simulation.detach_tls_sheets_from_body:
            logging.warning("By convention `detach_tls_sheets_from_body` should be True in Ansys simulations")


# Following code is not validation checks but utilities used by validity checks


def recursive_all(l, condition):
    if not isinstance(l, list):
        return condition(l)
    else:
        return all((recursive_all(e, condition) for e in l))


def get_port_names(simulation):
    """Helper function that returns a list of port names in a Simulation object.
    Args:
        simulation: A Simulation object.
    Returns:
        port_names: A list of names related to the ports present in simulation.
    """
    port_list = simulation.ports if isinstance(simulation, Simulation) else []
    port_names = []
    for port in port_list:
        port_names.append(type(port).__name__)
    return port_names


class ValidateSimError(Exception):
    """Custom exception class for specific error handling."""

    def __init__(self, message, validation_type=None):
        super().__init__(message)
        self.validation_type = validation_type
