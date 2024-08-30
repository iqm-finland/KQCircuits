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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

import os
import stat

import logging
from typing import Optional, Union, Sequence, Tuple
from pathlib import Path

from kqcircuits.simulations.export.ansys.ansys_solution import AnsysSolution, get_ansys_solution
from kqcircuits.simulations.export.simulation_export import (
    copy_content_into_directory,
    get_post_process_command_lines,
    get_combined_parameters,
    export_simulation_json,
)
from kqcircuits.simulations.export.simulation_validate import validate_simulation
from kqcircuits.util.export_helper import write_commit_reference_file
from kqcircuits.simulations.export.util import export_layers
from kqcircuits.defaults import ANSYS_EXECUTABLE, ANSYS_SCRIPT_PATHS
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.simulations.cross_section_simulation import CrossSectionSimulation
from kqcircuits.simulations.post_process import PostProcess


def export_ansys_json(simulation: Union[Simulation, CrossSectionSimulation], solution: AnsysSolution, path: Path):
    """
    Export Ansys simulation into json and gds files.

    Arguments:
        simulation: The simulation to be exported.
        solution: The solution to be exported.
        path: Location where to write json and gds files.

    Returns:
         Path to exported json file.
    """
    if simulation is None or not isinstance(simulation, (Simulation, CrossSectionSimulation)):
        raise ValueError("Cannot export without simulation")

    # write .gds file
    gds_file = simulation.name + ".gds"
    gds_file_path = str(path.joinpath(gds_file))
    gds_scaling = min(1e3 * simulation.layout.dbu, 1.0)
    if not Path(gds_file_path).exists():
        simulation.layout.dbu /= gds_scaling
        export_layers(
            gds_file_path, simulation.layout, [simulation.cell], output_format="GDS2", layers=simulation.get_layers()
        )
        simulation.layout.dbu *= gds_scaling
    full_name = simulation.name + solution.name
    # collect data for .json file
    json_data = {
        "name": full_name,
        **solution.get_solution_data(),
        **simulation.get_simulation_data(),
        "gds_file": gds_file,
        "gds_scaling": gds_scaling,  # Ansys gds import can't handle dbu changes, so gds scaling is added manually
        "parameters": get_combined_parameters(simulation, solution),
    }

    # write .json file
    json_file_path = str(path.joinpath(full_name + ".json"))
    export_simulation_json(json_data, json_file_path)

    return json_file_path


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
    with open(bat_filename, "w", encoding="utf-8") as file:
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
            # pylint: disable=consider-using-f-string
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
            # pylint: enable=consider-using-f-string

        file.write(get_post_process_command_lines(post_process, path, json_filenames))

    # Make the bat file executable in linux
    os.chmod(bat_filename, os.stat(bat_filename).st_mode | stat.S_IEXEC)

    return bat_filename


def export_ansys(
    simulations: Sequence[Union[Simulation, Tuple[Simulation, AnsysSolution]]],
    path: Path,
    script_folder: str = "scripts",
    file_prefix: str = "simulation",
    exit_after_run: bool = False,
    import_script: str = "import_and_simulate.py",
    post_process: Optional[Union[PostProcess, Sequence[PostProcess]]] = None,
    use_rel_path: bool = True,
    skip_errors: bool = False,
    **solution_params,
) -> Path:
    """
    Export Ansys simulations by writing necessary scripts and json, gds, and bat files.

    Arguments:
        simulations: List of Simulation objects or tuples containing Simulation and Solution objects.
        path: Location where to write export files.
        script_folder: Path to the Ansys-scripts folder.
        file_prefix: Name of the batch file to be created.
        exit_after_run: Defines if the Ansys Electronics Desktop is automatically closed after running the script.
        import_script: Name of import script file.
        post_process: List of PostProcess objects, a single PostProcess object, or None to be executed after simulations
        use_rel_path: Determines if to use relative paths.
        skip_errors: Skip simulations that cause errors. Default is False.

            .. warning::

               **Use this carefully**, some of your simulations might not make sense physically and
               you might end up wasting time on bad simulations.
        solution_params: AnsysSolution parameters if simulations is a list of Simulation objects.

    Returns:
        Path to exported bat file.
    """
    write_commit_reference_file(path)
    copy_content_into_directory(ANSYS_SCRIPT_PATHS, path, script_folder)
    json_filenames = []
    common_sol = None if all(isinstance(s, Sequence) for s in simulations) else get_ansys_solution(**solution_params)
    for sim_sol in simulations:
        simulation, solution = sim_sol if isinstance(sim_sol, Sequence) else (sim_sol, common_sol)
        validate_simulation(simulation, solution)
        try:
            json_filenames.append(export_ansys_json(simulation, solution, path))
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
