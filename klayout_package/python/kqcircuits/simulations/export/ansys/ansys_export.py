# This code is part of KQCircuits
# Copyright (C) 2021 IQM Finland Oy
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

import os
import stat

import json
import logging

from pathlib import Path

from kqcircuits.simulations.export.simulation_export import copy_content_into_directory, get_post_process_command_lines
from kqcircuits.util.export_helper import write_commit_reference_file
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder
from kqcircuits.simulations.export.util import export_layers
from kqcircuits.defaults import ANSYS_EXECUTABLE, ANSYS_SCRIPT_PATHS
from kqcircuits.simulations.simulation import Simulation


def export_ansys_json(
    simulation: Simulation,
    path: Path,
    ansys_tool="hfss",
    frequency_units="GHz",
    frequency=5,
    max_delta_s=0.1,
    percent_error=1,
    percent_refinement=30,
    maximum_passes=12,
    minimum_passes=1,
    minimum_converged_passes=1,
    sweep_enabled=True,
    sweep_start=0,
    sweep_end=10,
    sweep_count=101,
    sweep_type="interpolating",
    max_delta_f=0.1,
    n_modes=2,
    mesh_size=None,
    simulation_flags=None,
    ansys_project_template=None,
    integrate_energies=False,
    hfss_capacitance_export=False,
):
    r"""
    Export Ansys simulation into json and gds files.

    Arguments:
        simulation: The simulation to be exported.
        path: Location where to write json and gds files.
        ansys_tool: Determines whether to use HFSS ('hfss') or Q3D Extractor ('q3d').
        frequency_units: Units of frequency.
        frequency: Frequency for mesh refinement. To set up multifrequency analysis in HFSS use list of numbers.
        max_delta_s: Stopping criterion in HFSS simulation.
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
        n_modes: Number of eigenmodes to solve. Used when ``ansys_tool`` is 'pyepr'.
        mesh_size(dict): Dictionary to determine manual mesh refinement on layers. Set key as the layer name and
            value as the maximal mesh element length inside the layer.
        simulation_flags: Optional export processing, given as list of strings
        ansys_project_template: path to the simulation template
        integrate_energies: Calculate energy integrals over each layer and save them into a file
        hfss_capacitance_export: If True, the capacitance matrices are exported from HFSS simulations

    Returns:
         Path to exported json file.
    """
    if simulation is None or not isinstance(simulation, Simulation):
        raise ValueError("Cannot export without simulation")
    if simulation_flags is None:
        simulation_flags = []

    # collect data for .json file
    json_data = {
        "ansys_tool": ansys_tool,
        **simulation.get_simulation_data(),
        "analysis_setup": {
            "frequency_units": frequency_units,
            "frequency": frequency,
            "max_delta_s": max_delta_s,  # stopping criterion for HFSS
            "percent_error": percent_error,  # stopping criterion for Q3D
            "percent_refinement": percent_refinement,
            "maximum_passes": maximum_passes,
            "minimum_passes": minimum_passes,
            "minimum_converged_passes": minimum_converged_passes,
            "sweep_enabled": sweep_enabled,
            "sweep_start": sweep_start,
            "sweep_end": sweep_end,
            "sweep_count": sweep_count,
            "sweep_type": sweep_type,
            "max_delta_f": max_delta_f,
            "n_modes": n_modes,
        },
        "mesh_size": {} if mesh_size is None else mesh_size,
        "simulation_flags": simulation_flags,
        "integrate_energies": integrate_energies,
        "hfss_capacitance_export": hfss_capacitance_export,
    }

    if ansys_project_template is not None:
        json_data["ansys_project_template"] = ansys_project_template

    # write .json file
    json_filename = str(path.joinpath(simulation.name + ".json"))
    with open(json_filename, "w") as fp:
        json.dump(json_data, fp, cls=GeometryJsonEncoder, indent=4)

    # write .gds file
    gds_filename = str(path.joinpath(simulation.name + ".gds"))
    export_layers(
        gds_filename, simulation.layout, [simulation.cell], output_format="GDS2", layers=simulation.get_layers()
    )

    return json_filename


def export_ansys_bat(
    json_filenames,
    path: Path,
    file_prefix="simulation",
    exit_after_run=False,
    execution_script="scripts/import_and_simulate.py",
    post_process=None,
    use_rel_path=True,
):
    """
    Create a batch file for running one or more already exported simulations.

    Arguments:
        json_filenames: List of paths to json files to be included into the batch.
        path: Location where to write the bat file.
        file_prefix: Name of the batch file to be created.
        exit_after_run: Defines if the Ansys Electronics Desktop is automatically closed after running the script.
        execution_script: The script file to be executed.
        post_process: List of PostProcess objects, a single PostProcess object, or None to be executed after simulations
        use_rel_path: Determines if to use relative paths.

    Returns:
         Path to exported bat file.
    """
    run_cmd = "RunScriptAndExit" if exit_after_run else "RunScript"

    bat_filename = str(path.joinpath(file_prefix + ".bat"))
    with open(bat_filename, "w") as file:
        file.write(
            "@echo off\n"
            r'powershell -Command "Get-Process | Where-Object {$_.MainWindowTitle -like \"Run Simulations*\"} '
            '| Select -ExpandProperty Id | Export-Clixml -path blocking_pids.xml"\n'
            "title Run Simulations\n"
            'powershell -Command "$sim_pids = Import-Clixml -Path blocking_pids.xml; if ($sim_pids) '
            r"{ echo \"Waiting for $sim_pids\"; Wait-Process $sim_pids -ErrorAction SilentlyContinue }; "
            'Remove-Item blocking_pids.xml"\n'
        )

        # Commands for each simulation
        for i, json_filename in enumerate(json_filenames):
            printing = "echo Simulation {}/{} - {}\n".format(
                i + 1, len(json_filenames), str(Path(json_filename).relative_to(path))
            )
            file.write(printing)
            command = '"{}" -scriptargs "{}" -{} "{}"\n'.format(
                ANSYS_EXECUTABLE,
                str(Path(json_filename).relative_to(path) if use_rel_path else json_filename),
                run_cmd,
                str(execution_script),
            )
            file.write(command)

        file.write(get_post_process_command_lines(post_process, path, json_filenames))

    # Make the bat file executable in linux
    os.chmod(bat_filename, os.stat(bat_filename).st_mode | stat.S_IEXEC)

    return bat_filename


