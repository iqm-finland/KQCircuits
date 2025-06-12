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
epr_gui_visualised_partition_regions = {
    "Circular Capacitor": [
        "cplrbulk",
        "1leadbulk",
        "2leadbulk",
        "1gapbulk",
        "2gapbulk",
    ],
    "Smooth Capacitor": [
        "fingersbulk",
    ],
    "Spiral Capacitor": [
        "fingergmer",
        "waveguides",
    ],
    "Swissmon": [
        "crossbulk",
        "0cplrbulk",
        "1cplrbulk",
        "2cplrbulk",
    ],
    "Double Pads": [
        "coupler1mer",
        "coupler2mer",
        "islandbulk",
        "leadsbulk",
    ],
    "Circular Transmon Single Island": [
        "0cplrmer",
        "1cplrmer",
        "2cplrmer",
        "leadsmer"
    ],
}
