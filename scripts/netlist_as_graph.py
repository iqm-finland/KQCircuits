import networkx as nx
import matplotlib.pyplot as plt
import json
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
    G_1 = nx.Graph()
    G_1.add_edges_from(edges)
    pos = nx.spring_layout(G_1, k=0.5, iterations=2000)
    plt.figure(3, figsize=(12, 12))
    nx.draw(G_1, pos, labels=labels, with_labels=True)


plot_network_as_graph()
plt.show()