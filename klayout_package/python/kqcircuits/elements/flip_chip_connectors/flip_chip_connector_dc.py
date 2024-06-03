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


from kqcircuits.elements.flip_chip_connectors.flip_chip_connector import FlipChipConnector
from kqcircuits.util.geometry_helper import circle_polygon


class FlipChipConnectorDc(FlipChipConnector):
    """PCell declaration for an inter-chip dc connector.

    .. MARKERS_FOR_PNG 0,0 0,15
    """

    def build(self):

        ubm_shape = circle_polygon(self.ubm_diameter / 2, self.n)
        self.cell.shapes(self.get_layer("underbump_metallization", 0)).insert(ubm_shape)
        self.cell.shapes(self.get_layer("underbump_metallization", 1)).insert(ubm_shape)

        avoidance_shape = circle_polygon(self.ubm_diameter / 2 + self.margin, self.n)
        self.cell.shapes(self.get_layer("ground_grid_avoidance", 0)).insert(avoidance_shape)
        self.cell.shapes(self.get_layer("ground_grid_avoidance", 1)).insert(avoidance_shape)

        bump_shape = circle_polygon(self.bump_diameter / 2, self.n)
        self.cell.shapes(self.get_layer("indium_bump", 0)).insert(bump_shape)  # bottom In bump
        self.cell.shapes(self.get_layer("indium_bump", 1)).insert(bump_shape)  # top In bump
