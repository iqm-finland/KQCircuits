# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.simulations.simulation import Simulation
from kqcircuits.pya_resolver import pya


class EmptySimulation(Simulation):

    def build(self):
        pass
