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


from kqcircuits.test_structures.junction_test_pads.junction_test_pads import JunctionTestPads


class JunctionTestPadsSimple(JunctionTestPads):
    """Junction test structures.

    Produces an array of junction test structures within the given area. Each structure consists of a Junction,
    which is connected to pads. There can be either 2 or 4 pads per Junction, depending on the configuration.
    Optionally, it is possible to produce only pads without any Junctions.
    """

    def build(self):

        self.junction_spacing = 0
        super()._produce_impl()
