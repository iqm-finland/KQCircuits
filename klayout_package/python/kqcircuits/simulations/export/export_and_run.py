# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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
from pathlib import Path
import subprocess
import platform
import sys
import logging

from kqcircuits.defaults import EXPORT_PATH_IDENTIFIER

logging.basicConfig(level=logging.WARN, stream=sys.stdout)


def export_and_run(export_script: Path, export_path: Path, quiet: bool = False, export_only: bool = False, args=None):
    """
    Exports and runs a KQC simulation.

    Args:
        export_script(Path): path to the simulation export script
        export_path(Path): path where simulation files are exported set with `--export-path-basename`. If None, the
                           path set in export script will be used.
        quiet(bool): if True all the GUI dialogs are shown, otherwise not.
        export_only(bool): if True no simulation is run, only export files.
        args(list): a list of strings describing arguments to be passed to the simulation script

    Returns:
        a tuple containing

            * export_script(Path): path to the simulation export script
            * export_path(list(Path)): list of paths where simulation files are exported

    """

    script_export_paths = run_export_script(export_script, export_path, quiet, args)

    if not export_only:
        run_simulations(script_export_paths)

    return export_script, script_export_paths


def run_export_script(export_script: Path, export_path: Path, quiet: bool = False, args=None):
    """
    Generate the simulation files by running the export script. Returns list of paths where
    simulation files are exported. Returned paths are parsed from stdout of the export script printed
    by function `create_or_empty_tmp_directory`, based on the identifier `EXPORT_PATH_IDENTIFIER`
    """
    if args is None:
        args = []
    elif "--simulation-export-path" in args:
        logging.error("--simulation-export-path is not allowed!")
        sys.exit()

    export_cmd = (
        [sys.executable, export_script]
        + (["--simulation-export-path", str(export_path)] if export_path else [])
        + args
        + (["-q"] if quiet else [])
    )
    # Run export script and capture stdout to be processed
    with subprocess.Popen(export_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
        process_stdout, process_stderr = process.communicate()
        print(process_stdout)
        print(process_stderr, file=sys.stderr)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, export_cmd)

    # Parse export paths from stdout printed in `create_or_empty_tmp_directory`
    script_export_paths = [l.strip() for l in process_stdout.split("\n")]
    script_export_paths = [
        Path(l.removeprefix(EXPORT_PATH_IDENTIFIER))
        for l in script_export_paths
        if l.startswith(EXPORT_PATH_IDENTIFIER)
    ]

    # remove duplicate paths
    unique_paths = set()
    script_export_paths = [n for n in script_export_paths if not (n in unique_paths or unique_paths.add(n))]

    if export_path and len(script_export_paths) > 1:
        logging.error("Using `--export-path-basename` is not supported with scripts exporting multiple simulations")

    return script_export_paths


def run_simulations(script_export_paths: list[Path]):
    """Run exported simulations"""
    for script_export_path in script_export_paths:
        if (script_export_path / "simulation.sh").is_file():
            simulation_shell_script = "simulation.sh"
        elif (script_export_path / "simulation.bat").is_file():
            simulation_shell_script = "simulation.bat"
        else:
            logging.warning(f"No simulation.sh or .bat script found in {script_export_path}")
            continue

        if platform.system() == "Windows":  # Windows
            subprocess.call(simulation_shell_script, shell=True, cwd=str(script_export_path))
        elif platform.system() == "Darwin":  # macOS
            subprocess.call(["bash", simulation_shell_script], cwd=str(script_export_path))
        else:  # Linux
            subprocess.call(["bash", simulation_shell_script], cwd=str(script_export_path))
