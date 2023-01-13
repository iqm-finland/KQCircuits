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


import json
import logging

from distutils.dir_util import copy_tree
from pathlib import Path

from kqcircuits.util.export_helper import write_commit_reference_file
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder
from kqcircuits.simulations.export.util import export_layers
from kqcircuits.defaults import ANSYS_SCRIPT_PATHS
from kqcircuits.simulations.simulation import Simulation


def copy_ansys_scripts_to_directory(path: Path, import_script_folder='scripts'):
    """
    Copies Ansys scripts into directory path.

    Arguments:
        path: Location where to copy scripts folder.
        import_script_folder: Name of the folder in its new location.
    """
    if path.exists() and path.is_dir():
        for script_path in ANSYS_SCRIPT_PATHS:
            copy_tree(str(script_path), str(path.joinpath(import_script_folder)), update=1)


def export_ansys_json(simulation: Simulation, path: Path, ansys_tool='hfss',
                      frequency_units="GHz", frequency=5, max_delta_s=0.1, percent_error=1, percent_refinement=30,
                      maximum_passes=12, minimum_passes=1, minimum_converged_passes=1,
                      sweep_enabled=True, sweep_start=0, sweep_end=10, sweep_count=101, sweep_type='interpolating',
                      max_delta_f=0.1, n_modes=2, gap_max_element_length=None, substrate_loss_tangent=0,
                      dielectric_surfaces=None, simulation_flags=None, ansys_project_template=None):
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
        gap_max_element_length: Largest mesh element length allowed in the gaps given in simulation units
            (if None is given, then the mesh element size is not restricted in the gap).
        substrate_loss_tangent: Bulk loss tangent (:math:`\tan{\delta}`) material parameter. 0 is off.
        dielectric_surfaces: Material parameters for TLS interfaces, used in post-processing field calculations
            from the participation sheets. Default is None. Input is of the form::

                'layerMA': {  # metal–vacuum
                    'tan_delta_surf': 0.001,  # loss tangent
                    'th': 4e-9,  # thickness
                    'eps_r': 10  # relative permittivity
                },
                'layerMS': { # metal–substrate
                    'tan_delta_surf': 0.001,
                    'th': 2e-9,
                    'eps_r': 10
                },
                'layerSA': { # substrate–vacuum
                    'tan_delta_surf': 0.001,
                    'th': 2e-9,
                    'eps_r': 10
                },
        simulation_flags: Optional export processing, given as list of strings
        ansys_project_template: path to the simulation template

    Returns:
         Path to exported json file.
    """
    if simulation is None or not isinstance(simulation, Simulation):
        raise ValueError("Cannot export without simulation")
    if simulation_flags is None:
        simulation_flags = []

    # collect data for .json file
    json_data = {
        'ansys_tool': ansys_tool,
        **simulation.get_simulation_data(),
        'analysis_setup': {
            'frequency_units': frequency_units,
            'frequency': frequency,
            'max_delta_s': max_delta_s,  # stopping criterion for HFSS
            'percent_error': percent_error,  # stopping criterion for Q3D
            'percent_refinement': percent_refinement,
            'maximum_passes': maximum_passes,
            'minimum_passes': minimum_passes,
            'minimum_converged_passes': minimum_converged_passes,
            'sweep_enabled': sweep_enabled,
            'sweep_start': sweep_start,
            'sweep_end': sweep_end,
            'sweep_count': sweep_count,
            'sweep_type': sweep_type,
            'max_delta_f': max_delta_f,
            'n_modes': n_modes,
        },
        'gap_max_element_length': gap_max_element_length,
        'substrate_loss_tangent': substrate_loss_tangent,
        'dielectric_surfaces': dielectric_surfaces,
        'simulation_flags': simulation_flags
    }

    if ansys_project_template is not None:
        json_data['ansys_project_template'] = ansys_project_template

    # write .json file
    json_filename = str(path.joinpath(simulation.name + '.json'))
    with open(json_filename, 'w') as fp:
        json.dump(json_data, fp, cls=GeometryJsonEncoder, indent=4)

    # write .gds file
    gds_filename = str(path.joinpath(simulation.name + '.gds'))
    export_layers(gds_filename, simulation.layout, [simulation.cell],
                  output_format='GDS2',
                  layers=simulation.get_layers()
                  )

    return json_filename


def export_ansys_bat(json_filenames, path: Path, file_prefix='simulation', exit_after_run=False,
                     ansys_executable=r"%PROGRAMFILES%\AnsysEM\v222\Win64\ansysedt.exe",
                     import_script_folder='scripts', import_script='import_and_simulate.py',
                     post_process_script='export_batch_results.py', intermediate_processing_command=None,
                     use_rel_path=True):
    """
    Create a batch file for running one or more already exported simulations.

    Arguments:
        json_filenames: List of paths to json files to be included into the batch.
        path: Location where to write the bat file.
        file_prefix: Name of the batch file to be created.
        exit_after_run: Defines if the Ansys Electronics Desktop is automatically closed after running the script.
        ansys_executable: Path to the Ansys Electronics Desktop executable.
        import_script_folder: Path to the Ansys-scripts folder.
        import_script: Name of import script file.
        post_process_script: Name of post processing script file.
        intermediate_processing_command: Command for intermediate steps between simulations.
            Default is None, which doesn't enable any processing. An example argument is ``python scripts/script.py``,
            which runs in the `.bat` as::

                python scripts/script.py json_filename.json

        use_rel_path: Determines if to use relative paths.

    Returns:
         Path to exported bat file.
    """
    run_cmd = 'RunScriptAndExit' if exit_after_run else 'RunScript'

    bat_filename = str(path.joinpath(file_prefix + '.bat'))
    with open(bat_filename, 'w') as file:
        file.write(
            '@echo off\n'\
            r'powershell -Command "Get-Process | Where-Object {$_.MainWindowTitle -like \"Run Simulations*\"} '\
                '| Select -ExpandProperty Id | Export-Clixml -path blocking_pids.xml"\n'\
            'title Run Simulations\n'\
            'powershell -Command "$sim_pids = Import-Clixml -Path blocking_pids.xml; if ($sim_pids) '\
                r'{ echo \"Waiting for $sim_pids\"; Wait-Process $sim_pids -ErrorAction SilentlyContinue }; '\
                'Remove-Item blocking_pids.xml"\n'
        )

        # Commands for each simulation
        for i, json_filename in enumerate(json_filenames):
            printing = 'echo Simulation {}/{} - {}\n'.format(
                i+1,
                len(json_filenames),
                str(Path(json_filename).relative_to(path)))
            file.write(printing)
            command = '"{}" -scriptargs "{}" -{} "{}"\n'.format(
                ansys_executable,
                str(Path(json_filename).relative_to(path) if use_rel_path else json_filename),
                run_cmd,
                str(Path(import_script_folder).joinpath(import_script)))
            file.write(command)
            # Possible processing between simulations
            if intermediate_processing_command is not None:
                command = '{} "{}"\n'.format(
                    intermediate_processing_command,
                    str(Path(json_filename).relative_to(path))
                )
                file.write(command)

        # Post-process command
        command = '"{}" -{} "{}"\n'.format(
            ansys_executable,
            run_cmd,
            str(Path(import_script_folder).joinpath(post_process_script)))
        file.write(command)

    return bat_filename


def export_ansys(simulations, path: Path, ansys_tool='hfss', import_script_folder='scripts', file_prefix='simulation',
                 frequency_units="GHz", frequency=5, max_delta_s=0.1, percent_error=1, percent_refinement=30,
                 maximum_passes=12, minimum_passes=1, minimum_converged_passes=1,
                 sweep_enabled=True, sweep_start=0, sweep_end=10, sweep_count=101, sweep_type='interpolating',
                 max_delta_f=0.1, n_modes=2, gap_max_element_length=None, substrate_loss_tangent=0,
                 dielectric_surfaces=None, exit_after_run=False,
                 ansys_executable=r"%PROGRAMFILES%\AnsysEM\v222\Win64\ansysedt.exe",
                 import_script='import_and_simulate.py', post_process_script='export_batch_results.py',
                 intermediate_processing_command=None, use_rel_path=True, simulation_flags=None,
                 ansys_project_template=None, skip_errors=False):
    r"""
    Export Ansys simulations by writing necessary scripts and json, gds, and bat files.

    Arguments:
        simulations: List of simulations to be exported.
        path: Location where to write export files.
        ansys_tool: Determines whether to use HFSS ('hfss'), Q3D Extractor ('q3d') or HFSS eigenmode ('eigenmode').
        import_script_folder: Path to the Ansys-scripts folder.
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
        gap_max_element_length: Largest mesh element length allowed in the gaps given in simulation units
            (if None is given, then the mesh element size is not restricted in the gap).
        substrate_loss_tangent: Bulk loss tangent (:math:`\tan{\delta}`) material parameter. 0 is off.
        dielectric_surfaces: Material parameters for TLS interfaces, used in post-processing field calculations
            from the participation sheets. Default is None. Input is of the form::

                'layerMA': {  # metal–vacuum
                    'tan_delta_surf': 0.001,  # loss tangent
                    'th': 4e-9,  # thickness
                    'eps_r': 10  # relative permittivity
                },
                'layerMS': { # metal–substrate
                    'tan_delta_surf': 0.001,
                    'th': 2e-9,
                    'eps_r': 10
                },
                'layerSA': { # substrate–vacuum
                    'tan_delta_surf': 0.001,
                    'th': 2e-9,
                    'eps_r': 10
                },

        exit_after_run: Defines if the Ansys Electronics Desktop is automatically closed after running the script.
        ansys_executable: Path to the Ansys Electronics Desktop executable.
        import_script: Name of import script file.
        post_process_script: Name of post processing script file.
        intermediate_processing_command: Command for intermediate steps between simulations.
            Default is None, which doesn't enable any processing. An example argument is ``python scripts/script.py``,
            which runs in the `.bat` as::

                python scripts/script.py json_filename.json

        use_rel_path: Determines if to use relative paths.
        simulation_flags: Optional export processing, given as list of strings. See Simulation Export in docs.
        ansys_project_template: path to the simulation template
        skip_errors: Skip simulations that cause errors. Default is False.

            .. warning::

               **Use this carefully**, some of your simulations might not make sense physically and
               you might end up wasting time on bad simulations.

    Returns:
        Path to exported bat file.
    """
    write_commit_reference_file(path)
    copy_ansys_scripts_to_directory(path, import_script_folder=import_script_folder)
    json_filenames = []
    for simulation in simulations:
        try:
            json_filenames.append(export_ansys_json(simulation, path, ansys_tool=ansys_tool,
                                            frequency_units=frequency_units, frequency=frequency,
                                            max_delta_s=max_delta_s, percent_error=percent_error,
                                            percent_refinement=percent_refinement,
                                            maximum_passes=maximum_passes, minimum_passes=minimum_passes,
                                            minimum_converged_passes=minimum_converged_passes,
                                            sweep_enabled=sweep_enabled, sweep_start=sweep_start,
                                            sweep_end=sweep_end, sweep_count=sweep_count, sweep_type=sweep_type,
                                            max_delta_f=max_delta_f, n_modes=n_modes,
                                            gap_max_element_length=gap_max_element_length,
                                            substrate_loss_tangent=substrate_loss_tangent,
                                            dielectric_surfaces=dielectric_surfaces,
                                            simulation_flags=simulation_flags,
                                            ansys_project_template=ansys_project_template))
        except (IndexError, ValueError, Exception) as e:  # pylint: disable=broad-except
            if skip_errors:
                logging.warning(
                    f'Simulation {simulation.name} skipped due to {e.args}. '\
                    'Some of your other simulations might not make sense geometrically. '\
                    'Disable `skip_errors` to see the full traceback.'
                )
            else:
                raise UserWarning(
                    'Generating simulation failed. You can discard the errors using `skip_errors` in `export_ansys`. '\
                    'Moreover, `skip_errors` enables visual inspection of failed and successful simulation '\
                    'geometry files.'
                ) from e

    return export_ansys_bat(json_filenames, path, file_prefix=file_prefix, exit_after_run=exit_after_run,
                            ansys_executable=ansys_executable, import_script_folder=import_script_folder,
                            import_script=import_script, post_process_script=post_process_script,
                            intermediate_processing_command=intermediate_processing_command,
                            use_rel_path=use_rel_path)
