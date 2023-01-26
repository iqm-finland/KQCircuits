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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).
from pathlib import Path
import subprocess
import platform
import sys

def export_and_run(export_script: Path, export_path: Path, quiet: bool=False):
    """
    Exports and runs a KQC simulation.

    Args:
        export_script(Path): path to the simulation export script
        export_path(Path): path where simulation files are exported
        quiet(bool): if True all the GUI dialogs are shown, otherwise not.
    """

    if quiet:
        subprocess.call([sys.executable, export_script,
            '--simulation-export-path', str(export_path), '-q'])
    else:
        subprocess.call([sys.executable, export_script,
            '--simulation-export-path', str(export_path)])


    if (export_path / 'simulation.sh').is_file():
        simulation_shell_script = 'simulation.sh'
    else:
        simulation_shell_script = 'simulation.bat'

    if platform.system() == 'Windows':  # Windows
        subprocess.call(simulation_shell_script, shell=True, cwd=str(export_path))
    elif platform.system() == 'Darwin':  # macOS
        subprocess.call(['bash', simulation_shell_script], cwd=str(export_path))
    else:  # Linux
        subprocess.call(['bash', simulation_shell_script], cwd=str(export_path))
