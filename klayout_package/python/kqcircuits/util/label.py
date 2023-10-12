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

from enum import Enum, auto

from kqcircuits.pya_resolver import pya

class LabelOrigin(Enum):
    """Origin of the Text PCell. One of the four corners of the cell bounding box
    """
    BOTTOMLEFT = auto()
    BOTTOMRIGHT = auto()
    TOPLEFT = auto()
    TOPRIGHT = auto()

def produce_label(cell, label, location, origin, origin_offset, margin, layers, layer_protection, size=350,
                  mirror=False):
    """Produces a Text PCell accounting for desired relative position of the text respect to the given location
    and the spacing.

    Args:
        cell: container cell for the label PCell
        label: text of the label
        location: DPoint for the location of the text
        origin: LabelOrigin at which the text is located
        origin_offset: extra spacing from the location
        margin: margin of the ground grid avoidance layer around the text
        layers: list of layers where the label text is added
        layer_protection: layer where a box around the label text is added
        size: Character height in um, default 350

    Effect:
        Shapes added to the corresponding layers
    """

    layout = cell.layout()

    if not label:
        label = "A13"  # longest label on 6 inch wafer
        protection_only = True
    else:
        protection_only = False

    # text cell
    subcells = []
    for layer in layers:
        subcells.append(layout.create_cell("TEXT", "Basic", {
            "layer": layer,
            "text": label,
            "mag": size/350*500,
        }))

    # relative placement with margin
    relative_placement = {
        LabelOrigin.BOTTOMLEFT: pya.Vector(
            subcells[0].dbbox().p1.x - margin - origin_offset,
            subcells[0].dbbox().p1.y - margin - origin_offset),
        LabelOrigin.TOPLEFT: pya.Vector(
            subcells[0].dbbox().p1.x - margin - origin_offset,
            subcells[0].dbbox().p2.y + margin + origin_offset),
        LabelOrigin.TOPRIGHT: pya.Vector(
            subcells[0].dbbox().p2.x + margin + origin_offset,
            subcells[0].dbbox().p2.y + margin + origin_offset),
        LabelOrigin.BOTTOMRIGHT: pya.Vector(
            subcells[0].dbbox().p2.x + margin + origin_offset,
            subcells[0].dbbox().p1.y - margin - origin_offset),
    }[origin] * (-1)

    if mirror:
        trans = pya.DTrans(2, True, location.x - relative_placement.x, location.y + relative_placement.y)
    else:
        trans = pya.DTrans(location + relative_placement)

    if not protection_only:
        for subcell in subcells:
            cell.insert(pya.DCellInstArray(subcell.cell_index(), trans))

    # protection layer with margin
    protection = pya.DBox(pya.DPoint(subcells[0].dbbox().p1.x - margin, subcells[0].dbbox().p1.y - margin),
                          pya.DPoint(subcells[0].dbbox().p2.x + margin, subcells[0].dbbox().p2.y + margin))
    cell.shapes(layout.layer(layer_protection)).insert(
        trans.trans(protection))
