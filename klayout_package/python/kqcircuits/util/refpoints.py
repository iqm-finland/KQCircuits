# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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
from kqcircuits.pya_resolver import pya


class Refpoints:
    """Helper class for extracting reference points from given layer and cell.

    Once Refpoints is initialized, it can be used similar way as dictionary, where reference point text (string) field
    is the key and reference point position (pya.DPoint) is the value.

    Refpoints is implemented such that the dictionary is extracted from given layer and cell only when it's used for the
    first time. Extracting the dictionary can be relatively time-demanding process, so this way we can speed up the
    element creation process in KQC.

    Attributes:
        layer: layer specification for source of reference points
        cell: cell containing the reference points
        trans: transform for converting reference points into target coordinate system
        rec_levels: recursion level when looking for reference points from subcells. Set to 0 to disable recursion.
    """
    def __init__(self, layer, cell, trans, rec_levels):
        self.layer = layer
        self.cell = cell
        self.trans = trans
        self.rec_levels = rec_levels
        self.refpoints = None

    def dict(self):
        """Extracts and returns reference points as dictionary, where text is the key and position is the value."""
        if self.refpoints is None:
            self.refpoints = {}
            shapes_iter = pya.RecursiveShapeIterator(self.cell.layout(), self.cell, self.layer)
            if self.rec_levels is not None:
                shapes_iter.max_depth = self.rec_levels
            while not shapes_iter.at_end():
                shape = shapes_iter.shape()
                if shape.type() in (pya.Shape.TText, pya.Shape.TTextRef):
                    self.refpoints[shape.text_string] = self.trans * (shapes_iter.dtrans()*pya.DPoint(shape.text_dpos))
                shapes_iter.next()
        return self.refpoints

    def __iter__(self):
        """Returns iterator"""
        return iter(self.dict())

    def __getitem__(self, item):
        """The [] operator to return position for given reference point text."""
        return self.dict()[item]

    def __setitem__(self, item, value):
        """The [] operator to set a new reference point."""
        self.dict()[item] = value

    def items(self):
        """Returns a list of text-position pairs."""
        return self.dict().items()

    def keys(self):
        """Returns a list of texts."""
        return self.dict().keys()

    def values(self):
        """Returns a list of positions."""
        return self.dict().values()
