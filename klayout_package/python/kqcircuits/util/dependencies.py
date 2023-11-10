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

from importlib import util, import_module

# Record dependencies in setup.py too
kqc_python_dependencies = {
    "numpy": "numpy>=1.16",
    "scipy": "scipy>=1.2",
    "tqdm": "tqdm>=4.61",
    "networkx": "networkx>=2.7",
}


def install_kqc_dependencies():
    """Check KQCircuits' dependencies and install/upgrade if missing.

    This is *only* for KLayout. Stand-alone mode needs manual pip install, preferably in a venv.
    This function should run only once at KLayout startup.
    """
    # pylint: disable=import-outside-toplevel

    from kqcircuits.pya_resolver import pya
    # Skip installation in stand-alone python package mode
    if not hasattr(pya, 'MessageBox'):
        return

    missing_pkgs = []

    for pkg, pkg_ver in kqc_python_dependencies.items():
        if util.find_spec(pkg) is None:
            missing_pkgs.append(pkg)
        else:
            mod = import_module(pkg)
            v_inst = tuple(map(int, (mod.__version__.split("."))))
            v_reqd = tuple(map(int, (pkg_ver.rsplit("=", maxsplit=1)[-1].split("."))))
            if v_reqd > v_inst:
                missing_pkgs.append(pkg)

    if not missing_pkgs:
        return

    # Install missing modules inside KLayout.
    from pip import __main__
    if hasattr(__main__, "_main"):
        main = __main__._main
    else:
        from pip._internal.cli.main import main

    ask = pya.MessageBox.warning("Install packages?", "Install missing packages using 'pip': " +
                                 ", ".join(missing_pkgs), pya.MessageBox.Yes + pya.MessageBox.No)
    if ask == pya.MessageBox.Yes:
        main(['install'] + [kqc_python_dependencies[pkg] for pkg in missing_pkgs])
