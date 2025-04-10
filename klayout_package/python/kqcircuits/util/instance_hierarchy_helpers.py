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
