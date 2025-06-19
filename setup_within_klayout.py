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
import argparse
import site
import sys
from io import IOBase
from sys import executable, platform
from setup_helper import setup_symlinks, klayout_configdir, get_klayout_python_info


if __name__ == "__main__":
    # KQCircuits source path
    kqc_root_path = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(description="KQC setup within klayout")
    parser.add_argument("--unlink", action="store_true", help="remove links")
    args = parser.parse_args()

    configdir = klayout_configdir(kqc_root_path)
    # create symlink between KLayout python folder and kqcircuits folder
    link_map = (
        ("klayout_package/python/kqcircuits", "python/kqcircuits"),
        ("klayout_package/python/scripts", "python/kqcircuits_scripts"),
        ("klayout_package/python/requirements", "python/kqcircuits_requirements"),
        ("klayout_package/python/drc", "drc/kqcircuits"),
    )

    setup_symlinks(kqc_root_path, configdir, link_map, unlink=args.unlink)

    if not args.unlink:
        klayout_py_version, klayout_py_platforms, target_dir = get_klayout_python_info()
        print(f"Detected that KLayout was compiled to use python version '{klayout_py_version}'")
        test_file = IOBase()
        try:
            test_file_path = os.path.join(target_dir, ".test.file")
            # Following will throw PermissionError if target_dir needs sudo
            test_file = open(test_file_path, "x", encoding="utf-8")
            test_file.close()
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
        except PermissionError:
            target_dir = site.USER_SITE.replace(
                f"{sys.version_info[0]}.{sys.version_info[1]}", f"{'.'.join(klayout_py_version.split('.')[:2])}"
            )
            print("")
            print("KLayout's reported site-packages directory is sudo-protected.")
            print("This usually means that the KLayout executable is linked to system Python installation.")
            print(f"In such cases we simply install dependencies under USER_SITE: {target_dir}")
            print(
                "If this still causes issues, at your own risk you can run this command "
                + "with sudo to install dependencies into system directory."
            )
            print("")
        finally:
            test_file.close()
        print("Installing required packages")
        detected_os = None
        if os.name == "nt":  # Windows
            detected_os = "win"
        elif os.name == "posix":
            if platform == "darwin":  # macOS
                detected_os = "mac"
            else:
                detected_os = "linux"
        else:
            raise SystemError("Unsupported operating system.")

        print(f'Required packages will be installed in "{target_dir}".')
        # The specific pip package may be further pinpointed by specifying --abi and --implementation.
        # Specifying those doesn't seem to be needed at the moment.
        platform_args = ""
        for platform in klayout_py_platforms:
            platform_args += f"--platform {platform} "
        os.system(
            f"{executable} -m pip install -r klayout_package/python/requirements/{detected_os}/gui-requirements.txt "
            + f"--python-version {klayout_py_version} {platform_args} --only-binary=:all: "
            + f"--upgrade --target={target_dir} --break-system-packages"
        )
        print("Finished setting up KQC.")
    else:
        print("KQC unlinked from the Klayout installation")
