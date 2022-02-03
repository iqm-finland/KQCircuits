# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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

import os


# Retuns KLayout's configuration directory already associated with `root_path`.
# If it is not found then creates and returns the right directory to use.
# If the default .klayout is used by an other KQC then use .klayout_alt/This_KQC
def klayout_configdir(root_path, configdir=""):
    if not configdir:
        if os.name == "nt":
            config_dir_name = "KLayout"
        elif os.name == "posix":
            config_dir_name = ".klayout"
        else:
            raise SystemError("Error: unsupported operating system")
        configdir = os.path.join(os.path.expanduser("~"), config_dir_name)

    klayout_python_path = f"{configdir}/python"
    if not os.path.exists(klayout_python_path):  # directory does not exist, create it.
        os.makedirs(klayout_python_path)
        return configdir

    kqc_link = os.path.realpath(f"{klayout_python_path}/kqcircuits")
    kqc_target = f"{root_path}/klayout_package/python/kqcircuits"

    if not os.path.exists(kqc_link) or os.path.samefile(kqc_link, kqc_target):  # found it
        return configdir
    elif not configdir.endswith("_alt"):  # look for alternative location, like ".klayout_alt/my_2nd_kqc_dir"
        dir_name = os.path.split(root_path)[1]
        return klayout_configdir(root_path, f"{configdir}_alt/{dir_name}")
    else:  # Several alternatives with identical name. Discourage and overwrite.
        print("Warning: {configdir} already used! Reconfiguring for this source directory.")
        return configdir

# This function createst KLayout symlinks. Used by setup_within_klayout.py.
def setup_symlinks(root_path, configdir, link_map):
    klayout_python_path = f"{configdir}/python"

    for target, name in link_map:
        link_name = os.path.join(klayout_python_path, name)
        link_target = os.path.join(root_path, target)
        if os.path.lexists(link_name):
            os.unlink(link_name)
        os.symlink(link_target, link_name, target_is_directory=True)
        print("Created symlink \"{}\" to \"{}\"".format(link_name, link_target))
