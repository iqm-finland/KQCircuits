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


"""PCell declaration classes for elements.

Elements represent all the different structures that form a quantum circuit. They are implemented as PCells, with the
base class of Element being PCellDeclarationHelper. After loading elements into KLayout PCell libraries, they can be
placed in a layout using the KLayout GUI or in code.

Elements contain some shared PCell parameters, including a list of refpoints which can be used to position them. They
also have methods that make it easy to create elements with different parameters and insert them to other elements.

Elements support a concept of faces, which is used for 3D-integrated chips to place shapes in layers belonging to a
certain chip face. For example, an element may create shapes in face 0 and face 1, and the ``face_ids`` parameter
of the element determines which actual chip faces the faces 0 and 1 refer to.
"""
