# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.spiral_resonator import SpiralResonator
from kqcircuits.defaults import default_layers


class SpiralResonatorAuto(SpiralResonator):
    """The PCell declaration for a rectangular spiral resonator.

    The input of the resonator (refpoint `base`) is at left edge of the resonator. The space above, below,
    and right of the input are parameters, so the resonator will be within a box right of the input. The resonator
    length is a parameter, and it is attempted to be fit into the box such that the spacing between waveguides is as
    large as possible. Optionally, airbridge crossings can be added to all spiral segments on one side of the spiral.
    """

    PARAMETERS_SCHEMA = {
        # this is here just for hiding the "inherited" parameter in GUI
        "x_spacing": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Spacing between vertical segments",
            "default": 30,
            "readonly": True,
        },
        # this is here just for hiding the "inherited" parameter in GUI
        "y_spacing": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Spacing between horizontal segments",
            "default": 30,
            "readonly": True,
        },
    }

    def produce_impl(self):

        left, bottom, right, top, mirrored = self.get_spiral_dimensions()
        width = right - left
        height = top - bottom

        # Try to create the spiral with the largest possible spacing. This is done by starting with x_spacing=width/2
        # and y_spacing=height/2, and then decreasing them until the spiral can be created with the spacings. The
        # spacings are adjusted in an alternating fashion such that for example the y_spacing goes like
        # (width/2, width/2, width/3, width/3, width/4, width/4 ...).

        can_create_resonator = False
        spacing_idx = 4  # with each increment of this, the spacings are decreased as described above

        while not can_create_resonator:

            self.x_spacing = min(width, height)/((spacing_idx + 1)//2)
            self.y_spacing = self.x_spacing
            #self.y_spacing = height/(spacing_idx//2)

            self.cell.clear()
            can_create_resonator = self.produce_spiral_resonator()

            # prevent possibility of infinite loop (100000 here is an arbitrary large number)
            if (not can_create_resonator) and (spacing_idx > 100000):
                self.cell.clear()
                error_msg = "Cannot create a resonator with the given parameters. Try increasing the available area."
                error_text_cell = self.layout.create_cell("TEXT", "Basic", {
                    "layer": default_layers["annotations"],
                    "text": error_msg,
                    "mag": 10.0
                })
                self.insert_cell(error_text_cell)
                raise ValueError(error_msg)
                break

            spacing_idx += 1
