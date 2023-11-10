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


from kqcircuits.elements.element import Element
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.defaults import default_tsv_type
from kqcircuits.elements.tsvs import tsv_type_choices


class Tsv(Element):
    """Base Class for TSVs."""

    default_type = default_tsv_type

    tsv_type = Param(pdt.TypeString, "TSV type", default_tsv_type, choices=tsv_type_choices)
    tsv_diameter = Param(pdt.TypeDouble, "TSV diameter", 100, unit="μm")
    tsv_margin = Param(pdt.TypeDouble, "TSV margin", 30, unit="μm")

    @classmethod
    def create(cls, layout, library=None, tsv_type=None, **parameters):
        """Create a TSV cell in layout."""
        return cls.create_subtype(layout, library, tsv_type, **parameters)[0]
