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
from kqcircuits.simulations.export.ansys.ansys_solution import (
    AnsysEigenmodeSolution,
    AnsysCurrentSolution,
    AnsysVoltageSolution,
    AnsysHfssSolution,
)
from kqcircuits.simulations.export.elmer.elmer_solution import ElmerVectorHelmholtzSolution, ElmerCapacitanceSolution


class ValidateSim:
    """Validation class that contains consistency checks."""

    def has_no_ports_when_required(self, simulation, solution):
        """Validation check: ensures that a simulation object has ports when the solution type requires it.
        Args:
            simulations: A Simulation object.
            solutions: A Solution object.
        Raises:
            Errors when validation criteria are not met.
        """
        port_names = get_port_names(simulation)
        sim_name = simulation.name
        if not port_names and type(solution) in [
            AnsysHfssSolution,
            AnsysVoltageSolution,
            AnsysCurrentSolution,
            ElmerVectorHelmholtzSolution,
            ElmerCapacitanceSolution,
        ]:
            raise ValidateSimError(
                f"Simulation '{sim_name}' has no ports assigned. This is incompatible with {type(solution)}",
                validation_type=self.has_no_ports_when_required.__name__,
            )

    def has_edgeport_when_forbidden(self, simulation, solution):
        """Validation check: ensure that if at least one "EdgePort" is present, some solution types can't be chosen.
        Args:
            simulations: A Simulation object.
            solutions: A Solution object.
        Raises:
            Errors when validation criteria are not met.
        """
        port_names = get_port_names(simulation)
        sim_name = simulation.name
        if "EdgePort" in port_names and type(solution) in [
            AnsysEigenmodeSolution,
            AnsysVoltageSolution,
            AnsysCurrentSolution,
        ]:
            raise ValidateSimError(
                f"Simulation '{sim_name}' has at least one 'EdgePort'. This is incompatible with {type(solution)}",
                validation_type=self.has_edgeport_when_forbidden.__name__,
            )

    def flux_integration_layer_exists_if_needed(self, simulation, solution):
        """Validation check related to the presence of layers and magnetic flux integration.
        Args:
            simulation: A Simulation object.
        Raises:
            Errors when validation criteria are not met.
        """
        sim_name = simulation.name
        has_integrate_flux = hasattr(solution, "integrate_magnetic_flux")
        integrate_flux = solution.integrate_magnetic_flux if has_integrate_flux else False

        # Ensures that a layer with thickness == 0 and a material != "pec"
        # exists in the setup when "integrate_magnetic_flux" is True.
        if integrate_flux:
            layers = simulation.layers
            has_flux_integration_layer = False
            for layer in layers.values():
                if layer.get("thickness", -1) == 0 and layer.get("material", "") != "pec":
                    has_flux_integration_layer = True
                    break
            if not has_flux_integration_layer:
                raise ValidateSimError(
                    f"Simulation '{sim_name}' has 'integrate_magnetic_flux = True' "
                    + "but the integration layer is missing.",
                    validation_type=self.flux_integration_layer_exists_if_needed.__name__,
                )


def get_port_names(simulation):
    """Helper function that returns a list of port names in a Simulation object.
    Args:
        simulation: A Simulation object.
    Returns:
        port_names: A list of names related to the ports present in simulation.
    """
    port_list = simulation.ports
    port_names = []
    for port in port_list:
        port_names.append(type(port).__name__)
    return port_names


class ValidateSimError(Exception):
    """Custom exception class for specific error handling."""

    def __init__(self, message, validation_type=None):
        super().__init__(message)
        self.validation_type = validation_type
