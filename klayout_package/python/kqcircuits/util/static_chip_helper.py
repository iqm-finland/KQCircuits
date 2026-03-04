# This code is part of KQCircuits
# Copyright (C) 2026 IQM Finland Oy
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

"""Utility function library for processing static geometry of chip"""

from kqcircuits.defaults import default_faces
from kqcircuits.pya_resolver import pya


def clear_layer(cell: pya.Cell, layer_info: pya.LayerInfo):
    """Clear chip geometry from ``cell`` at given ``layer_info``

    Modifies value of ``cell`` after this operation.
    """
    cell.flatten(True).clear(cell.layout().layer(layer_info))


def strip_faces(cell: pya.Cell, faces_to_preserve: list[str]):
    """Strip geometries from all faces on the ``cell`` except
    for faces listed in ``faces_to_preserve``

    Modifies value of ``cell`` after this operation.
    """
    for face_id, face_dictionary in default_faces.items():
        if face_id not in faces_to_preserve:
            for layer_info in face_dictionary.values():
                clear_layer(cell, layer_info)


def get_chip_boundary_box(cell: pya.Cell, face_ids: list[str]) -> pya.DBox:
    """Returns the bounding box encompassing base metal gap shapes in ``cell``
    over all given ``face_ids``.
    """
    bboxes = [
        cell.dbbox_per_layer(cell.layout().layer(default_faces[face_id]["base_metal_gap_wo_grid"]))
        for face_id in face_ids
    ]
    if all(b.empty() for b in bboxes):
        return pya.DBox()
    p1_xs, p1_ys, p2_xs, p2_ys = zip(*[(b.p1.x, b.p1.y, b.p2.x, b.p2.y) for b in bboxes if not b.empty()])
    return pya.DBox(min(p1_xs), min(p1_ys), max(p2_xs), max(p2_ys))


def copy_chip_cell_from_face(chip_cell: pya.Cell, cell_copy_name: str, from_face: str) -> pya.Cell:
    """Takes ``chip_cell``, copies a cell to same layout, then strips away
    all faces except from face id value passed as ``from_face``.
    New cell has name set as ``cell_copy_name``.
    """
    new_cell = chip_cell.layout().create_cell(cell_copy_name)
    new_cell.copy_tree(chip_cell)
    strip_faces(new_cell, [from_face])
    return new_cell


def swap_face(cell: pya.Cell, from_face: str, to_face: str):
    """Swap all layers in ``cell`` such that geometry in layer
    at ``from_face`` face id gets placed to layer of same name
    at ``to_face`` face id. If ``from_face`` face id has a layer
    that ``to_face`` doesn't have, will clear such layer.

    Modifies value of ``cell`` after this operation.
    """
    for layer_name, layer_info in default_faces[from_face].items():
        if layer_name in default_faces[to_face]:
            cell.swap(cell.layout().layer(layer_info), cell.layout().layer(default_faces[to_face][layer_name]))
        else:
            clear_layer(cell, layer_info)
