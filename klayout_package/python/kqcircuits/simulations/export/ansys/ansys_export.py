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
import shutil
from pathlib import Path

from kqcircuits.util.export_helper import write_commit_reference_file
from kqcircuits.util.geometry_json_encoder import GeometryJsonEncoder
from kqcircuits.simulations.export.util import export_layers
from kqcircuits.defaults import default_layers, ANSYS_SCRIPTS_PATH
from kqcircuits.simulations.simulation import Simulation


def copy_ansys_scripts_to_directory(path: Path, import_script_folder='scripts'):
    """
    Copies Ansys scripts into directory path.

    Arguments:
        path: Location where to copy scripts folder.
        import_script_folder: Name of the folder in its new location.
    """
    if path.exists() and path.is_dir():
        shutil.copytree(ANSYS_SCRIPTS_PATH, path.joinpath(import_script_folder))


def export_ansys_json(simulation: Simulation, path: Path, ansys_tool='hfss',
                      frequency_units="GHz", frequency=5, max_delta_s=0.1, percent_error=1, percent_refinement=30,
                      maximum_passes=12, minimum_passes=1, minimum_converged_passes=1,
                      sweep_enabled=True, sweep_start=0, sweep_end=10, sweep_count=101,
                      export_processing=None, ansys_project_template=None):
    """
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
        export_processing: Optional export processing, given as list of strings
        ansys_project_template: path to the simulation template

    Returns:
         Path to exported json file.
    """
    if simulation is None or not isinstance(simulation, Simulation):
        raise ValueError("Cannot export without simulation")
    if export_processing is None:
        export_processing = []

    # select layers
    layers = ["b_simulation_signal",
              "b_simulation_ground",
              "b_simulation_airbridge_flyover",
              "b_simulation_airbridge_pads"]
    if simulation.wafer_stack_type == "multiface":
        layers += ["t_simulation_signal",
                   "t_simulation_ground",
                   "b_simulation_indium_bump"]

    # collect data for .json file
    json_data = {
        'ansys_tool': ansys_tool,
        **simulation.get_simulation_data(),
        **{(r[13:] if r.startswith('b_') else r[:2] + r[13:]) + '_layer': default_layers[r] for r in layers},
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
            'sweep_count': sweep_count
        },
        'export_processing': export_processing
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
                  layers={default_layers[r] for r in layers}
                  )

    return json_filename


def export_ansys_bat(json_filenames, path: Path, file_prefix='simulation', exit_after_run=False,
                     ansys_executable=r"%PROGRAMFILES%\AnsysEM\v221\Win64\ansysedt.exe",
                     import_script_folder='scripts', import_script='import_and_simulate.py',
                     post_process_script='export_batch_results.py', use_rel_path=True):
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
        use_rel_path: Determines if to use relative paths.

    Returns:
         Path to exported bat file.
    """
    run_cmd = 'RunScriptAndExit' if exit_after_run else 'RunScript'

    bat_filename = str(path.joinpath(file_prefix + '.bat'))
    with open(bat_filename, 'w') as file:
        file.write('@echo off\ntitle Run Simulations\n')

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
                 sweep_enabled=True, sweep_start=0, sweep_end=10, sweep_count=101,
                 exit_after_run=False, ansys_executable=r"%PROGRAMFILES%\AnsysEM\v221\Win64\ansysedt.exe",
                 import_script='import_and_simulate.py', post_process_script='export_batch_results.py',
                 use_rel_path=True, export_processing=None, ansys_project_template=None):
    """
    Export Ansys simulations by writing necessary scripts and json, gds, and bat files.

    Arguments:
        simulations: List of simulations to be exported.
        path: Location where to write export files.
        ansys_tool: Determines whether to use HFSS ('hfss') or Q3D Extractor ('q3d').
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
        exit_after_run: Defines if the Ansys Electronics Desktop is automatically closed after running the script.
        ansys_executable: Path to the Ansys Electronics Desktop executable.
        import_script: Name of import script file.
        post_process_script: Name of post processing script file.
        use_rel_path: Determines if to use relative paths.
        export_processing: Optional export processing, given as list of strings
        ansys_project_template: path to the simulation template

    Returns:
        Path to exported bat file.
    """
    write_commit_reference_file(path)
    copy_ansys_scripts_to_directory(path, import_script_folder=import_script_folder)
    json_filenames = []
    for simulation in simulations:
        json_filenames.append(export_ansys_json(simulation, path, ansys_tool=ansys_tool,
                                                frequency_units=frequency_units, frequency=frequency,
                                                max_delta_s=max_delta_s, percent_error=percent_error,
                                                percent_refinement=percent_refinement,
                                                maximum_passes=maximum_passes, minimum_passes=minimum_passes,
                                                minimum_converged_passes=minimum_converged_passes,
                                                sweep_enabled=sweep_enabled, sweep_start=sweep_start,
                                                sweep_end=sweep_end, sweep_count=sweep_count,
                                                export_processing=export_processing,
                                                ansys_project_template=ansys_project_template))
    return export_ansys_bat(json_filenames, path, file_prefix=file_prefix, exit_after_run=exit_after_run,
                            ansys_executable=ansys_executable, import_script_folder=import_script_folder,
                            import_script=import_script, post_process_script=post_process_script,
                            use_rel_path=use_rel_path)
