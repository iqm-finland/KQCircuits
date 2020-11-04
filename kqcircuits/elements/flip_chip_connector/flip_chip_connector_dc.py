# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from autologging import logged, traced
from kqcircuits.elements.flip_chip_connector.flip_chip_connector import FlipChipConnector

@traced
@logged
class FlipChipConnectorDc(FlipChipConnector):
    """PCell declaration for an inter-chip dc connector."""

    def produce_impl(self):
        self.create_bump_connector()
        super().produce_impl()