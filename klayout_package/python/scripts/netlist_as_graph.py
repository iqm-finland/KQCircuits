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


import json
import sys
import matplotlib.pyplot as plt
import networkx as nx

if len(sys.argv) < 2:
    print("Usage: netlist_as_graph.py <path to netlist file> (<optional, use true locations, 0 or 1>)")
    sys.exit(-1)

with open(str(sys.argv[1]), "r") as fp:
    network = json.load(fp)

def plot_network_as_graph(true_locations: bool = True):
    edges = []
    used_subcircuit_ids = set()
    for net in network["nets"].values():
        if len(net) >= 2:
            edges.append([net[0]["subcircuit_id"], net[1]["subcircuit_id"]])
            used_subcircuit_ids.add(net[0]["subcircuit_id"])
            used_subcircuit_ids.add(net[1]["subcircuit_id"])
    labels, pos = {}, {}
    for subcircuit_id in used_subcircuit_ids:
        labels[subcircuit_id] = network["subcircuits"][str(subcircuit_id)]["cell_name"]
        pos[subcircuit_id] = network["subcircuits"][str(subcircuit_id)]["subcircuit_location"]
    graph_1 = nx.Graph()
    graph_1.add_edges_from(edges)
    pos = pos if true_locations else nx.spring_layout(graph_1, k=0.5, iterations=2000)
    plt.figure(3, figsize=(12, 12))
    nx.draw(graph_1, pos, labels=labels, with_labels=True)


plot_network_as_graph(true_locations=(sys.argv[2] == '1') if (len(sys.argv) >= 3) else True)
plt.show()
