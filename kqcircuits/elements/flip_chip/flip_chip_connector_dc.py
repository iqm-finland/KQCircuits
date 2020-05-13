# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import math
from kqcircuits.pya_resolver import pya
from autologging import logged, traced

from kqcircuits.elements.element import Element


@logged
@traced
class FlipChipConnectorDc(Element):
    """PCell declaration for an inter-chip dc connector.

    Origin is at the geometric center. The connector mediates galvanic contact
    between top chip and bottom chip.  The design is compatible with both
    indium evaporation and electroplating.

    Attributes:

        ubm_box: length of the side of the under-bump metallization box [um]
        bump_radius: indium bump radius [um]
    """

    PARAMETERS_SCHEMA = {
        "ubm_box": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Under-bump metallization width (um)",
            "default": 30
        },
        "bump_radius": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Bump radius (um)",
            "default": 10
        }
    }

    def __init__(self):
        super().__init__()

    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return "flip_chip_Connector_dc({})".format(self.name)

    def coerce_parameters_impl(self):
        None

    def can_create_from_shape_impl(self):
        return False

    def parameters_from_shape_impl(self):
        None

    def transformation_from_shape_impl(self):
        return pya.Trans()

    def produce_impl(self):
        # origin: geometric center
        # direction: from top to bottom

        # shorthand
        w = self.ubm_box
        r = self.bump_radius

        # under-bump metallization
        pts = [
            pya.DPoint(-w/2, -w/2),
            pya.DPoint(-w/2, w/2),
            pya.DPoint(w/2, w/2),
            pya.DPoint(w/2, -w/2),
        ]
        shape = pya.DPolygon(pts)

        # bottom under-bump metallization
        self.cell.shapes(self.layout.layer(self.face(0)["underbump metallization"])).insert(shape)
        # top under-bump metallization
        self.cell.shapes(self.layout.layer(self.face(1)["underbump metallization"])).insert(shape)

        # Protection layer
        m = self.margin
        pts = [
            pya.DPoint(-w/2 - m, -w/2 - m),
            pya.DPoint(-w/2 - m, w/2 + m),
            pya.DPoint(w/2 + m, w/2 + m),
            pya.DPoint(w/2 + m, -w/2 - m),
        ]
        shape = pya.DPolygon(pts)

        # ground avoidance layer bottom
        self.cell.shapes(self.layout.layer(self.face(0)["ground grid avoidance"])).insert(shape)
        self.cell.shapes(self.layout.layer(self.face(0)["ground grid avoidance"])).insert(pya.DTrans.M0*shape)

        # ground avoidance layer top
        self.cell.shapes(self.layout.layer(self.face(1)["ground grid avoidance"])).insert(shape)
        self.cell.shapes(self.layout.layer(self.face(1)["ground grid avoidance"])).insert(pya.DTrans.M0*shape)

        # bump geometry
        circle_pts = [pya.DPoint(math.cos(a/32 * math.pi) * r,
                      math.sin(a/32 * math.pi) * r) for a in range(0, 64 + 1)]
        shape = pya.DPolygon(circle_pts)
        self.cell.shapes(self.layout.layer(self.face(0)["indium bump"])).insert(shape)  # bottom In bump
        self.cell.shapes(self.layout.layer(self.face(1)["indium bump"])).insert(shape)  # top In bump


