# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.chips.chip import Chip
from kqcircuits.pya_resolver import pya


class DcTest(Chip):
    """Chip with launchers for DC sample holder."""

    def produce_impl(self):

        self.produce_launchers_DC()

        super().produce_impl()
