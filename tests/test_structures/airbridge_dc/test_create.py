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

from kqcircuits.elements.airbridges.airbridge_rectangular import AirbridgeRectangular
from kqcircuits.test_structures.airbridge_dc import AirbridgeDC


def test_bridge_number_few():
    n_bridges = 7
    assert _get_number_of_bridges(n_bridges) == n_bridges


def test_bridge_number_many():
    n_bridges = 124
    assert _get_number_of_bridges(n_bridges) == n_bridges


def _get_number_of_bridges(n_bridges):
    layout = pya.Layout()
    cell = AirbridgeDC.create(layout, n_ab=n_bridges)
    actual_n_bridges = 0
    for inst in cell.each_inst():
        if type(inst.cell.pcell_declaration()) == AirbridgeRectangular:
            actual_n_bridges += 1
    return actual_n_bridges
