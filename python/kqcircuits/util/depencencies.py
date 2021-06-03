# This code is part of KQCirquits
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

from importlib import util


def check():
    """Check KQCircuits' dependencies and install if missing.

    That this is *only* for KLayout. Stand-alone mode needs manual pip install, preferably in a venv.
    """

    _missing_mods = []
    for mod in ["autologging", "numpy", "scipy"]:  # The needed modules are defined here
        if util.find_spec(mod) is None:
            _missing_mods.append(mod)
    if not _missing_mods:
        return

    # Install missing modules inside KLayout.
    import pya
    from pip import __main__
    main = __main__._main
    ask = pya.MessageBox.warning("Install packages?", "Install missing packages using 'pip': " +
                                 ", ".join(_missing_mods), pya.MessageBox.Yes + pya.MessageBox.No)
    if ask == pya.MessageBox.Yes:
        for mod in _missing_mods:
            main(['install', mod])
