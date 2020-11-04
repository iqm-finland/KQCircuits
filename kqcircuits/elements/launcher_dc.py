# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya


class LauncherDC(Element):
    """The PCell declaration for a DC launcher for connecting wirebonds."""

    PARAMETERS_SCHEMA = {
        "width": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Pad width [μm]",
            "default": 500
        },
    }

    def produce_impl(self):

        extra_width = 100

        offset = self.width/2
        metal_region = pya.Region((pya.DBox(-offset, -offset, offset, offset)).to_itype(self.layout.dbu))

        offset = (self.width + extra_width)/2
        gap_region = pya.Region((pya.DBox(-offset, -offset, offset, offset)).to_itype(self.layout.dbu))
        self.cell.shapes(self.get_layer("base metal gap wo grid")).insert(gap_region - metal_region)

        offset = (self.width + extra_width)/2 + self.margin
        shape = pya.Region((pya.DBox(-offset, -offset, offset, offset)).to_itype(self.layout.dbu))
        self.cell.shapes(self.get_layer("ground grid avoidance")).insert(shape)

        # add reference point
        self.add_port("", pya.DPoint(0, 0))

        super().produce_impl()
