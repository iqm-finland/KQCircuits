# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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

import logging
import sys
from pathlib import Path

from kqcircuits.defaults import default_faces
from kqcircuits.elements.airbridge_connection import AirbridgeConnection
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_rf import FlipChipConnectorRf
from kqcircuits.elements.smooth_capacitor import SmoothCapacitor
from kqcircuits.elements.tsvs.tsv_standard import TsvStandard
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.export.ansys.ansys_export import export_ansys
from kqcircuits.simulations.export.elmer.elmer_export import export_elmer
from kqcircuits.simulations.export.simulation_export import export_simulation_oas

from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.export_helper import create_or_empty_tmp_directory, get_active_or_new_layout, \
    open_with_klayout_or_default_application
from kqcircuits.util.parameters import Param, pdt


class TutorialSim(Simulation):
    """A simulation class where one can add elements on chosen faces.

    Implemented element types:
    - SmoothCapacitor (an element on single face)
    - FlipChipConnectorRf (an element with shapes on two faces and indium bumps in between)
    - AirbridgeConnection (an element on single face with airbridges)
    - Text shape (just a simple shape without ports)
    - TsvStandard (an element with shapes on two faces of the same substrate and through silicon via in between)
    """

    capacitor_faces = Param(pdt.TypeList, "Face IDs for capacitor elements", [],
                            docstring="Leave empty to not include capacitor")
    connector_faces = Param(pdt.TypeList, "Face IDs for flip chip connector elements", [],
                            docstring="Leave empty to not include connector")
    airbridge_faces = Param(pdt.TypeList, "Face IDs for airbridge connector elements", [],
                            docstring="Leave empty to not include airbridge")
    text_faces = Param(pdt.TypeList, "Face IDs for IQM texts", [],
                       docstring="Leave empty to not include text")
    tsv_faces = Param(pdt.TypeList, "Face IDs for through silicon via elements", [],
                      docstring="Leave empty to not include TSVs")

    def build(self):
        number_of_elements = len(self.capacitor_faces) + len(self.connector_faces) + len(self.airbridge_faces) + \
                             len(self.text_faces) + len(self.tsv_faces)
        element_y = self.box.bottom + self.box.height() / (number_of_elements + 1)
        port_count = 1

        # create capacitors
        for face in self.capacitor_faces:
            cell = self.add_element(SmoothCapacitor, face_ids=[face])
            cap_trans = pya.DTrans(0, False, self.box.center().x, element_y)
            element_y += self.box.height() / (number_of_elements + 1)
            _, refp = self.insert_cell(cell, cap_trans)
            self.produce_waveguide_to_port(refp["port_a"], refp["port_a_corner"], port_count, 'left',
                                           face=self.face_ids.index(face))
            self.produce_waveguide_to_port(refp["port_b"], refp["port_b_corner"], port_count + 1, 'right',
                                           face=self.face_ids.index(face))
            port_count += 2

        # create flip chip connectors
        for faces in self.connector_faces:
            cell = self.add_element(FlipChipConnectorRf, face_ids=faces)
            cap_trans = pya.DTrans(0, False, self.box.center().x, element_y)
            element_y += self.box.height() / (number_of_elements + 1)
            _, refp = self.insert_cell(cell, cap_trans)
            self.produce_waveguide_to_port(refp["1t1_port"], refp["1t1_port_corner"], port_count, 'left',
                                           face=self.face_ids.index(faces[0]))
            self.produce_waveguide_to_port(refp["2b1_port"], refp["2b1_port_corner"], port_count + 1, 'right',
                                           face=self.face_ids.index(faces[1]))
            port_count += 2

        # create airbridge connectors
        for face in self.airbridge_faces:
            cell = self.add_element(AirbridgeConnection, face_ids=[face])
            cap_trans = pya.DTrans(0, False, self.box.center().x, element_y)
            element_y += self.box.height() / (number_of_elements + 1)
            _, refp = self.insert_cell(cell, cap_trans)
            self.produce_waveguide_to_port(refp["port_a"], refp["port_a_corner"], port_count, 'left',
                                           face=self.face_ids.index(face))
            self.produce_waveguide_to_port(refp["port_b"], refp["port_b_corner"], port_count + 1, 'right',
                                           face=self.face_ids.index(face), a=20, b=12)
            port_count += 2

        # create text shape
        for face in self.text_faces:
            text_cell = self.layout.create_cell("TEXT", "Basic", {
                "layer": default_faces[face]['base_metal_gap_wo_grid'], "text": "IQM", "mag": 100})
            text_center = text_cell.bbox().to_dtype(self.layout.dbu).center()
            self.insert_cell(text_cell, pya.DTrans(self.box.center().x - text_center.x, element_y - text_center.y))
            element_y += self.box.height() / (number_of_elements + 1)

        # create through silicon via
        for faces in self.tsv_faces:
            cell = self.add_element(TsvStandard, face_ids=faces)
            trans = pya.DTrans(0, False, self.box.center().x, element_y)
            _, refp = self.insert_cell(cell, trans)
            element_y += self.box.height() / (number_of_elements + 1)



