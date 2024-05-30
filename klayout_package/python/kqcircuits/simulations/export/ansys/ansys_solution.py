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
from dataclasses import dataclass
from typing import ClassVar
from kqcircuits.simulations.export.solution import Solution


@dataclass(kw_only=True, frozen=True)
class AnsysSolution(Solution):
    """
    A Base class for Ansys solution parameters

    Args:
        percent_refinement: Percentage of mesh refinement on each iteration.
        maximum_passes: Maximum number of iterations in simulation.
        minimum_passes: Minimum number of iterations in simulation.
        minimum_converged_passes: Determines how many iterations have to meet the stopping criterion to stop simulation.
        frequency_units: Units of frequency.
        mesh_size: Dictionary to determine manual mesh refinement on layers. Set key as the layer name and value as the
            maximal mesh element length inside the layer.
        simulation_flags: Optional export processing, given as list of strings. See Simulation Export in docs.
        ansys_project_template: path to the simulation template
    """

    ansys_tool: ClassVar[str] = ""
    percent_refinement: float = 30.0
    maximum_passes: int = 12
    minimum_passes: int = 1
    minimum_converged_passes: int = 1
    frequency_units: str = "GHz"
    mesh_size: dict | None = None
    simulation_flags: list[str] | None = None
    ansys_project_template: str | None = None

    def get_solution_data(self):
        """Return the solution data in dictionary form."""
        return {
            "solution_name": self.name,
            "ansys_tool": self.ansys_tool,
            "analysis_setup": {
                "percent_refinement": self.percent_refinement,
                "maximum_passes": self.maximum_passes,
                "minimum_passes": self.minimum_passes,
                "minimum_converged_passes": self.minimum_converged_passes,
                "frequency_units": self.frequency_units,
            },
            "mesh_size": {} if self.mesh_size is None else self.mesh_size,
            "simulation_flags": [] if self.simulation_flags is None else self.simulation_flags,
            **({} if self.ansys_project_template is None else {"ansys_project_template": self.ansys_project_template}),
        }


@dataclass(kw_only=True, frozen=True)
class AnsysHfssSolution(AnsysSolution):
    """
    Class for Ansys S-parameter (HFSS) solution parameters

    Args:
        frequency: Frequency for mesh refinement. To set up multifrequency analysis in HFSS use list of numbers.
        max_delta_s: Stopping criterion in HFSS simulation.
        sweep_enabled: Determines if HFSS frequency sweep is enabled.
        sweep_start: The lowest frequency in the sweep.
        sweep_end: The highest frequency in the sweep.
        sweep_count: Number of frequencies in the sweep.
        sweep_type: choices are "interpolating", "discrete" or "fast"
        capacitance_export: If True, the capacitance matrices are exported from S-parameter simulation
        integrate_energies: Calculate energy integrals over each layer and save them into a file
        integrate_magnetic_flux: Integrate magnetic fluxes through each non-pec sheet and save them into a file
    """

    ansys_tool: ClassVar[str] = "hfss"
    frequency: float | list[float] = 5
    max_delta_s: float = 0.1
    sweep_enabled: bool = True
    sweep_start: float = 0
    sweep_end: float = 10
    sweep_count: int = 101
    sweep_type: str = "interpolating"
    capacitance_export: bool = False
    integrate_energies: bool = False
    integrate_magnetic_flux: bool = False

    def get_solution_data(self):
        """Return the solution data in dictionary form."""
        data = super().get_solution_data()
        return {
            **data,
            "analysis_setup": {
                **data["analysis_setup"],
                "frequency": self.frequency,
                "max_delta_s": self.max_delta_s,
                "sweep_enabled": self.sweep_enabled,
                "sweep_start": self.sweep_start,
                "sweep_end": self.sweep_end,
                "sweep_count": self.sweep_count,
                "sweep_type": self.sweep_type,
            },
            "capacitance_export": self.capacitance_export,
            "integrate_energies": self.integrate_energies,
            "integrate_magnetic_flux": self.integrate_magnetic_flux,
        }


@dataclass(kw_only=True, frozen=True)
class AnsysQ3dSolution(AnsysSolution):
    """
    Class for Ansys capacitance matrix (Q3D) solution parameters

    Args:
        frequency: Nominal solution frequency (has no effect on capacitance matrix at the moment).
        percent_error: Stopping criterion in Q3D simulation.
    """

    ansys_tool: ClassVar[str] = "q3d"
    frequency: float = 5
    percent_error: float = 1

    def get_solution_data(self):
        """Return the solution data in dictionary form."""
        data = super().get_solution_data()
        return {
            **data,
            "analysis_setup": {
                **data["analysis_setup"],
                "frequency": self.frequency,
                "percent_error": self.percent_error,
            },
        }


