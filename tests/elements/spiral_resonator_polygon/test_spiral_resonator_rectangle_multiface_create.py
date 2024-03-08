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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import get_cell_path_length
from kqcircuits.elements.spiral_resonator_polygon import SpiralResonatorPolygon, rectangular_parameters

relative_length_tolerance = 1e-3


def test_length_by_connector_location():
    len_begin = _get_waveguide_length(4200, 500, 400, 1000, 0)
    len_middle = _get_waveguide_length(4200, 500, 400, 1000, 2000)
    len_end = _get_waveguide_length(4200, 500, 400, 1000, 4000)
    relative_middle_begin = abs(len_begin - len_middle) / len_middle
    relative_middle_end = abs(len_end - len_middle) / len_middle
    assert relative_middle_begin < relative_length_tolerance and relative_middle_end < relative_length_tolerance


def _get_waveguide_length(length, above_space, below_space, right_space, connector_dist):
    """Returns the relative error of the spiral resonator length with the given parameters."""
    layout = pya.Layout()
    spiral_resonator_cell = SpiralResonatorPolygon.create(
        layout,
        **rectangular_parameters(
            length=length,
            above_space=above_space,
            below_space=below_space,
            right_space=right_space,
            connector_dist=connector_dist,
        ),
    )
    return get_cell_path_length(spiral_resonator_cell)
