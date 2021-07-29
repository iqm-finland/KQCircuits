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


from autologging import logged, traced

from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya
from kqcircuits.squids import squid_type_choices
from kqcircuits.util.library_helper import load_libraries, to_library_name
from kqcircuits.util.parameters import Param, pdt


@traced
@logged
class Squid(Element):
    """Base class for SQUIDs without actual produce function.

    This class can represent both code generated and manually designed SQUIDs. Thus, any SQUID can be created using code
    like

        `self.add_element(Squid, squid_type="SquidName", **parameters)`,

    where "SquidName" is either a specific squid class name or name of a manually designed squid cell.
    """

    LIBRARY_NAME = "SQUID Library"
    LIBRARY_DESCRIPTION = "Library for SQUIDs."
    LIBRARY_PATH = "squids"

    junction_width = Param(pdt.TypeDouble, "Junction width [μm]", 0.02)

    @classmethod
    def create(cls, layout, squid_type=None, **parameters):
        """Create cell for a squid in layout.

        The squid cell is created either from a pcell class or a from a manual design file, depending on squid_type. If
        squid_type does not correspond to any squid, an empty "NoSquid" squid is returned.

        Overrides Element.create(), so that functions like add_element() and insert_cell() will call this instead.

        Args:
            layout: pya.Layout object where this cell is created
            squid_type (str): name of the squid class or of the manually designed squid cell
            **parameters: PCell parameters for the element as keyword arguments

        Returns:
            the created squid cell
        """

        if squid_type is None:
            squid_type = to_library_name(cls.__name__)

        if squid_type:
            squids_library = load_libraries(path=cls.LIBRARY_PATH)[cls.LIBRARY_NAME]
            library_layout = squids_library.layout()
            if squid_type in library_layout.pcell_names():
                # if code-generated, create like a normal element
                pcell_class = squids_library.layout().pcell_declaration(squid_type).__class__
                return Element._create_cell(pcell_class, layout, **parameters)
            elif library_layout.cell(squid_type):
                # if manually designed squid, load from squids.oas
                return layout.create_cell(squid_type, cls.LIBRARY_NAME)
        # fallback to NoSquid if there is no squid corresponding to squid_type
        return layout.create_cell("NoSquid", Squid.LIBRARY_NAME)


@traced
@logged
def replace_squids(cell, squid_type, parameter_name, parameter_start, parameter_step, parameter_end=None):
    """Replaces squids by code generated squids with the given parameter sweep.

    All squids below top_cell in the cell hierarchy are removed. The number of code
    generated squids may be limited by the value of parameter_end.

    Args:
        cell (Cell): The cell where the squids to be replaced are
        squid_type: class name of the code generated squid that replaces the other squids
        parameter_name (str): Name of the parameter to be swept
        parameter_start: Start value of the parameter
        parameter_step: Parameter value increment step
        parameter_end: End value of the parameter. If None, there is no limit for the parameter value, so that all
            squids are replaced

    """
    layout = cell.layout()
    parameter_value = parameter_start
    squid_types = [choice[1] for choice in squid_type_choices]

    old_squids = []  # list of tuples (squid instance, squid dtrans with respect to cell, old name)

    def recursive_replace_squids(top_cell_inst, combined_dtrans):
        """Appends to old_squids all squids in top_cell_inst or any instance below it in hierarchy."""
        # cannot use just top_cell_inst.cell due to klayout bug, see
        # https://www.klayout.de/forum/discussion/1191/cell-shapes-cannot-call-non-const-method-on-a-const-reference
        top_cell = layout.cell(top_cell_inst.cell_index)
        for subcell_inst in top_cell.each_inst():
            subcell_name = subcell_inst.cell.name
            if subcell_name in squid_types:
                old_squids.append((subcell_inst, combined_dtrans*subcell_inst.dtrans, subcell_name))
            else:
                recursive_replace_squids(subcell_inst, combined_dtrans*subcell_inst.dtrans)

    for inst in cell.each_inst():
        if inst.cell.name in squid_types:
            old_squids.append((inst, inst.dtrans, inst.cell.name))
        recursive_replace_squids(inst, inst.dtrans)

    # sort left-to-right and bottom-to-top
    old_squids.sort(key=lambda squid: (squid[1].disp.x, squid[1].disp.y))

    for (inst, dtrans, name) in old_squids:
        if (parameter_end is None) or (parameter_value <= parameter_end):
            # create new squid at old squid's position
            parameters = {parameter_name: parameter_value}
            squid_cell = Squid.create(layout, squid_type=squid_type, face_ids=inst.pcell_parameter("face_ids"),
                                      **parameters)
            cell.insert(pya.DCellInstArray(squid_cell.cell_index(), dtrans))
            replace_squids._log.info("Replaced squid \"{}\" with dtrans={} by a squid \"{}\" with {}={}."
                                     .format(name, dtrans, squid_type, parameter_name, parameter_value))
            parameter_value += parameter_step
        # delete old squid
        inst.delete()
