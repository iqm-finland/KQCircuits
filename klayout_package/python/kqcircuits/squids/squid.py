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

    junction_width = Param(pdt.TypeDouble, "Junction width for code generated squids", 0.02, unit="[μm]",
                           docstring="Junction width (only used for code generated squids)")
    loop_area = Param(pdt.TypeDouble, "Loop area", 100, unit="μm^2")

    @classmethod
    def create(cls, layout, library=None, squid_type=None, **parameters):
        """Create cell for a squid in layout.

        The squid cell is created either from a pcell class or a from a manual design file, depending on squid_type. If
        squid_type does not correspond to any squid, an empty "NoSquid" squid is returned.

        Overrides Element.create(), so that functions like add_element() and insert_cell() will call this instead.

        Args:
            layout: pya.Layout object where this cell is created
            library: LIBRARY_NAME of the calling PCell instance
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
                return Element._create_cell(pcell_class, layout, library, **parameters)
            elif library_layout.cell(squid_type):
                # if manually designed squid, load from squids.oas
                return layout.create_cell(squid_type, cls.LIBRARY_NAME)

        # fallback to NoSquid if there is no squid corresponding to squid_type
        return layout.create_cell("NoSquid", Squid.LIBRARY_NAME)
