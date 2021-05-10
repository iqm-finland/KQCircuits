# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import get_cell_path_length

from kqcircuits.elements.spiral_resonator_multiface import SpiralResonatorMultiface
from kqcircuits.defaults import default_layers

relative_length_tolerance = 1e-3

def test_length_by_connector_location():
    len_begin = _get_waveguide_length(4200, 500, 400, 1000, 0)
    len_middle = _get_waveguide_length(4200, 500, 400, 1000, 2000)
    len_end = _get_waveguide_length(4200, 500, 400, 1000, 4000)
    relative_middle_begin = abs(len_begin - len_middle) / len_middle
    relative_middle_end = abs(len_end - len_middle) / len_middle
    assert relative_middle_begin < relative_length_tolerance and relative_middle_end < relative_length_tolerance

def _get_waveguide_length(length, above_space, below_space, right_space, connector_dist, bridges_top=False):
    """Returns the relative error of the spiral resonator length with the given parameters."""
    layout = pya.Layout()
    spiral_resonator_cell = SpiralResonatorMultiface.create(layout,
                                                            length=length,
                                                            above_space=above_space,
                                                            below_space=below_space,
                                                            right_space=right_space,
                                                            connector_dist=connector_dist,
                                                            bridges_top=bridges_top
                                                            )
    return get_cell_path_length(spiral_resonator_cell, layout.layer(default_layers["waveguide_length"]))
