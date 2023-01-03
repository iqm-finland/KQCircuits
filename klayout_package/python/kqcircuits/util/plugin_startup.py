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


from kqcircuits.util.edit_node_plugin import EditNodePluginFactory


_plugins_registered = False


def register_plugins():
    """ Register KQC plugins into KLayout. Registration happens only one.

    Note: For KLayout 0.28.0 and up, plugin registration must happen before any layout views are created.
    """
    global _plugins_registered  # pylint: disable=global-statement
    if not _plugins_registered:
        _plugins_registered = True

        # Register the Edit Node plugin
        EditNodePluginFactory()
