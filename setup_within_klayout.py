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


"""
Installs required packages and creates symlinks, so that kqcircuits can be used in KLayout Editor.
This assumes that a prebuilt KLayout has already been installed in the default location, and that KLayout has been
opened at least once (because that creates the KLayout python folder).
This also assumes that pip is available in the shell where you run this.

Usage:

    (in Windows the command line must be opened with admin privileges)

    > cd directory_where_this_file_is

    > python3 setup_within_klayout.py
    (depending on your OS and Python setup, may need to replace "python3" by "py" or "python", but make sure it refers
    to Python 3)

"""


import os


def find_path_or_ask(path, message):
    """Checks if the given path exists, and asks for new path if it does not.

    Args:
        path: the path that is first tried
        message: text to display when asking for a new path

    Returns:
         the path once it is found
    """
    while not os.path.exists(path):
        path = input(message)
    return path


# set up paths
kqc_root_path = os.path.dirname(os.path.abspath(__file__))
print("KQC source code assumed to be in \"{}\"".format(kqc_root_path))
if os.name == "nt":
    klayout_python_path = os.path.join(os.path.expanduser("~"), "KLayout", "python")
elif os.name == "posix":
    klayout_python_path = os.path.join(os.path.expanduser("~"), ".klayout", "python")
else:
    raise SystemError("Error: unsupported operating system")
klayout_python_path = find_path_or_ask(klayout_python_path, "Could not find path to KLayout python directory. Please "
                                                            "enter the path:")
print("KLayout python directory assumed to be \"{}\"".format(klayout_python_path))

# create symlink between KLayout python folder and kqcircuits folder
link_map = (
    ("kqcircuits", "kqcircuits"),
    ("scripts", "kqcircuits_scripts"),
)
for target, name in link_map:
    link_name = os.path.join(klayout_python_path, name)
    link_target = os.path.join(kqc_root_path, target)
    if not os.path.exists(link_name):
        os.symlink(link_target, link_name, target_is_directory=True)
        print("Created symlink \"{}\" to \"{}\"".format(link_name, link_target))
    else:
        print("Found existing symlink \"{}\" to \"{}\"".format(link_name, link_name))

print("Installing required packages")
# install required packages
if os.name == "nt":
    klayout_packages_path = os.path.join(os.getenv("APPDATA"), "KLayout", "lib", "python3.7", "site-packages")
    klayout_packages_path = find_path_or_ask(klayout_packages_path, "Could not find path to KLayout site-packages "
                                                                    "directory. Please enter the path:")
    print("Required packages will be installed in \"{}\"".format(klayout_packages_path))
    os.system("pip install -r requirements_within_klayout_windows.txt --target={}".format(klayout_packages_path))
elif os.name == "posix":
    os.system("pip3 install -r requirements_within_klayout_unix.txt")
else:
    raise SystemError("Error: unsupported operating system")

print("Finished setting up KQC.")
