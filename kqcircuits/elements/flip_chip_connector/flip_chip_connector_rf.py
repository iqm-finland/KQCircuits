# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from autologging import logged, traced
from kqcircuits.elements.flip_chip_connector.flip_chip_connector import FlipChipConnector
from kqcircuits.elements.flip_chip_connector.flip_chip_connector_dc import FlipChipConnectorDc

from kqcircuits.elements.launcher import Launcher

@traced
@logged
class FlipChipConnectorRf(FlipChipConnector):
    """PCell declaration for an inter-chip rf connector.

    The connector makes a galvanic contact between the flipped over top chip and the bottom chip.
    The design is compatible with both indium evaporation and electroplating. Origin is at the
    geometric center.

    Attributes:

        connector_type choices:
            * ``single``: the bump connects the two sides
            * ``GSG``: ground-signal-ground indium bumps
            * ``Coax``: signal transmitting bump is surronded by four ground bumps
    """

    PARAMETERS_SCHEMA = {
        "connector_type": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Connector type",
            "default": "Coax",
            "choices": [["Single", "Single"], ["GSG", "GSG"], ["Coax", "Coax"]]
        },
        "inter_bump_distance": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Distance between In bumps ",
            "default": 100
        }

    }

    def produce_impl(self):
        # Flip-chip bump
        bump = self.add_element(FlipChipConnectorDc, ubm_box=self.ubm_box, bump_diameter=self.bump_diameter, margin= self.margin)
        self.insert_cell(bump)
        bump_ref = self.get_refpoints(bump)
        self.__log.debug("bump_ref: %s", bump_ref)

        # Taper geometry
        taper = self.add_element(Launcher,
                                s=self.ubm_box, l=self.ubm_box, face_ids=[self.face_ids[0]],
                                a=self.a, b=self.b)
        taper_t = self.add_element(Launcher,
                                s=self.ubm_box, l=self.ubm_box, face_ids=[self.face_ids[1]],
                                a=self.a, b=self.b)
        self.insert_cell(taper, pya.DCplxTrans(
            1, 0, False, bump_ref["base"] + pya.DPoint(- 3 / 2 * self.ubm_box, 0)), self.face_ids[0])
        self.insert_cell(taper_t, pya.DCplxTrans(
            1, 180, False, bump_ref["base"] + pya.DPoint(3 / 2 * self.ubm_box, 0)), self.face_ids[1])

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
