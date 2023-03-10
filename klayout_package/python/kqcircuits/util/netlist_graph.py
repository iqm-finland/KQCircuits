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

import importlib
import networkx as nx
from kqcircuits.defaults import default_netlist_ignore_connections

spec = importlib.util.find_spec("matplotlib")
matplotlib_exists = spec is not None
if matplotlib_exists:
    from matplotlib import pyplot as plt


def network_as_graph(network):
    """
    Import KQC netlist as networkx graph.

    Each element is added as a node, identified by the subcircuit id used in the netlist.
    For each node, the data dictionary contains the following items:

    * cell_name: identifies the PCell, for example ``Waveguide Coplanar$1``.
        Multiple nodes can point to the same PCell, if it has identical parameters.
    * cell_type: The PCell full name, for example ``Waveguide Coplanar``
    * location: A list [x, y] specifying the element coordinates in um.
    * instance_name: The instance name of the PCell instance, may be an empty string
    * name: A unique name for this instance. Equal to instance_name if that exists, made
        unique by appending a numbered suffix if needed. If the instance name is empty,
        a string containing the subcircuit_id.
    * properties: A dictionary containing the PCell properties associated with this instance

    Args:
        network: dictionary of netlist data obtained by loading the netlist json file

    Returns. Networkx Graph
    """
    edges = []
    used_subcircuit_ids = set()
    used_names = set()

    # Add all edges from the netlist
    for net in network["nets"].values():
        if len(net) >= 2:
            for i,net_i in enumerate(net):
                for net_j in net[i+1:]:
                    reasons_to_ignore_connections = [(a,b) for a,b in default_netlist_ignore_connections
                        if (net_i["pin"] == a and net_j["pin"] == b) or (net_i["pin"] == b and net_j["pin"] == a)]
                    if len(reasons_to_ignore_connections) > 0:
                        continue
                    edges.append([net_i["subcircuit_id"], net_j["subcircuit_id"]])
                    used_subcircuit_ids.add(net_i["subcircuit_id"])
                    used_subcircuit_ids.add(net_j["subcircuit_id"])
    graph = nx.Graph()
    graph.add_edges_from(edges)

    # Add data to the nodes
    for subcircuit_id in used_subcircuit_ids:
        subcircuit = network["subcircuits"][str(subcircuit_id)]
        graph.nodes[subcircuit_id]["cell_name"] = subcircuit["cell_name"]
        graph.nodes[subcircuit_id]["cell_type"] = subcircuit["cell_name"].split('$')[0].replace('*', ' ')
        graph.nodes[subcircuit_id]["location"] = [  subcircuit["subcircuit_location"]["x"],
                                                    subcircuit["subcircuit_location"]["y"]]
        if "instance_name" in subcircuit and subcircuit["instance_name"] is not None:
            instance_name = subcircuit["instance_name"]
        else:
            instance_name = ""
        base_name = instance_name if instance_name != "" else str(subcircuit_id)

        # Define a unique name by suffixing with a number if needed
        name = base_name
        i = 0
        while name in used_names:
            i += 1
            name = f"{base_name}_{i}"
        used_names.add(base_name)

        graph.nodes[subcircuit_id]["instance_name"] = instance_name
        graph.nodes[subcircuit_id]["name"] = name
        graph.nodes[subcircuit_id]["properties"] = subcircuit.get("properties", {})

    return graph


def draw_graph(graph, with_labels=True, with_position=True, figsize=(8, 8), export_path=None):
    """
    Draw a netlist graph

    Args:
        graph: Networkx Graph with data structures as loaded by ``network_as_graph``
        with_labels: if True, the unique ``name`` of each node will be shown as label
        with_position: if True, the nodes will be positioned as they are physically located on the chip.
            If False, a spring layout will be used to position the nodes.
        figsize: Figure size to pass to matplotlib, default (8, 8)
        export_path: Path to export image to, or None to show interactive plot

    """
    if not matplotlib_exists:
        return
    plt.figure(figsize=figsize)
    if with_position:
        pos = {node: data["location"] for node, data in graph.nodes(data=True)}
    else:
        pos = nx.spring_layout(graph)
    labels = {node: data["name"] for node, data in graph.nodes(data=True)}
    nx.draw(graph, pos=pos, labels=labels, with_labels=with_labels)
    if export_path is not None:
        plt.savefig(export_path)
    else:
        plt.show()
