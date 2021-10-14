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


def cap_params(fingers, length, coupler_type="interdigital", **kwargs):
    """A utility function to easily produce typical FingerCapacitorSquare instance parameters.

    Args:
        fingers: number of fingers
        length: length of fingers
        coupler_type: a string describing the capacitor type
        **kwargs: other optional parameters
    """

    defaults = {"finger_number": fingers,
                "finger_length": length,
                "finger_gap_end": 5,
                "finger_gap_side": 5,
                "finger_width": 15,
                "ground_padding": 10,
               }

    params = {}

    if coupler_type == "gap":
        params = {"finger_length": 0,
                  "finger_gap_end": length,
                  "finger_gap_side": 0,
                  "finger_width": 10,
                 }
    elif coupler_type == "fc gap":
        params = {"finger_length": 0,
                  "finger_gap_end": length,
                  "ground_padding": 15,
                 }
    elif coupler_type == "fc interdigital":
        params = {"ground_padding": 15,
                 }

    return {**defaults, **params, **kwargs}
