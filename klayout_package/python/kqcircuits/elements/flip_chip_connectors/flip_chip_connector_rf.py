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


from autologging import logged

from kqcircuits.elements.flip_chip_connectors import connector_type_choices
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector import FlipChipConnector
from kqcircuits.elements.flip_chip_connectors.flip_chip_connector_dc import FlipChipConnectorDc
from kqcircuits.elements.launcher import Launcher
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt


@logged
class FlipChipConnectorRf(FlipChipConnector):
    """PCell declaration for an inter-chip rf connector.

    Flip chip connector with two coplanar waveguide connections and different ground bump configurations.
    The input port is on the first face and on the left. The output port is on the second face and rotated as chosen.

    About connector_type choices:
        * ``Single``: the bump connects the two sides
        * ``GSG``: ground-signal-ground indium bumps
        * ``Coax``: signal transmitting bump is surrounded by four ground bumps

    .. MARKERS_FOR_PNG 0,0 15,0 0,-40 -28,0
    """

    connector_type = Param(pdt.TypeString, "Connector type", "Coax", choices=connector_type_choices)
    inter_bump_distance = Param(pdt.TypeDouble, "Distance between In bumps", 100, unit="μm")
    output_rotation = Param(pdt.TypeDouble, "Rotation of output port w.r.t. input port", 180, unit="degrees")
    connector_a = Param(pdt.TypeDouble, "Conductor width at the connector area", 40, unit="μm")
    connector_b = Param(pdt.TypeDouble, "Gap width at the connector area", 40, unit="μm")
    round_connector = Param(pdt.TypeBoolean, "Use round connector shape", False)
    n_center_bumps = Param(pdt.TypeInt, "Number of center bumps in series", 1)

    def build(self):
        # Flip-chip bump
        bump = self.add_element(FlipChipConnectorDc)
        for i in range(self.n_center_bumps):
            self.insert_cell(bump, pya.DTrans((i - (self.n_center_bumps - 1) / 2) * self.inter_bump_distance, 0))
        bump_ref = self.get_refpoints(bump)
        self.__log.debug("bump_ref: %s", bump_ref)

        tt = pya.DCplxTrans(1, self.output_rotation, False, 0, 0)  # top transformation
        if self.round_connector:
            # Rounded geometry
            def rounded_plate_with_trace(trace_x, plate_x, trace_width, plate_width, plate_length):
                reg = pya.Region(pya.DBox(plate_x - plate_length / 2, -plate_width / 2,
                                          plate_x + plate_length / 2, plate_width / 2).to_itype(self.layout.dbu))
                reg.round_corners(0, min(plate_width, plate_length) / (2 * self.layout.dbu), self.n)
                reg += pya.Region(pya.DBox(trace_x, -trace_width / 2,
                                           plate_x, trace_width / 2).to_itype(self.layout.dbu))
                return reg

            w = self.connector_a + 2 * self.connector_b
            l = w + (self.n_center_bumps - 1) * self.inter_bump_distance
            region = rounded_plate_with_trace(-l/2, 0, self.a + 2 * self.b, w, l)
            avoid_region = region.sized(self.margin / self.layout.dbu, self.margin / self.layout.dbu, 2)
            for i in range(self.n_center_bumps):
                region -= rounded_plate_with_trace(-l/2, (i - (self.n_center_bumps - 1) / 2) * self.inter_bump_distance,
                                                   self.a, self.connector_a, self.connector_a)

            self.cell.shapes(self.get_layer("base_metal_gap_wo_grid")).insert(region)
            self.cell.shapes(self.get_layer("base_metal_gap_wo_grid", 1)).insert(region.transformed(pya.ICplxTrans(tt)))
            self.add_protection(avoid_region)
            self.add_protection(avoid_region.transformed(pya.ICplxTrans(tt)), 1, 0)

            # add reference point
            self.add_port("{}_port".format(self.face_ids[0]), pya.DPoint(-l/2, 0), pya.DVector(-1, 0), 0)
            self.add_port("{}_port".format(self.face_ids[1]), tt * pya.DPoint(-l/2, 0), tt * pya.DVector(-1, 0), 1)
        else:
            # Taper geometry
            s = self.ubm_diameter + (self.n_center_bumps - 1) * self.inter_bump_distance
            trans = pya.DCplxTrans(1, 0, False, bump_ref["base"] + pya.DPoint(- self.ubm_diameter - s / 2, 0))
            self.insert_cell(Launcher, trans, self.face_ids[0], s=s, l=self.ubm_diameter,
                             a_launcher=self.connector_a, b_launcher=self.connector_b,
                             launcher_frame_gap=self.connector_b)
            self.insert_cell(Launcher, tt * trans, self.face_ids[1], s=s, l=self.ubm_diameter,
                             a_launcher=self.connector_a, b_launcher=self.connector_b,
                             launcher_frame_gap=self.connector_b, face_ids=[self.face_ids[1], self.face_ids[0]])

        # Insert ground bumps
        if self.connector_type == "GSG":
            self.insert_cell(bump, pya.DCplxTrans(1, 0, False, pya.DPoint(0, self.inter_bump_distance)))
            self.insert_cell(bump, pya.DCplxTrans(1, 0, False, pya.DPoint(0, -self.inter_bump_distance)))
        elif self.connector_type == "Coax":
            dist_y = 0.5**0.5 * self.inter_bump_distance
            dist_x = dist_y + self.inter_bump_distance * (self.n_center_bumps - 1) / 2
            self.insert_cell(bump, pya.DCplxTrans(1, 0, False, pya.DPoint(dist_x, dist_y)))
            self.insert_cell(bump, pya.DCplxTrans(1, 0, False, pya.DPoint(-dist_x, dist_y)))
            self.insert_cell(bump, pya.DCplxTrans(1, 0, False, pya.DPoint(dist_x, -dist_y)))
            self.insert_cell(bump, pya.DCplxTrans(1, 0, False, pya.DPoint(-dist_x, -dist_y)))