# Prepare output directory
dir_path = create_or_empty_tmp_directory(Path(__file__).stem + "_output")

sim_class = TutorialSim  # pylint: disable=invalid-name

# Simulation parameters
sim_parameters = {
    'box': pya.DBox(pya.DPoint(0, 0), pya.DPoint(1000, 1000)),
    'face_ids': ['1b1', '1t1', '2b1', '2t1']
}
# Export parameters
export_parameters = {
    'path': dir_path,
    'ansys_tool': 'hfss',
    'maximum_passes': 5,  # make simulation to finish relatively quickly, but accuracy can be poor
    'sweep_enabled': False,
    'frequency': 1
}

# Get layout
logging.basicConfig(level=logging.WARN, stream=sys.stdout)
layout = get_active_or_new_layout()

# Create simulations with different features
simulations = [
    # simple single-face simulation (old wafer_stack_type='planar')
    sim_class(layout, **sim_parameters, name='01-single_face', face_stack=['1t1'], airbridge_faces=['1t1'],
              vertical_over_etching=10),
    # a flip-chip simulation (old wafer_stack_type='multiface'), using wave ports and custom substrate materials
    sim_class(layout, **sim_parameters, name='02-two_face', face_stack=['1t1', '2b1'], connector_faces=[['1t1', '2b1']],
              use_internal_ports=False, metal_height=1.0, substrate_material=['silicon', 'sapphire'],
              material_dict={'silicon': {'permittivity': 11.45},
                             'sapphire': {'permittivity': 9.3, 'dielectric_loss_tangent': 2e-5}}),
    # a flip-chip simulation taking into account the vacuum box above the top wafer
    sim_class(layout, **sim_parameters, name='03-three_face', face_stack=['1t1', '2b1', '2t1'],
              connector_faces=[['1t1', '2b1']], text_faces=['2t1'], metal_height=1.0, dielectric_height=[0, 0, 1.0]),
    # a flip-chip simulation taking into account the vacuum boxes above and below wafers
    sim_class(layout, **sim_parameters, name='04-four_face', face_stack=['1b1', '1t1', '2b1', '2t1'],
              airbridge_faces=['1t1'], capacitor_faces=['1b1', '2b1'], text_faces=['2t1'], tsv_faces=[['1b1', '1t1']],
              lower_box_height=1000, hollow_tsv=True, metal_height=[0.0, 1.0, 0.0, 1.0]),
    # a three-wafer simulation with alternative face order, also emphasize individual chip distance and substrate height
    sim_class(layout, **sim_parameters, name='05-four_face_inverse', face_stack=['2t1', '2b1', '1t1', '1b1'],
              airbridge_faces=['1t1'], capacitor_faces=['1b1', '2b1'], text_faces=['2t1'], tsv_faces=[['1b1', '1t1']],
              chip_distance=[10.0, 20.0], substrate_height=[100., 200., 300.], metal_height=[0.0, 1.0, 0.0, 1.0]),
    # a simulation with two wafers pressed together without a gap between them
    sim_class(layout, **sim_parameters, name='06-zero_chip_distance', face_stack=['1t1', [], '2t1'],
              chip_distance=0.0, capacitor_faces=['1t1'], text_faces=['2t1']),
]

# Export Ansys (or Elmer) files
export_tool = 'ansys'
if export_tool == 'ansys':
    export_ansys(simulations, **export_parameters)
elif export_tool == 'elmer':
    export_elmer(simulations, path=dir_path, workflow={'run_gmsh_gui': True}, mesh_size={
        'global_max': 100,
        **{f'{f}_gap': 10 for f in ['1b1', '1t1', '2b1', '2t1']}
    })

# Write and open oas file
open_with_klayout_or_default_application(export_simulation_oas(simulations, dir_path))
