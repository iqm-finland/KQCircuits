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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).
"""
Calculates Q-factors from S-parameter results.
For each port creates network where all other ports are terminated by resistor.
The Q-factor of the port is the calculated from y-parameters by imag(y) / real(y),
"""
import json
import os
import sys
import skrf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "util"))
from post_process_helpers import read_snp_network  # pylint: disable=wrong-import-position, no-name-in-module

# Find data files
path = os.path.curdir
result_files = [f for f in os.listdir(path) if f[:-2].endswith("_project_SMatrix.s")]
for result_file in result_files:
    snp_network, z0s = read_snp_network(result_file)
    freq = skrf.Frequency.from_f(snp_network.f)

    output_data = {"frequencies": list(freq.f)}
    for i, z0 in enumerate(z0s):
        port = skrf.Circuit.Port(freq, "port", z0=z0)
        connections = [[(snp_network, i), (port, 0)]]
        for j, z0j in enumerate(z0s):
            if j != i:
                resistor = skrf.Circuit.SeriesImpedance(freq, z0j, f"res{j}]")
                gnd = skrf.Circuit.Ground(freq, f"gnd{j}")
                connections += [[(snp_network, j), (resistor, 0)], [(resistor, 1), (gnd, 0)]]
        circ = skrf.Circuit(connections)
        q = [y[0][0].imag / y[0][0].real for y in circ.network.y]
        if any(v > 0 for v in q):  # ignore ports that gets invalid q values
            output_data[f"Q_port{i + 1}"] = q

    output_file = result_file[:-2].replace("_project_SMatrix.s", "_q.json")
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=4)
