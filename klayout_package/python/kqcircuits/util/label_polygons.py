# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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

import logging
from functools import lru_cache
from pathlib import Path
from kqcircuits.pya_resolver import pya


# Expected properties of the text geometry as loaded from the ``font_polygons.oas`` file

# File path to the ``font_polygons.oas`` file
OAS_PATH = str(Path(__file__).parent.joinpath("font_polygons.oas"))
# Letters in the oas file
OAS_LETTERS = [chr(ord("A") + i) for i in range(0, 32)] + [chr(ord("0") + i) for i in range(0, 10)]
# Spacing between two letters
OAS_TEXT_SPACING = 300.0
# "mag" parameter set for TEXT pcell in oas file
OAS_TEXT_MAGNIFICATION = 500.0
# dbu in the oas file
OAS_DBU = 0.001


def get_text_polygon(label: str, size: int = OAS_TEXT_MAGNIFICATION) -> pya.Region:
    """Returns the given label string as a region.

    If size argument is given as non-integer, will round it to nearest micron.

    Utilizes speed ups compared to generating text geometry with KLayout's TEXT PCells.
    Only supports characters layed out in the ``font_polygons.oas`` file.
    """

    font_polygons = load_font_polygons()
    unsported_characters = set(x.upper() for x in label) - set(font_polygons.keys()) - set(" ")
    if unsported_characters:
        logging.warning(
            f"Unsupported characters for get_text_polygon: {unsported_characters}."
            f" These characters will be skipped in label '{label}'"
        )

    spacing = size * OAS_TEXT_SPACING / (OAS_DBU * OAS_TEXT_MAGNIFICATION)
    label_region = pya.Region()
    if label is not None:
        for i, letter in enumerate(str(label)):
            if letter.upper() not in font_polygons:
                continue
            label_region += (
                font_polygons[letter.upper()]
                .scaled_and_snapped(0, round(size), OAS_TEXT_MAGNIFICATION, 0, round(size), OAS_TEXT_MAGNIFICATION)
                .moved(i * spacing, 0)
            )
    return label_region


@lru_cache(maxsize=None)
def load_font_polygons() -> dict[str, pya.Region]:
    """Loads from static OAS file a region for each letter used in labels.

    Cached for reuse.
    """
    layout = pya.Layout()
    layout.read(OAS_PATH)

    font_dict = {letter: pya.Region() for letter in OAS_LETTERS}
    for shape in pya.Region(layout.top_cells()[-1].begin_shapes_rec(layout.layer(129, 1))).each():
        index = round(shape.bbox().to_dtype(OAS_DBU).p1.x) // OAS_TEXT_MAGNIFICATION
        font_dict[OAS_LETTERS[int(index)]] += pya.Region(shape.moved(-OAS_TEXT_MAGNIFICATION * index / OAS_DBU, 0))

    return font_dict
