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
"""
Calculates Q-factors from S-parameter results.
For each port creates network where all other ports are terminated by resistor.
The Q-factor of the port is the calculated from y-parameters by imag(y) / real(y),
"""
import json
import os
import skrf


def read_snp_network(snp_file):
    """Read sNp file and returns network and list of z0 for each port"""
    snp_network = skrf.Network(snp_file)

    # skrf.Network fails to read multiple Z0 terms from s2p file, so we do it separately.
    with open(snp_file) as file:
        lines = file.readlines()
        for line in lines:
            if line.startswith("# GHz S MA R "):
                z0s = [float(z) for z in line[13:].split()]
                if len(z0s) > 1:
                    return snp_network, z0s
    return snp_network, snp_network.z0[0]


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
