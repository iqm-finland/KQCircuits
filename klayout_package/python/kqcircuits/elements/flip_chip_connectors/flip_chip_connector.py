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

from kqcircuits.elements.element import Element
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.defaults import default_bump_type, default_bump_parameters
from kqcircuits.elements.flip_chip_connectors import connector_type_choices


class FlipChipConnector(Element):
    """Connector between matching faces of two chips.

    The connector makes a galvanic contact between the flipped over top chip and the bottom chip.
    Origin is at the geometric center.
    """

    default_type = default_bump_type
    ubm_diameter = Param(
        pdt.TypeDouble, "Under-bump metalization diameter", default_bump_parameters["under_bump_diameter"], unit="μm"
    )
    bump_diameter = Param(pdt.TypeDouble, "Bump diameter", default_bump_parameters["bump_diameter"], unit="μm")
    bump_type = Param(pdt.TypeString, "Bump type", default_bump_type, choices=connector_type_choices)

    @classmethod
    def create(cls, layout, library=None, bump_type=None, **parameters):
        """Create a bump cell in layout."""
        return cls.create_subtype(layout, library, bump_type, **parameters)[0]