@dataclass(kw_only=True, frozen=True)
class AnsysEigenmodeSolution(AnsysSolution):
    """
    Class for Ansys eigenmode solution parameters

    Args:
        min_frequency: Minimum allowed eigenmode frequency
        max_delta_f: Maximum allowed relative difference in eigenfrequency (%)
        n_modes: Number of eigenmodes to solve.
        integrate_energies: Calculate energy integrals over each layer and save them into a file
        integrate_magnetic_flux: Integrate magnetic fluxes through each non-pec sheet and save them into a file
    """

    ansys_tool: ClassVar[str] = "eigenmode"
    min_frequency: float = 0.1
    max_delta_f: float = 0.1
    n_modes: int = 2
    integrate_energies: bool = False
    integrate_magnetic_flux: bool = False

    def get_solution_data(self):
        """Return the solution data in dictionary form."""
        data = super().get_solution_data()
        return {
            **data,
            "analysis_setup": {
                **data["analysis_setup"],
                "min_frequency": self.min_frequency,
                "max_delta_f": self.max_delta_f,
                "n_modes": self.n_modes,
            },
            "integrate_energies": self.integrate_energies,
            "integrate_magnetic_flux": self.integrate_magnetic_flux,
        }


@dataclass(kw_only=True, frozen=True)
class AnsysCurrentSolution(AnsysSolution):
    """
    Class for Ansys current excitation solution parameters

    Args:
        frequency: Frequency of alternating current excitation.
        max_delta_e: Stopping criterion in current excitation simulation.
        integrate_energies: Calculate energy integrals over each layer and save them into a file
        integrate_magnetic_flux: Integrate magnetic fluxes through each non-pec sheet and save them into a file
    """

    ansys_tool: ClassVar[str] = "current"
    frequency: float = 0.1
    max_delta_e: float = 0.1
    integrate_energies: bool = False
    integrate_magnetic_flux: bool = False

    def get_solution_data(self):
        """Return the solution data in dictionary form."""
        data = super().get_solution_data()
        return {
            **data,
            "analysis_setup": {
                **data["analysis_setup"],
                "frequency": self.frequency,
                "max_delta_e": self.max_delta_e,
            },
            "integrate_energies": self.integrate_energies,
            "integrate_magnetic_flux": self.integrate_magnetic_flux,
        }


@dataclass(kw_only=True, frozen=True)
class AnsysVoltageSolution(AnsysSolution):
    """
    Class for Ansys voltage excitation solution parameters

    Args:
        frequency: Frequency of alternating voltage excitation.
        max_delta_e: Stopping criterion in voltage excitation simulation.
        integrate_energies: Calculate energy integrals over each layer and save them into a file
        integrate_magnetic_flux: Integrate magnetic fluxes through each non-pec sheet and save them into a file
    """

    ansys_tool: ClassVar[str] = "voltage"
    frequency: float = 5
    max_delta_e: float = 0.1
    integrate_energies: bool = False
    integrate_magnetic_flux: bool = False

    def get_solution_data(self):
        """Return the solution data in dictionary form."""
        data = super().get_solution_data()
        return {
            **data,
            "analysis_setup": {
                **data["analysis_setup"],
                "frequency": self.frequency,
                "max_delta_e": self.max_delta_e,
            },
            "integrate_energies": self.integrate_energies,
            "integrate_magnetic_flux": self.integrate_magnetic_flux,
        }


@dataclass(kw_only=True, frozen=True)
class AnsysCrossSectionSolution(AnsysSolution):
    """
    Class for Ansys cross-section solution parameters. Produces capacitance and inductance per unit length.

    Args:
        frequency: Nominal solution frequency (has no effect on results at the moment).
        percent_error: Stopping criterion in cross-section simulation.
        integrate_energies: Calculate energy integrals over each layer and save them into a file
    """

    ansys_tool: ClassVar[str] = "cross-section"
    frequency: float = 5
    percent_error: float = 0.01
    integrate_energies: bool = False

    def get_solution_data(self):
        """Return the solution data in dictionary form."""
        data = super().get_solution_data()
        return {
            **data,
            "analysis_setup": {
                **data["analysis_setup"],
                "frequency": self.frequency,
                "percent_error": self.percent_error,
            },
            "integrate_energies": self.integrate_energies,
        }


def get_ansys_solution(ansys_tool="hfss", **solution_params):
    """Returns an instance of AnsysSolution subclass.

    Args:
        ansys_tool: Determines the subclass of AnsysSolution.
        solution_params: Arguments passed for AnsysSolution subclass.
    """
    for c in [
        AnsysHfssSolution,
        AnsysQ3dSolution,
        AnsysEigenmodeSolution,
        AnsysCurrentSolution,
        AnsysVoltageSolution,
        AnsysCrossSectionSolution,
    ]:
        if ansys_tool == c.ansys_tool:
            return c(**solution_params)
    raise ValueError(f"No AnsysSolution found for ansys_tool={ansys_tool}.")
