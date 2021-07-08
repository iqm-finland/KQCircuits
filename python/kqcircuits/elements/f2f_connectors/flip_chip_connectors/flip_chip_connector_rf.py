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


from autologging import logged, traced

from kqcircuits.elements.f2f_connectors.flip_chip_connectors.flip_chip_connector import FlipChipConnector
from kqcircuits.elements.f2f_connectors.flip_chip_connectors.flip_chip_connector_dc import FlipChipConnectorDc
from kqcircuits.elements.launcher import Launcher
from kqcircuits.pya_resolver import pya
from kqcircuits.util.parameters import Param, pdt


@traced
@logged
class FlipChipConnectorRf(FlipChipConnector):
    """PCell declaration for an inter-chip rf connector.

    Flip chip connector with two coplanar waveguide connections and different ground bump configurations.
    The input port is on the first face and on the left. The output port is on the second face and rotated as chosen.

    Attributes:
        connector_type choices:
            * ``single``: the bump connects the two sides
            * ``GSG``: ground-signal-ground indium bumps
            * ``Coax``: signal transmitting bump is surrounded by four ground bumps
        inter_bump_distance: distance between ground bumps
        output_rotation: rotation of the output port w.r.t. the input port
        a2: Trace width of the centre conductor, 0 for automatic a/b ratio
        b2: Gap width of the centre conductor, 0 for automatic a/b ratio
    """

    connector_type = Param(pdt.TypeString, "Connector type", "Coax",
        choices=[["Single", "Single"], ["GSG", "GSG"], ["Coax", "Coax"]])
    inter_bump_distance = Param(pdt.TypeDouble, "Distance between In bumps", 100, unit="μm")
    output_rotation = Param(pdt.TypeDouble, "Rotation of output port w.r.t. input port", 180, unit="degrees")
    a2 = Param(pdt.TypeDouble, "Width of flip-chip center conductor", 40, unit="μm")
    b2 = Param(pdt.TypeDouble, "Width of flip-chip center gap", 40, unit="μm")

    def produce_impl(self):
        # Flip-chip bump
        bump = self.add_element(FlipChipConnectorDc,
                                ubm_diameter=self.ubm_diameter, bump_diameter=self.bump_diameter, margin=self.margin)
        self.insert_cell(bump)
        bump_ref = self.get_refpoints(bump)
        self.__log.debug("bump_ref: %s", bump_ref)

        # Taper geometry
        taper = self.add_element(Launcher,
                                 s=self.ubm_diameter, l=self.ubm_diameter, face_ids=[self.face_ids[0]],
                                 a=self.a, b=self.b, a_launcher=self.a2, b_launcher=self.b2)
        taper_t = self.add_element(Launcher,
                                   s=self.ubm_diameter, l=self.ubm_diameter, face_ids=[self.face_ids[1]],
                                   a=self.a, b=self.b, a_launcher=self.a2, b_launcher=self.b2)
        self.insert_cell(taper, pya.DCplxTrans(
            1, 0, False, bump_ref["base"] + pya.DPoint(- 3 / 2 * self.ubm_diameter, 0)), self.face_ids[0])
        self.insert_cell(taper_t, pya.DCplxTrans(
            1, self.output_rotation, False, pya.DVector(0, 0)) * pya.DCplxTrans(
            1, 0, False, bump_ref["base"] + pya.DPoint(- 3 / 2 * self.ubm_diameter, 0)), self.face_ids[1])

        if self.connector_type == "GSG":
            self.insert_cell(bump, pya.DCplxTrans(1, 0, False, pya.DPoint(0, self.inter_bump_distance)))
            self.insert_cell(bump, pya.DCplxTrans(1, 0, False, pya.DPoint(0, -self.inter_bump_distance)))

        elif self.connector_type == "Coax":
            # short-hand notation
            dist = 0.5**0.5 * self.inter_bump_distance
            self.insert_cell(bump, pya.DCplxTrans(1, 0, False, pya.DPoint(dist, dist)))
            self.insert_cell(bump, pya.DCplxTrans(1, 0, False, pya.DPoint(-dist, dist)))
            self.insert_cell(bump, pya.DCplxTrans(1, 0, False, pya.DPoint(dist, -dist)))
            self.insert_cell(bump, pya.DCplxTrans(1, 0, False, pya.DPoint(-dist, -dist)))

        super().produce_impl()
