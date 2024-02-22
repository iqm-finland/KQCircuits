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
from dataclasses import dataclass
from typing import Optional, Union, List


@dataclass
class AnsysSolution:  # TODO: subclass from Solution
    """
    A Base class for Ansys Solution and export parameters

    Args:
        name: name of the solution
        ansys_tool: Determines whether to use 'hfss' (s-parameters), 'q3d', 'current', 'voltage', or 'eigenmode'.
        frequency_units: Units of frequency.
        frequency: Frequency for mesh refinement. To set up multifrequency analysis in HFSS use list of numbers.
        max_delta_s: Stopping criterion in HFSS simulation.
        max_delta_e: Stopping criterion in current or voltage excitation simulation.
        percent_error: Stopping criterion in Q3D simulation.
        percent_refinement: Percentage of mesh refinement on each iteration.
        maximum_passes: Maximum number of iterations in simulation.
        minimum_passes: Minimum number of iterations in simulation.
        minimum_converged_passes: Determines how many iterations have to meet the stopping criterion to stop simulation.
        sweep_enabled: Determines if HFSS frequency sweep is enabled.
        sweep_start: The lowest frequency in the sweep.
        sweep_end: The highest frequency in the sweep.
        sweep_count: Number of frequencies in the sweep.
        sweep_type: choices are "interpolating", "discrete" or "fast"
        max_delta_f: Maximum allowed relative difference in eigenfrequency (%). Used when ``ansys_tool`` is *eigenmode*.
        n_modes: Number of eigenmodes to solve. Used when ``ansys_tool`` is 'eigenmode'.
        mesh_size: Dictionary to determine manual mesh refinement on layers. Set key as the layer name and value as the
            maximal mesh element length inside the layer.
        simulation_flags: Optional export processing, given as list of strings. See Simulation Export in docs.
        ansys_project_template: path to the simulation template
        integrate_energies: Calculate energy integrals over each layer and save them into a file
        integrate_magnetic_flux: Integrate magnetic fluxes through each non-pec sheet and save them into a file
        hfss_capacitance_export: If True, the capacitance matrices are exported from HFSS simulations
    """

    name: str = ""
    ansys_tool: str = "hfss"  # to be ClassVar
    frequency_units: str = "GHz"
    frequency: Union[float, List[float]] = 5
    max_delta_s: float = 0.1
    max_delta_e: float = 0.1
    percent_error: float = 1
    percent_refinement: float = 30.0
    maximum_passes: int = 12
    minimum_passes: int = 1
    minimum_converged_passes: int = 1
    sweep_enabled: bool = True
    sweep_start: float = 0
    sweep_end: float = 10
    sweep_count: int = 101
    sweep_type: str = "interpolating"
    max_delta_f: float = 0.1
    n_modes: int = 2
    mesh_size: Optional[dict] = None
    simulation_flags: Optional[List[str]] = None
    ansys_project_template: Optional[str] = None
    integrate_energies: bool = False
    integrate_magnetic_flux: bool = False
    hfss_capacitance_export: bool = False

    def get_solution_data(self):
        """Return the solution data in dictionary form."""
        return {
            "ansys_tool": self.ansys_tool,
            "analysis_setup": {
                "frequency_units": self.frequency_units,
                "frequency": self.frequency,
                "max_delta_s": self.max_delta_s,  # stopping criterion for HFSS
                "max_delta_e": self.max_delta_e,  # stopping criterion for current or voltage excitation simulation
                "percent_error": self.percent_error,  # stopping criterion for Q3D
                "percent_refinement": self.percent_refinement,
                "maximum_passes": self.maximum_passes,
                "minimum_passes": self.minimum_passes,
                "minimum_converged_passes": self.minimum_converged_passes,
                "sweep_enabled": self.sweep_enabled,
                "sweep_start": self.sweep_start,
                "sweep_end": self.sweep_end,
                "sweep_count": self.sweep_count,
                "sweep_type": self.sweep_type,
                "max_delta_f": self.max_delta_f,
                "n_modes": self.n_modes,
            },
            "mesh_size": {} if self.mesh_size is None else self.mesh_size,
            "simulation_flags": [] if self.simulation_flags is None else self.simulation_flags,
            "integrate_energies": self.integrate_energies,
            "integrate_magnetic_flux": self.integrate_magnetic_flux,
            "hfss_capacitance_export": self.hfss_capacitance_export,
            **({} if self.ansys_project_template is None else {"ansys_project_template": self.ansys_project_template}),
        }
