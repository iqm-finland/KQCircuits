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


"""This module is used for importing the KLayout Python API (pya).

Without this module, the API would need to be imported using ``import pya`` for usage in KLayout Editor and using
``import klayout.db`` for usage with standalone klayout package. To make it simple to create a python module for both
use cases, this module automatically imports the correct module and exposes it as ``pya``.

It also contains convenience functions to find the KLayout executable and the running session type.

Usage:
    from kqcircuits.pya_resolver import pya

"""

import os
import platform
from pathlib import Path
from shutil import which
try:
    import pya
    import pya as lay  # pylint: disable=unused-import
except ImportError:
    import klayout.db as pya
    from klayout import lay  # pylint: disable=unused-import


def is_standalone_session():
    return not hasattr(pya, 'Application')

def klayout_executable_command():
    """Returns the KLayout executable command's full path in the current OS. Or ``None`` if it is not found."""
    if is_standalone_session():
        if platform.system() == "Windows":
            klayout_path = which("klayout_app.exe")
            if klayout_path is None:  # try the default location
                dwp = Path(os.getenv("APPDATA")).joinpath("KLayout/klayout_app.exe")
                if dwp.is_file():
                    return str(dwp)
            return klayout_path
        klayout_path = which("klayout")  # Linux is simple :)
        if klayout_path is None and platform.system() == "Darwin":
            dwp = "/Applications/klayout.app/Contents/MacOS/klayout"
            if Path(dwp).is_file():
                return dwp
            dwp = "/Applications/KLayout/klayout.app/Contents/MacOS/klayout"
            if Path(dwp).is_file():
                return dwp
        return klayout_path
    else:  # The path of the currently running KLayout application
        return pya.Application.instance().applicationFilePath()
