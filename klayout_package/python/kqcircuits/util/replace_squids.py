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

"""
    Functions to replace SQUIDs in existing design files.

    Typical usage in a macro::

            top_cell = KLayoutView(current=True).active_cell
            replace_squids(top_cell, "MySQUID", "junction_width", 0.5, 0.1)  # a parameter sweep
            replace_squid(top_cell, "QB_2", "MySQUID", mirror=True)          # replace an individual SQUID
"""

from os import path
from autologging import logged
from kqcircuits.pya_resolver import pya
from kqcircuits.junctions import junction_type_choices
from kqcircuits.junctions.junction import Junction
from kqcircuits.chips.chip import Chip


@logged
def replace_squids(cell, junction_type, parameter_name, parameter_start, parameter_step, parameter_end=None):
    """Replaces squids by code generated squids with the given parameter sweep.

    All squids below top_cell in the cell hierarchy are removed. The number of code
    generated squids may be limited by the value of parameter_end.

    Args:
        cell (Cell): The cell where the squids to be replaced are
        junction_type: class name of the code generated squid that replaces the other squids
        parameter_name (str): Name of the parameter to be swept
        parameter_start: Start value of the parameter
        parameter_step: Parameter value increment step
        parameter_end: End value of the parameter. If None, there is no limit for the parameter value, so that all
            squids are replaced

    """
    layout = cell.layout()
    parameter_value = parameter_start
    junction_types = [choice if isinstance(choice, str) else choice[1] for choice in junction_type_choices]

    old_squids = []  # list of tuples (squid instance, squid dtrans with respect to cell, old name)

    def recursive_replace_squids(top_cell_inst, combined_dtrans):
        """Appends to old_squids all squids in top_cell_inst or any instance below it in hierarchy."""
        # cannot use just top_cell_inst.cell due to klayout bug, see
        # https://www.klayout.de/forum/discussion/1191/cell-shapes-cannot-call-non-const-method-on-a-const-reference
        top_cell = layout.cell(top_cell_inst.cell_index)
        for subcell_inst in top_cell.each_inst():
            subcell_name = subcell_inst.cell.name
            if subcell_name in junction_types:
                old_squids.append((subcell_inst, combined_dtrans*subcell_inst.dtrans, subcell_name))
            else:
                recursive_replace_squids(subcell_inst, combined_dtrans*subcell_inst.dtrans)

    for inst in cell.each_inst():
        if inst.cell.name in junction_types:
            old_squids.append((inst, inst.dtrans, inst.cell.name))
        recursive_replace_squids(inst, inst.dtrans)

    # sort left-to-right and bottom-to-top
    old_squids.sort(key=lambda squid: (squid[1].disp.x, squid[1].disp.y))

    for (inst, dtrans, name) in old_squids:
        if (parameter_end is None) or (parameter_value <= parameter_end):
            # create new squid at old squid's position
            parameters = {parameter_name: parameter_value}
            squid_cell = Junction.create(layout, junction_type=junction_type, face_ids=inst.pcell_parameter("face_ids"),
                                      **parameters)
            cell.insert(pya.DCellInstArray(squid_cell.cell_index(), dtrans))
            replace_squids._log.info("Replaced squid \"{}\" with dtrans={} by a squid \"{}\" with {}={}."
                                     .format(name, dtrans, junction_type, parameter_name, parameter_value))
            parameter_value += parameter_step
        # delete old squid
        inst.delete()

