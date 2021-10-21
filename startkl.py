#!/usr/bin/env python3

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

# Starts KLayout with KQCircuits configured in this directory. Force edit mode.

import os
import sys
import subprocess
from kqcircuits.defaults import ROOT_PATH


sys.path.append(str(ROOT_PATH))
from setup_helper import klayout_configdir

configdir = klayout_configdir(ROOT_PATH)
if not os.path.exists(f"{configdir}/python/kqcircuits"):
    print("Not configured? Please run setup_within_klayout.py first.")
    sys.exit(-1)

if os.name == "nt":
    exe = os.path.join(os.getenv("APPDATA"), "KLayout", "klayout_app.exe")
    exe = f'set "KLAYOUT_HOME={configdir}" & "{exe}"'
else:
    exe = f'KLAYOUT_HOME={configdir} klayout'

subprocess.run(f'{exe} -e', shell=True, check=True)
