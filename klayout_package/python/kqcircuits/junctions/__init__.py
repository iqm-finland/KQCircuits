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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


"""PCell declaration classes for junctions.

Junctions can be either code-generated or loaded from manual design files. They are typically included in
qubits or junction test structures.

This package contains three manually designed SQUIDs in OASIS files from the Quantum Computing and Devices
research group at Aalto:
QCD1, QCD2 and QCD3.
"""

junction_type_choices = [
    "No Squid",
    "Manhattan",
    "Manhattan Single Junction",
    "Super Inductor",
    "Sim",
]
