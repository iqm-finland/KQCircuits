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

import matplotlib.pyplot as plt
import networkx as nx

from kqcircuits.defaults import TMP_PATH

with open(str(TMP_PATH / "netlist_Chip Library.Demo.json"), "r") as fp:
    network = json.load(fp)


def plot_network_as_graph():
    edges = []
    used_subcircuit_ids = set()
    for net in network["nets"].values():
        if len(net) >= 2:
            edges.append([net[0]["subcircuit_id"], net[1]["subcircuit_id"]])
            used_subcircuit_ids.add(net[0]["subcircuit_id"])
            used_subcircuit_ids.add(net[1]["subcircuit_id"])
    labels = {}
    for subcircuit_id in used_subcircuit_ids:
        labels[subcircuit_id] = network["subcircuits"][f"{subcircuit_id}"]["cell_name"]
    graph_1 = nx.Graph()
    graph_1.add_edges_from(edges)
    pos = nx.spring_layout(graph_1, k=0.5, iterations=2000)
    plt.figure(3, figsize=(12, 12))
    nx.draw(graph_1, pos, labels=labels, with_labels=True)


plot_network_as_graph()
plt.show()
