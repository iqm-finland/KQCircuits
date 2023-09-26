# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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
import ast
import logging
import sys
from pathlib import Path

from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.simulation_export import export_simulation_oas, sweep_simulation
from kqcircuits.simulations.port import EdgePort
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout, \
    open_with_klayout_or_default_application


class TlsWaveguideSim(Simulation):
    """ A very short segment of waveguide. """

    def build(self):
        self.insert_cell(WaveguideCoplanar, path=pya.DPath([pya.DPoint(self.box.left, self.box.center().y),
                                                            pya.DPoint(self.box.right, self.box.center().y)], 0))
        self.ports.append(EdgePort(1, pya.DPoint(self.box.left, self.box.center().y), face=0))
        self.ports.append(EdgePort(2, pya.DPoint(self.box.right, self.box.center().y), face=0))


# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

# Simulation parameters
sim_class = TlsWaveguideSim  # pylint: disable=invalid-name
sim_parameters = {
    'name': 'tls_waveguide_sim',
    'face_stack': ['1t1'],  # single chip
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(10, 100)),
    'substrate_height': 50,  # limited simulation domain
    'upper_box_height': 50,  # limited simulation domain
    'metal_height': 0.2,
    'metal_edge_region_dimensions': [1.0],
    'tls_layer_thickness': 0.01,
    'tls_layer_material': ['oxideMA', 'oxideMS', 'oxideSA'],
    'material_dict': {**ast.literal_eval(Simulation.material_dict),
                      'oxideMA': {'permittivity': 8},
                      'oxideMS': {'permittivity': 11.4},
                      'oxideSA': {'permittivity': 4}},
}
export_parameters = {
    'path': dir_path,
    'ansys_tool': 'hfss',
    'sweep_enabled': False,
    'exit_after_run': True,
    'mesh_size': {'1t1_layerMAwall': 0.15,
                  '1t1_layerMAmer': 0.5,
                  '1t1_layerMSmer': 0.5,
                  '1t1_layerSAmer': 0.5},
    'integrate_energies': True,
    'post_process_script': 'export_epr.py',
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

#Fixed geometry simulation
simulations = sweep_simulation(layout, sim_class, sim_parameters, {'a': [2, 10]})

# Export Ansys files
export_ansys(simulations, **export_parameters)

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
