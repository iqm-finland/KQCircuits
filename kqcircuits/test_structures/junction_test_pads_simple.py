# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import numpy

from kqcircuits.test_structures.junction_test_pads import JunctionTestPads


class JunctionTestPadsSimple(JunctionTestPads):
    """Junction test structures.

    Produces an array of junction test structures within the given area. Each structure consists of a SQUID,
    which is connected to pads. There can be either 2 or 4 pads per SQUID, depending on the configuration.
    Optionally, it is possible to produce only pads without any SQUIDs.
    """

    def produce_impl(self):

        self.junction_spacing = 0
        self.extra_arm_length = 0

        super()._produce_impl()
