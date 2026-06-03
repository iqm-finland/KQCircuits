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

from typing import List
from dataclasses import dataclass

from kqcircuits.defaults import default_faces
from kqcircuits.pya_resolver import pya


@dataclass
class InstanceHierarchy:
    """Data structure holding the instance hierarchy of a single cell instance"""

    instance: pya.Instance
    trans: pya.DCplxTrans
    parent_instances: List[pya.Instance]
    top_cell: pya.Cell


def get_cell_instance_hierarchy(layout: pya.Layout, cell_index: int) -> List[InstanceHierarchy]:
    """Find all instances of a cell and their transforms (DCplxTrans) in the global coordinate system.
    Resolves the full cell hierarchy.

    Args:
      layout: Layout object
      cell_index: Cell index of the cell to find instances of

    Returns: list of ``InstanceHierarchy`` structrures describing the cell hierarchy of each instance
    """

    to_do = [(cell_index, pya.DCplxTrans(), None, [])]
    results = []

    # Traverse the cell hierarchy upwards from the current cell, and accumulate the transformations at each hierarchy
    # level until we reach the top cell, such that we have the global transform of each instance.
    while len(to_do) > 0:
        current_cell_index, input_trans, input_inst, parent_instances = to_do.pop(0)
        cell = layout.cell(current_cell_index)
        has_parents = False
        for parent_inst in cell.each_parent_inst():
            inst = parent_inst.child_inst()
            if input_inst is None:
                input_inst = inst
            else:
                parent_instances = parent_instances + [inst]
            trans = inst.dcplx_trans
            to_do.append((parent_inst.parent_cell_index(), trans * input_trans, input_inst, parent_instances))
            has_parents = True
        if not has_parents and input_inst is not None:
            results.append(
                InstanceHierarchy(
                    instance=input_inst, trans=input_trans, parent_instances=parent_instances, top_cell=cell
                )
            )
    return results


def _get_instance_primary_face_id(instance: pya.Instance) -> str:
    """Return the primary face id for an instance, or the default KQC face."""
    face_ids = instance.pcell_parameter("face_ids")
    if isinstance(face_ids, str):
        return face_ids
    if face_ids is not None:
        try:
            if len(face_ids) > 0:
                return face_ids[0]
        except TypeError:
            pass
    return "1t1"


def get_instance_marker_polygons(
    layout: pya.Layout, instance: pya.Instance, trans: pya.DCplxTrans | None = None
) -> List[pya.DPolygon]:
    """Return ground-grid silhouette polygons for an instance in top-cell coordinates.

    Args:
        layout: Layout containing the instance.
        instance: Instance whose geometry should be highlighted.
        trans: Optional instance transform in top-cell coordinates. Defaults to ``instance.dcplx_trans``.

    Returns: DPolygons from the instance's primary face ``ground_grid_avoidance`` layer.
    """
    instance_trans = instance.dcplx_trans if trans is None else trans
    face_id = _get_instance_primary_face_id(instance)
    face = default_faces.get(face_id, default_faces["1t1"])
    marker_layer = layout.layer(face["ground_grid_avoidance"])

    polygons = []
    for shape_iter in instance.cell.begin_shapes_rec(marker_layer):
        polygon = shape_iter.shape().dpolygon
        if polygon is not None:
            polygons.append(instance_trans * shape_iter.dtrans() * polygon)
    return polygons


def formatted_cell_instance_hierarchy(inst_data: InstanceHierarchy) -> str:
    """Create formatted list showing the instance hierarchy of all instances of a cell, including the global
    transformation of the instance and the instance names along the hierarchy if they are defined.

    Args:
         layout: Layout object
         cell_index: Cell index of the cell to find instances of

    Returns: formatted string (multiple lines)
    """

    def _format_inst(inst, trans=None):
        inst_name = inst.property("id")
        r = f"{inst.cell.name}"
        if inst_name is not None:
            r += f' "{inst_name}"'
        if trans is not None:
            r += f" at {str(trans)}"
        return r

    def _spacing(i):
        return " " * 2 * (i + 1) + "-> "

    res = _spacing(-1) + f"{inst_data.top_cell.name}\n"
    for i, child in enumerate(reversed(inst_data.parent_instances)):
        res += _spacing(i) + _format_inst(child) + "\n"
    res += _spacing(len(inst_data.parent_instances)) + _format_inst(inst_data.instance, inst_data.trans) + "\n"
    return res


def transform_top_cell(
    transform: pya.DCplxTrans | pya.DTrans, layout: pya.Layout, cell: None | pya.Cell = None
) -> None:
    """Apply transformation to a top cell. Useful for chips.

    An alternative to layout.transform, but it preserves transformation hierarchy of instances.
    KLayout's layout.transform function tends to make transformation displacement to be arbitrary,
    and compensate for it by shifting polygons within instances.
    ``transform_top_cell`` will make sure that polygons won't shift in relation to its instance's
    origin within instance hierarchy.

    Args:
        transform: Transformation to apply
        layout: Layout where the top cell is. Will contain changed geometry after this call.
        cell: Optional, to specify which top cell to transform within layout.
    """
    # Just pick first top cell in layout if not specified
    if cell is None:
        cell = layout.top_cells()[0]
    # Transform immediate child instances
    for i in cell.each_inst():
        i.transform(transform)
    # Transform polygons owned by the top cell. In KQC those tend to be ground grid etc.
    for layer in layout.layer_infos():
        cell.shapes(layout.layer(layer)).transform(transform)
