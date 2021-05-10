# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy's prior
# written permission.


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

