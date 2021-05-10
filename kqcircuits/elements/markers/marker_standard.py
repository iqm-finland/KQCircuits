# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.markers.marker import Marker


class MarkerStandard(Marker):
    """The PCell declaration for the Standard Marker."""

    def produce_impl(self):
        self._produce_impl()
