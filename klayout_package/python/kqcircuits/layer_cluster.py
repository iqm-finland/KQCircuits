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



class LayerCluster:
    """Container class for a cluster of layers.

    Some files need to be exported with certain clusters of layers, for example for EBL process. This class wraps
    information about such layer cluster.

    Attributes:
        main_layers: list of names of the layers which should contain shapes for this cluster to be exported
        extra_layers: list of names of other layers exported together with main_layers
        face_id: face_id of the layers in this cluster

    """

    def __init__(self, main_layers, extra_layers, face_id):
        self.main_layers = main_layers
        self.extra_layers = extra_layers
        self.face_id = face_id

    def all_layers(self):
        """Returns main_layers + extra_layers."""
        return self.main_layers + self.extra_layers
