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


from kqcircuits.pya_resolver import pya
DPoint = pya.DPoint


class Port:
    """Base data structure for simulation ports."""
    def __init__(self, number: int,
                 resistance: float = 50, reactance: float = 0, inductance: float = 0, capacitance: float = 0,
                 face: int = 0):
        self.number = number
        self.resistance = resistance
        self.reactance = reactance
        self.inductance = inductance
        self.capacitance = capacitance
        self.face = face
        self.type = type(self).__name__

    def as_dict(self):
        return vars(self)


class InternalPort(Port):
    """Data structure for ports inside the simulation area."""
    def __init__(self, number: int, signal_location: DPoint, ground_location: DPoint,
                 resistance: float = 50, reactance: float = 0, inductance: float = 0, capacitance: float = 0,
                 face: int = 0):
        super().__init__(number, resistance, reactance, inductance, capacitance, face)
        self.signal_location = signal_location
        self.ground_location = ground_location


class EdgePort(Port):
    """Data structure for ports at the edge of the simulation area."""
    def __init__(self, number: int, signal_location: DPoint,
                 resistance: float = 50, reactance: float = 0, inductance: float = 0, capacitance: float = 0,
                 deembed_len: float = None, face: int = 0):
        super().__init__(number, resistance, reactance, inductance, capacitance, face)
        self.signal_location = signal_location
        self.deembed_len = deembed_len
