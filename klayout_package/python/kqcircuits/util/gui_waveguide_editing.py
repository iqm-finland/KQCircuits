# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
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
from typing import Callable
from itertools import zip_longest

from kqcircuits.pya_resolver import pya
from kqcircuits.util.node import Node


def coerce_nodes_with_gui_path(
    nodes: list[Node],
    gui_path: pya.DPath,
    gui_path_shadow: pya.DPath,
    snap_point_callback: Callable[[pya.DPoint], pya.DPoint],
    dbu,
) -> tuple[list[Node], pya.DPath]:
    """Detect GUI editing changes in WaveguideComposite-like elements, and update the nodes list accordingly.

    To implement GUI editing of a WaveguiceComposite-like element, it needs three parameters:
    - ``nodes``: the actual list of ``Node`` objects
    - ``gui_path``: A ``pya.DPath`` parameter which is editable by the user in KLayout
    - ``gui_path_shadow``: A ``pya.DPath`` parameter which is hidden, and thus not edited by the user

    This function detects changes between ``gui_path`` and ``gui_path_shadow``. If there are changes, ``nodes`` is
    updated to reflect the coordinates.

    To use this function, call it in ``coerce_parameters_impl`` and use the output to update all three element
    parameters.

    Args:
        nodes: The ``Node`` objects (deserialzed with Node.nodes_from_string)
        gui_path: Path with a point for each Node that may have been edited by the user
        gui_path_shadow: reference Path with a point for each user that is never edited by the user.
        snap_point_callback: callback that can modify points to snap to a relevant grid. Only applied to new and
            changed positions.
        dbu: Value of layout.dbu

    Returns: tuple containing:

    - ``new_nodes``, updated list of Nodes, update the ``nodes`` parameter to this value (converted to strings)
    - ``new_path``, updated path, update ``gui_path`` and ``gui_path_shadow`` to this value
    """
    if len(nodes) < 2 or gui_path == gui_path_shadow:
        # Force rounding to integer database units since the KLayout Partial tool also rounds to database units.
        new_path = gui_path.to_itype(dbu).to_dtype(dbu)
        return nodes, new_path

    new_points = list(gui_path.each_point())
    old_points = list(gui_path_shadow.each_point())

    length_change = len(new_points) - len(old_points)
    if length_change == 0:
        # One or more points were moved; update node positions of the moved points
        for node, new_position, old_position in zip(nodes, new_points, old_points):
            if new_position != old_position:
                new_position = snap_point_callback(new_position)
                node.position = new_position
    elif length_change == 1:
        # One node was added. Figure out which node it was.
        added_index = None
        added_point = None
        for i, (new_point, old_point) in enumerate(zip_longest(new_points, old_points)):
            if old_point is None or new_point != old_point:
                added_index = i
                added_point = new_point
                break

        if added_index is not None:
            nodes.insert(added_index, Node(snap_point_callback(added_point)))
    elif length_change < 0 and gui_path.num_points() >= 2:
        # One or more points deleted; delete corresponding nodes. We require at least two remaining nodes.
        remaining_indices = []
        new_indices = []

        for i, old_point in enumerate(old_points):
            if old_point in new_points:
                remaining_indices.append(i)
                new_indices.append(new_points.index(old_point))

        # Verify we found the right number of remaining indices, and the order is correct
        new_indices_monotonic = all(i < j for i, j in zip(new_indices, new_indices[1:]))
        if len(remaining_indices) == len(new_points) and new_indices_monotonic:
            nodes = [nodes[i] for i in remaining_indices]

    # After coerce the gui_path and gui_path_shadow should both match the nodes.
    new_path = pya.DPath([node.position for node in nodes], 1)
    # Force rounding to integer database units since the KLayout Partial tool also rounds to database units.
    new_path = new_path.to_itype(dbu).to_dtype(dbu)
    return nodes, new_path