@logged
def replace_squid(top_cell, inst_name, junction_type, mirror=False, squid_index=0, **params):
    """Replaces a SQUID by the requested alternative in the named instance.

    Replaces the SQUID(s) in the sub-element(s) named ``inst_name`` with other SQUID(s) of
    ``junction_type``. The necessary SQUID parameters are specified in ``params``. If ``inst_name`` is
    a Test Structure then ``squid_index`` specifies which SQUID to change.

    Args:
        top_cell: The top cell with SQUIDs to be replaced
        inst_name: Instance name of PCell containing the SQUID to be replaced
        junction_type: Name of SQUID Class or .gds/.oas file
        mirror: Mirror the SQUID along its vertical axis
        squid_index: Index of the SQUID to be replaced within a Test Structure
        **params: Extra parameters for the new SQUID
    """

    def find_cells_with_squids(chip, inst_name):
        """Returns the container cells in `chip` called `inst_name`"""
        cells = []
        layout = chip.layout()
        for inst in chip.each_inst():
            if inst.property("id") == inst_name:
                cells.append((chip, inst))
            elif isinstance(inst.pcell_declaration(), Chip):  # recursively look for more chips
                cells += find_cells_with_squids(layout.cell(inst.cell_index), inst_name)
        return cells

    cells = find_cells_with_squids(top_cell, inst_name)
    if not cells:
        replace_squid._log.warn(f"Could not find anything named '{inst_name}'!")

    layout = top_cell.layout()
    file_cell = None
    if junction_type.endswith(".oas") or junction_type.endswith(".gds"):  # try to load from file
        if not path.exists(junction_type):
            replace_squid._log.warn(f"No file found at '{path.realpath(junction_type)}!")
            return
        load_opts = pya.LoadLayoutOptions()
        load_opts.cell_conflict_resolution = pya.LoadLayoutOptions.CellConflictResolution.RenameCell
        layout.read(junction_type, load_opts)
        file_cell = layout.top_cells()[-1]
        file_cell.name = f"Junction Library.{file_cell.name}"

    for (chip, inst) in cells:
        orig_trans = inst.dcplx_trans
        ccell = inst.layout().cell(inst.cell_index)

        if ccell.is_pcell_variant():  # make copy if used elsewhere
            dup = ccell.dup()
            dup.set_property("id", inst.property("id"))
            inst.delete()
            chip.insert(pya.DCellInstArray(dup.cell_index(), orig_trans), dup.prop_id)
            ccell = dup

        squids = [sq for sq in ccell.each_inst() if sq.cell.qname().find("Junction Library") != -1]
        squids.sort(key=lambda q: q.property("squid_index"))
        if not squids or squid_index >= len(squids) or squid_index < 0:
            replace_squid._log.warn(f"No SQUID found in '{inst_name}' or squid_index={squid_index} is out of range!")
            continue
        old_squid = squids[squid_index]
        if old_squid.is_pcell():
            params = {"face_ids": old_squid.pcell_parameter("face_ids"), **params}
        trans = old_squid.dcplx_trans * pya.DCplxTrans.M90 if mirror else old_squid.dcplx_trans
        squid_pos = (orig_trans * trans).disp
        replace_squid._log.info(f"Replaced SQUID of '{inst_name}' with {junction_type} at {squid_pos}.")
        old_squid.delete()
        if file_cell:
            new_squid = ccell.insert(pya.DCellInstArray(file_cell.cell_index(), trans))
        else:
            new_squid = Junction.create(layout, junction_type=junction_type, **params)
            new_squid = ccell.insert(pya.DCellInstArray(new_squid.cell_index(), trans))
        new_squid.set_property("squid_index", squid_index)

def convert_cells_to_static(layout):
    """Converts all cells in the layout to static. """

    converted_cells = {}

    # convert the cells to static
    for cell in layout.each_cell():
        if cell.is_library_cell():
            cell_idx = cell.cell_index()
            new_cell_idx = layout.convert_cell_to_static(cell_idx)
            if new_cell_idx != cell_idx:
                converted_cells[cell_idx] = new_cell_idx

    # translate the instances
    for cell in layout.each_cell():
        for inst in cell.each_inst():
            if inst.cell_index in converted_cells:
                inst.cell_index = converted_cells[inst.cell_index]

    # delete the PCells
    for cell_idx in converted_cells:
        layout.delete_cell(cell_idx)
