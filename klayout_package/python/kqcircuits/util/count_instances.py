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

def count_instances_in_cell(cell, pcell_class):
    """Returns the number of pcell instances of type `pcell_class` in cell.

    The instances are counted from the entire hierarchy below cell, not only direct child instances. Also pcells with
    type derived from `pcell_class` are counted.

    Args:
        cell: cell from which the instances are counted
        pcell_class: pcell class of the instances

    Returns:
        The number of instances below `cell` for which `isinstance(inst.cell.pcell_declaration(), pcell_class) == True`.
    """
    n = 0
    if isinstance(cell.pcell_declaration(), pcell_class):
        n += 1
    for inst in cell.each_inst():
        # workaround for getting the cell due to KLayout bug, see
        # https://www.klayout.de/forum/discussion/1191/cell-shapes-cannot-call-non-const-method-on-a-const-reference
        # TODO: replace by `inst_cell = inst.cell` once KLayout bug is fixed
        inst_cell = cell.layout().cell(inst.cell_index)
        n += count_instances_in_cell(inst_cell, pcell_class)
    return n
