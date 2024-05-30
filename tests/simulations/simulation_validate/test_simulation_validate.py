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

import pytest
from kqcircuits.simulations.export.simulation_validate import ValidateSim
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.simulations.port import InternalPort, EdgePort
from kqcircuits.simulations.export.ansys.ansys_solution import (
    AnsysCurrentSolution,
    AnsysHfssSolution,
    AnsysEigenmodeSolution,
    AnsysVoltageSolution,
)
from kqcircuits.simulations.export.elmer.elmer_solution import (
    ElmerVectorHelmholtzSolution,
    ElmerCapacitanceSolution,
)
from kqcircuits.simulations.export.simulation_validate import ValidateSimError


@pytest.fixture
def mock_simulation(layout):
    simulation = Simulation(layout)
    simulation.name = "test_sim"
    return simulation


@pytest.mark.parametrize(
    "solution",
    [
        AnsysCurrentSolution(),
        AnsysHfssSolution(),
        AnsysVoltageSolution(),
        ElmerVectorHelmholtzSolution(),
        ElmerCapacitanceSolution(),
    ],
)
def test_has_no_ports_when_required(mock_simulation, solution):
    ports = [InternalPort(0, [0, 0, 1, 1])]
    mock_simulation.ports = ports
    validator = ValidateSim()
    validator.has_no_ports_when_required(mock_simulation, solution)


@pytest.mark.parametrize(
    "solution",
    [
        AnsysCurrentSolution(),
        AnsysHfssSolution(),
        AnsysVoltageSolution(),
        ElmerVectorHelmholtzSolution(),
        ElmerCapacitanceSolution(),
    ],
)
def test_raise_no_port_error_when_required(mock_simulation, solution):
    validator = ValidateSim()
    with pytest.raises(ValidateSimError) as expected_error:
        validator.has_no_ports_when_required(mock_simulation, solution)
    assert expected_error.value.validation_type == "has_no_ports_when_required"


@pytest.mark.parametrize("solution", [AnsysEigenmodeSolution(), AnsysVoltageSolution(), AnsysCurrentSolution()])
def test_has_edgeport_when_forbidden(mock_simulation, solution):
    ports = [InternalPort(0, [0, 0, 1, 1])]
    mock_simulation.ports = ports
    validator = ValidateSim()
    validator.has_edgeport_when_forbidden(mock_simulation, solution)


@pytest.mark.parametrize("solution", [AnsysEigenmodeSolution(), AnsysVoltageSolution(), AnsysCurrentSolution()])
def test_raise_edgeport_error_when_forbidden(mock_simulation, solution):
    ports = [EdgePort(0, [0, 0, 1, 1])]
    mock_simulation.ports = ports
    validator = ValidateSim()
    with pytest.raises(ValidateSimError) as expected_error:
        validator.has_edgeport_when_forbidden(mock_simulation, solution)
    assert expected_error.value.validation_type == "has_edgeport_when_forbidden"


@pytest.mark.parametrize(
    "solution", [AnsysHfssSolution(), AnsysEigenmodeSolution(), AnsysCurrentSolution(), AnsysVoltageSolution()]
)
def test_flux_integration_layer_exists_if_needed_passes_if_no_layers(mock_simulation, solution):
    validator = ValidateSim()
    validator.flux_integration_layer_exists_if_needed(mock_simulation, solution)


@pytest.mark.parametrize(
    "solution", [AnsysHfssSolution(), AnsysEigenmodeSolution(), AnsysCurrentSolution(), AnsysVoltageSolution()]
)
def test_flux_integration_layer_exists_if_needed_passes_if_has_needed_layer(mock_simulation, solution):
    validator = ValidateSim()
    mock_simulation.layers["flux_integration_layer"] = {"z": 0.0, "thickness": 0.0, "material": "non-pec"}
    solution.integrate_magnetic_flux = True
    validator.flux_integration_layer_exists_if_needed(mock_simulation, solution)


@pytest.mark.parametrize(
    "solution", [AnsysHfssSolution(), AnsysEigenmodeSolution(), AnsysCurrentSolution(), AnsysVoltageSolution()]
)
def test_flux_integration_layer_exists_if_needed_passes_if_has_needed_layer_and_others(mock_simulation, solution):
    validator = ValidateSim()
    mock_simulation.layers["flux_integration_layer"] = {"z": 0.0, "thickness": 0.0, "material": "non-pec"}
    mock_simulation.layers["thick_non_pec"] = {"z": 0.0, "thickness": 0.1, "material": "non-pec"}
    mock_simulation.layers["sheet_pec"] = {"z": 0.0, "thickness": 0.0, "material": "pec"}
    solution.integrate_magnetic_flux = True
    validator.flux_integration_layer_exists_if_needed(mock_simulation, solution)


@pytest.mark.parametrize(
    "solution", [AnsysHfssSolution(), AnsysEigenmodeSolution(), AnsysCurrentSolution(), AnsysVoltageSolution()]
)
def test_flux_integration_layer_passes_if_not_integrating_flux(mock_simulation, solution):
    validator = ValidateSim()
    solution.integrate_magnetic_flux = False
    mock_simulation.layers["thick_non_pec"] = {"z": 0.0, "thickness": 0.1, "material": "non-pec"}
    mock_simulation.layers["sheet_pec"] = {"z": 0.0, "thickness": 0.0, "material": "pec"}
    validator.flux_integration_layer_exists_if_needed(mock_simulation, solution)


@pytest.mark.parametrize(
    "solution", [AnsysHfssSolution(), AnsysEigenmodeSolution(), AnsysCurrentSolution(), AnsysVoltageSolution()]
)
def test_raise_flux_integration_error_if_has_no_needed_layer(mock_simulation, solution):
    validator = ValidateSim()
    solution.integrate_magnetic_flux = True
    with pytest.raises(ValidateSimError) as expected_error:
        validator.flux_integration_layer_exists_if_needed(mock_simulation, solution)
    assert expected_error.value.validation_type == "flux_integration_layer_exists_if_needed"


@pytest.mark.parametrize(
    "solution", [AnsysHfssSolution(), AnsysEigenmodeSolution(), AnsysCurrentSolution(), AnsysVoltageSolution()]
)
def test_raise_flux_integration_error_if_has_no_needed_layer_and_others(mock_simulation, solution):
    validator = ValidateSim()
    solution.integrate_magnetic_flux = True
    mock_simulation.layers["thick_non_pec"] = {"z": 0.0, "thickness": 0.1, "material": "non-pec"}
    mock_simulation.layers["sheet_pec"] = {"z": 0.0, "thickness": 0.0, "material": "pec"}
    with pytest.raises(ValidateSimError) as expected_error:
        validator.flux_integration_layer_exists_if_needed(mock_simulation, solution)
    assert expected_error.value.validation_type == "flux_integration_layer_exists_if_needed"
