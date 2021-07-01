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

from importlib import util

# Record dependencies in setup.py too
kqc_python_dependencies = {
    "numpy": "numpy>=1.16",
    "autologging": "Autologging~=1.3",
    "scipy": "scipy>=1.2",
    "tqdm": "tqdm>=4.61",
}

def install_kqc_dependencies():
    """Check KQCircuits' dependencies and install if missing.

    This is *only* for KLayout. Stand-alone mode needs manual pip install, preferably in a venv.
    This function should run only once at KLayout startup.
    """

    missing_pkgs = []

    for pkg in kqc_python_dependencies.keys():
        if util.find_spec(pkg) is None:
            missing_pkgs.append(pkg)
    if not missing_pkgs:
        return

    # Install missing modules inside KLayout.
    import pya
    from pip import __main__
    main = __main__._main

    ask = pya.MessageBox.warning("Install packages?", "Install missing packages using 'pip': " +
                                 ", ".join(missing_pkgs), pya.MessageBox.Yes + pya.MessageBox.No)
    if ask == pya.MessageBox.Yes:
        main(['install'] + [kqc_python_dependencies[pkg] for pkg in missing_pkgs])
