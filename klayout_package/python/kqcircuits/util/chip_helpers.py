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

from kqcircuits.defaults import default_layers
from kqcircuits.elements.element import insert_cell_into
from kqcircuits.pya_resolver import pya


def produce_instance_name_labels(cell: pya.Cell):
    """Places instance name labels for instances a cell.

    Child instances of ``cell`` with the ``id`` property set will have a label drawn on the ``instance_names`` layer.
    If exists, the instance property ``label_trans`` is used as an additional transormation on the label for
    readability.

    Args:
          cell: the ``Cell`` to find child instances in
          target_cell: a ``Cell`` to place the labels in, or ``None`` to use ``cell``

    """
    layout = cell.layout()
    for inst in cell.each_inst():
        inst_id = inst.property("id")
        if inst_id:
            label_cell = layout.create_cell(
                "TEXT", "Basic", {"layer": default_layers["instance_names"], "text": inst_id, "mag": 400.0}
            )
            label_trans = inst.dcplx_trans
            # prevent the label from being upside-down or mirrored
            if 90 < label_trans.angle < 270:
                label_trans.angle += 180
            label_trans.mirror = False
            # optionally apply relative transformation to the label
            rel_label_trans_str = inst.property("label_trans")
            if rel_label_trans_str is not None:
                rel_label_trans = pya.DCplxTrans.from_s(rel_label_trans_str)
                label_trans = label_trans * rel_label_trans
            insert_cell_into(cell, label_cell, label_trans)
