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


from kqcircuits.elements.finger_capacitor_square import FingerCapacitorSquare
from kqcircuits.elements.smooth_capacitor import SmoothCapacitor


def cap_params(fingers, length=None, coupler_type="interdigital", element_key='cls', **kwargs):
    """An utility function to easily produce typical finger capacitor instance parameters.
    Covers FingerCapacitorSquare and SmoothCapacitor.

    Args:
        fingers: number of fingers in FingerCapacitorSquare or finger control parameter in SmoothCapacitor.
        length: length of fingers in FingerCapacitorSquare (useless parameter in SmoothCapacitor)
        coupler_type: a string describing the capacitor type (accepts "interdigital", "gap", "ground gap", or "smooth")
        element_key: dictionary key in which coupler Element is returned (use 'cls'=default with `add_element` function
                     or 'cell' with `insert_cell` function)
        **kwargs: other optional parameters

    Returns:
        dictionary of coupler parameters
    """
    if coupler_type == 'smooth':
        return {element_key: SmoothCapacitor,
                'finger_control': fingers,
                "finger_width": 10,
                "ground_gap": 10,
                "finger_gap": 5,
                **kwargs}

    defaults = {element_key: FingerCapacitorSquare,
                "finger_number": int(fingers),
                "finger_length": length,
                "finger_gap_end": 5,
                "finger_gap": 5,
                "finger_width": 15,
                "ground_padding": 10,
               }

    params = {}

    if coupler_type == "gap":
        params = {"finger_length": 0,
                  "finger_gap_end": length,
                  "finger_gap": 0,
                  "finger_width": 10,
                 }
    elif coupler_type == "ground gap":
        params = {"finger_length": 0,
                  "finger_gap_end": length,
                  "finger_gap": 50 - length / 2,
                  "finger_width": 20,
                  "ground_gap_ratio": 1/3
                  }

    return {**defaults, **params, **kwargs}