def export_ansys(
    simulations,
    path: Path,
    ansys_tool="hfss",
    script_folder="scripts",
    file_prefix="simulation",
    frequency_units="GHz",
    frequency=5,
    max_delta_s=0.1,
    percent_error=1,
    percent_refinement=30,
    maximum_passes=12,
    minimum_passes=1,
    minimum_converged_passes=1,
    sweep_enabled=True,
    sweep_start=0,
    sweep_end=10,
    sweep_count=101,
    sweep_type="interpolating",
    max_delta_f=0.1,
    n_modes=2,
    mesh_size=None,
    exit_after_run=False,
    import_script="import_and_simulate.py",
    post_process=None,
    use_rel_path=True,
    simulation_flags=None,
    ansys_project_template=None,
    integrate_energies=False,
    hfss_capacitance_export=False,
    skip_errors=False,
):
    r"""
    Export Ansys simulations by writing necessary scripts and json, gds, and bat files.

    Arguments:
        simulations: List of simulations to be exported.
        path: Location where to write export files.
        ansys_tool: Determines whether to use HFSS ('hfss'), Q3D Extractor ('q3d') or HFSS eigenmode ('eigenmode').
        script_folder: Path to the Ansys-scripts folder.
        file_prefix: Name of the batch file to be created.
        frequency_units: Units of frequency.
        frequency: Frequency for mesh refinement. To set up multifrequency analysis in HFSS use list of numbers.
        max_delta_s: Stopping criterion in HFSS simulation.
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
        mesh_size(dict): Dictionary to determine manual mesh refinement on layers. Set key as the layer name and
            value as the maximal mesh element length inside the layer.
        exit_after_run: Defines if the Ansys Electronics Desktop is automatically closed after running the script.
        import_script: Name of import script file.
        post_process: List of PostProcess objects, a single PostProcess object, or None to be executed after simulations

        use_rel_path: Determines if to use relative paths.
        simulation_flags: Optional export processing, given as list of strings. See Simulation Export in docs.
        ansys_project_template: path to the simulation template
        integrate_energies: Calculate energy integrals over each layer and save them into a file
        hfss_capacitance_export: If True, the capacitance matrices are exported from HFSS simulations
        skip_errors: Skip simulations that cause errors. Default is False.

            .. warning::

               **Use this carefully**, some of your simulations might not make sense physically and
               you might end up wasting time on bad simulations.

    Returns:
        Path to exported bat file.
    """
    write_commit_reference_file(path)
    copy_content_into_directory(ANSYS_SCRIPT_PATHS, path, script_folder)
    json_filenames = []
    for simulation in simulations:
        try:
            json_filenames.append(
                export_ansys_json(
                    simulation,
                    path,
                    ansys_tool=ansys_tool,
                    frequency_units=frequency_units,
                    frequency=frequency,
                    max_delta_s=max_delta_s,
                    percent_error=percent_error,
                    percent_refinement=percent_refinement,
                    maximum_passes=maximum_passes,
                    minimum_passes=minimum_passes,
                    minimum_converged_passes=minimum_converged_passes,
                    sweep_enabled=sweep_enabled,
                    sweep_start=sweep_start,
                    sweep_end=sweep_end,
                    sweep_count=sweep_count,
                    sweep_type=sweep_type,
                    max_delta_f=max_delta_f,
                    n_modes=n_modes,
                    mesh_size=mesh_size,
                    simulation_flags=simulation_flags,
                    ansys_project_template=ansys_project_template,
                    integrate_energies=integrate_energies,
                    hfss_capacitance_export=hfss_capacitance_export,
                )
            )
        except (IndexError, ValueError, Exception) as e:  # pylint: disable=broad-except
            if skip_errors:
                logging.warning(
                    f"Simulation {simulation.name} skipped due to {e.args}. "
                    "Some of your other simulations might not make sense geometrically. "
                    "Disable `skip_errors` to see the full traceback."
                )
            else:
                raise UserWarning(
                    "Generating simulation failed. You can discard the errors using `skip_errors` in `export_ansys`. "
                    "Moreover, `skip_errors` enables visual inspection of failed and successful simulation "
                    "geometry files."
                ) from e

    return export_ansys_bat(
        json_filenames,
        path,
        file_prefix=file_prefix,
        exit_after_run=exit_after_run,
        execution_script=Path(script_folder).joinpath(import_script),
        post_process=post_process,
        use_rel_path=use_rel_path,
    )
