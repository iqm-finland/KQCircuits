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

import logging
import os
import sys
import importlib.util

# This script is intended to be run by a KLayout instance in batch mode to retrieve
# information on KLayout's packaged Python instance, to guide setup_within_klayout.py wizard.

logging.basicConfig(filename=".klayout-python.info", encoding="utf-8", level=logging.DEBUG)
result = "\n"
if importlib.util.find_spec("pip") is None:
    result += "KLayout environment pip not found"
else:
    import pip
    from pip._internal.utils.compatibility_tags import get_supported

    found_platforms = set()
    for platform in get_supported():
        platform = str(platform).rsplit("-", maxsplit=1)[-1]
        if platform in found_platforms:
            continue
        result += f"KLayout python platform: {platform}\n"
        found_platforms.add(platform)
    result += f"KLayout python version: {'.'.join([str(n) for n in sys.version_info[0:3]])}\n"
    result += f"KLayout site-packages: {os.path.split(pip.__path__[0])[0]}"
logging.info(result)
# There was an attempt to update needed requirements in this code using KLayout's active python enironment,
# similar to how we do it in klayout_package/python/kqcircuits/util/dependencies.py
# For yet unknown reason this didn't work on Windows. Running KLayout on batch mode to execute
# programmatic pip update does not retain the updated packages. Therefore we simply gather
# the details on KLayout python's platform and version, then update packages from setup_within_klayout.py
