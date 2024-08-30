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
import json
from pathlib import Path


class PostProcess:
    """Base class for adding post-processing scripts into the simulation batch"""

    def __init__(
        self,
        script,
        command="python",
        arguments="",
        folder="scripts",
        repeat_for_each=False,
        data_file_prefix=None,
        **data,
    ):
        """
        Args:
            script: name of the post-processing script
            command: command to run the post-processing script
            arguments: command line arguments for the post-processing script given as string
            folder: path where to look for the post-processing script file
            repeat_for_each: whether to repeat the post-processing script for every simulation. The simulation json file
                name becomes the first command line argument.
            data_file_prefix: prefix of the saved data file if data is given
            data: additional data to be saved into a file. The data file name becomes the last command line argument.
        """
        self.script = script
        self.command = command
        self.arguments = arguments
        self.folder = folder
        self.repeat_for_each = repeat_for_each
        self.data_file_prefix = data_file_prefix
        self.data = data

    def get_command_line(self, path, json_filenames):
        """Saves the data into file if needed and returns the command line to execute the post-processing script.

        Args:
            path: simulation folder path
            json_filenames: list of paths to simulation json files
        """
        str_args = self.arguments
        if self.data:
            file = str(Path(self.script).stem if self.data_file_prefix is None else self.data_file_prefix) + ".json"
            str_args += ' "' + file + '"'
            with open(path.joinpath(file), "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)

        # Return the command line(s)
        str_cmd = f'{self.command} "{Path(self.folder).joinpath(self.script)}"'
        if self.repeat_for_each:
            lines = ""
            for json_filename in json_filenames:
                lines += f'{str_cmd} "{Path(json_filename).relative_to(path)}" {str_args}\n'
            return lines
        return f"{str_cmd} {str_args}\n"
