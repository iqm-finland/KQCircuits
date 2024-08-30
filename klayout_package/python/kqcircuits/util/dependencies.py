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

from importlib import import_module
from io import IOBase
from pathlib import Path
from sys import platform
import os
import site
import setuptools


def install_kqc_gui_dependencies():
    """Check KQCircuits' dependencies against klayout-requirements.txt file and install/upgrade if missing.

    This is *only* for KLayout GUI. Stand-alone mode needs manual pip install or pip-sync, preferably in a venv.
    This function should run only once at KLayout startup.
    """
    # pylint: disable=import-outside-toplevel

    from kqcircuits.pya_resolver import pya

    # Skip installation in stand-alone python package mode
    if not hasattr(pya, "MessageBox"):
        return

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

    target_dir = os.path.split(setuptools.__path__[0])[0]
    test_file = IOBase()
    try:
        test_file_path = os.path.join(target_dir, ".test.file")
        # Following throws PermissionError if target_dir needs sudo
        test_file = open(test_file_path, "x", encoding="utf-8")  # pylint: disable=R1732
        test_file.close()
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
    except PermissionError:
        target_dir = site.USER_SITE
    finally:
        test_file.close()

    mismatch = {}
    # Check path expected after Developer guide installation
    requirements_dir = Path(f"{os.path.dirname(__file__)}/../../kqcircuits_requirements")
    if not requirements_dir.exists():
        # Check path expected after SALT installation
        requirements_dir = Path(f"{os.path.dirname(__file__)}/../../requirements")
        if not requirements_dir.exists():
            raise FileNotFoundError(
                "Can't find gui-requirements.txt file. "
                + "If you used a developer GUI setup, try running 'python3 setup_within_klayout.py'"
            )
    requirements_file = f"{requirements_dir}/{detected_os}/gui-requirements.txt"
    with open(requirements_file, encoding="utf-8") as f:
        for line in f:
            line = line.split("#")[0]
            tokens = line.split("==")
            if len(tokens) < 2:
                continue
            package = tokens[0].strip()
            version = tokens[1].split("\\")[0].strip()
            try:
                mod = import_module(package)
                if not hasattr(mod, "__version__"):
                    raise ModuleNotFoundError()
                if mod.__version__ != version:
                    mismatch[package] = (version, mod.__version__)
            except ModuleNotFoundError:
                mismatch[package] = (version, None)

    if not mismatch:
        return

    mismatch_msg = "\n".join(
        [
            (
                f"  '{package}' ({expected_version}) - not installed"
                if not installed_version
                else f"  '{package}' expected version {expected_version}, got {installed_version}"
            )
            for package, (expected_version, installed_version) in mismatch.items()
        ]
    )

    # Install missing modules inside KLayout.
    from pip import __main__

    if hasattr(__main__, "_main"):
        main = __main__._main
    else:
        from pip._internal.cli.main import main

    ask = pya.MessageBox.warning(
        "Dependencies out of date",
        "Some dependencies for KQCircuits GUI were found to be out of date, according to\n"
        + f"{requirements_file}\n\n"
        + "The affected dependencies are:\n\n"
        + mismatch_msg
        + "\n\nInstall up to date dependencies?",
        pya.MessageBox.Yes + pya.MessageBox.No,
    )
    if ask == pya.MessageBox.Yes:
        main(["install", "-r", requirements_file, "--upgrade", f"--target={target_dir}"])
        error_msg = ""
        for package, (expected_version, _) in mismatch.items():
            try:
                mod = import_module(package)
                if not hasattr(mod, "__version__"):
                    raise ModuleNotFoundError()
                if mod.__version__ != expected_version:
                    error_msg += f"{package} still has version {mod.__version__} instead of {expected_version}\n"
            except ModuleNotFoundError:
                error_msg += f"{package} still not installed\n"
        if error_msg:
            pya.MessageBox.warning(
                "Dependency update not in effect",
                f"{error_msg}\nDependency update has not come into effect, KLayout restart is needed.\n\n"
                + "If a prompt related to dependencies appears again, "
                + "this means something went wrong with the update.\n",
                0,
            )
