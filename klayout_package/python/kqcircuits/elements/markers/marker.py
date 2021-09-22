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

from kqcircuits.util.library_helper import load_libraries, to_library_name
from kqcircuits.elements.element import Element
from kqcircuits.defaults import default_marker_type


@traced
@logged
class Marker(Element):
    """Base Class for Markers."""

    @classmethod
    def create(cls, layout, library=None, marker_type=None, **parameters):
        """Create a Marker cell in layout.

        Args:
            layout: pya.Layout object where the cell is created
            library: LIBRARY_NAME of the calling PCell instance
            marker_type: (str): name of the Marker subclass
            **parameters: PCell parameters as keyword arguments

        Returns:
            the created Marker cell
        """

        if marker_type is None:
            marker_type = to_library_name(cls.__name__)

        library_layout = (load_libraries(path=cls.LIBRARY_PATH)[cls.LIBRARY_NAME]).layout()
        if marker_type in library_layout.pcell_names():
            pcell_class = type(library_layout.pcell_declaration(marker_type))
            return Element._create_cell(pcell_class, layout, library, **parameters)
        elif marker_type != default_marker_type:
            return Marker.create(layout, library, marker_type=default_marker_type, **parameters)
        else:
            raise ValueError(f'Unknown Marker subclass "{marker_type}"!')
