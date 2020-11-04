# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.elements.finger_capacitor_taper import FingerCapacitorTaper


def produce_library_capacitor(layout, fingers, length, coupler_type="square", **kwargs):
    # Capacitor
    if (coupler_type == "plate"):
        cap = FingerCapacitorSquare.create(layout,
                                           finger_number=fingers,
                                           finger_length=0,
                                           finger_gap_end=length,
                                           finger_gap_side=0,
                                           finger_width=10,
                                           ground_padding=10,
                                           # corner_r=0,
                                           **kwargs
                                           )
    elif (coupler_type == "square"):
        cap = FingerCapacitorSquare.create(layout,
                                           finger_number=fingers,
                                           finger_length=length,
                                           finger_gap_end=5,
                                           finger_gap_side=5,
                                           finger_width=15,
                                           ground_padding=10,
                                           **kwargs
                                           )
    elif coupler_type == "fc plate":
        # based on simulation parameters
        cap = FingerCapacitorSquare.create(layout,
                                           finger_number=fingers,
                                           finger_length=0,
                                           finger_gap_end=length,
                                           finger_gap_side=5,
                                           finger_width=15,
                                           ground_padding=15,
                                           **kwargs
                                           )
    elif coupler_type == "fc square":
        # based on simulation parameters
        cap = FingerCapacitorSquare.create(layout,
                                           finger_number=fingers,
                                           finger_length=length,
                                           finger_gap_end=5,
                                           finger_gap_side=5,
                                           finger_width=15,
                                           ground_padding=15,
                                           **kwargs
                                           )
    else:
        cap = FingerCapacitorTaper.create(layout,
                                          finger_number=fingers,
                                          finger_length=length,
                                          finger_gap=5,
                                          finger_width=15,
                                          ground_padding=10,
                                          taper_length=(fingers * 20 - 5) / 2.,  # 45 degree taper,
                                          **kwargs
                                          )
    return cap
