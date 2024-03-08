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


import json
import sys
from kqcircuits.util.netlist_graph import network_as_graph, draw_graph

if len(sys.argv) < 2:
    print("Usage: netlist_as_graph.py <path to netlist file> (<optional, use true locations, 0 or 1>)")
    sys.exit(-1)

with open(str(sys.argv[1]), "r") as fp:
    network = json.load(fp)

graph = network_as_graph(network)
draw_graph(graph, with_labels=True, with_position=(sys.argv[2] == "1") if (len(sys.argv) >= 3) else True)
