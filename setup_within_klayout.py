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


"""
Installs required packages and creates symlinks, so that kqcircuits can be used in KLayout Editor.

It is assumed that KLayout is installed and that pip is available in the shell where you run this.

Usage:

    > cd directory_where_this_file_is

    > python3 setup_within_klayout.py
    (depending on your OS and Python setup, may need to replace "python3" by "py" or "python", but make sure it refers
    to Python 3)

    To set up a secondary klayout environment just run it from a differently named directory, like
    KQcircuits_2. To use this secondary environment with KLayout the KLAYOUT_HOME environment
    variable needs to point to it.
"""


import os
from sys import platform
from setup_helper import setup_symlinks, klayout_configdir


def get_klayout_packages_path(path_start):
    # KLayout python folder name changes when its python version is updated, try to make sure we find it
    python_versions = [(major, minor) for major in [3, 4] for minor in range(30)]
    for major, minor in python_versions:
        path_start_2 = os.path.join(path_start, f"{major}.{minor}") if platform == "darwin" else path_start
        packages_path = os.path.join(path_start_2, "lib", f"python{major}.{minor}", "site-packages")
        if os.path.exists(packages_path):
            break
    return packages_path

if __name__ == "__main__":
    # KQCircuits source path
    kqc_root_path = os.path.dirname(os.path.abspath(__file__))

    # create symlink between KLayout python folder and kqcircuits folder
    link_map = (
        ("klayout_package/python/kqcircuits", "python/kqcircuits"),
        ("klayout_package/python/scripts", "python/kqcircuits_scripts"),
        ("klayout_package/python/drc", "drc/kqcircuits"),
    )

    configdir = klayout_configdir(kqc_root_path)
    setup_symlinks(kqc_root_path, configdir, link_map)

    print("Installing required packages")
    target_dir = "the system Python environment"
    if os.name == "nt":  # Windows
        target_dir = get_klayout_packages_path(os.path.join(os.getenv("APPDATA"), "KLayout"))
        pip_args = f'requirements_within_klayout_windows.txt --target="{target_dir}"'
    elif os.name == "posix":
        pip_args = "requirements_within_klayout_unix.txt"  # Linux
        if platform == "darwin":  # macOS
            td = get_klayout_packages_path("/Applications/klayout.app/Contents/Frameworks/Python.framework/Versions")
            if not os.path.exists(td):
                # Homebrew installs under /Applications/KLayout/klayout.app
                td = get_klayout_packages_path("/Applications/KLayout/klayout.app/Contents/Frameworks/Python.framework/Versions")
            # KLayout may use either its own site-packages or the system site-packages, depending on the build
            if os.path.exists(td):
                target_dir = td
                pip_args += f' --target="{target_dir}"'
    else:
        raise SystemError("Unsupported operating system.")

    print(f'Required packages will be installed in "{target_dir}".')
    os.system(f"pip install -r {pip_args}")
    print("Finished setting up KQC.")
