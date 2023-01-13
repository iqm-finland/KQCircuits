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
    """Base data structure for simulation ports.

    Depending on your simulation type, these produce excitations, set potentials, or act as ideal RLC lumped elements.
    """
    def __init__(self, number: int,
                 resistance: float = 50, reactance: float = 0, inductance: float = 0, capacitance: float = 0,
                 face: int = 0, junction: bool = False):
        """
        Args:
            number: Port number.
            resistance: Real part of impedance. Given in Ohms (:math:`\\Omega`).
            reactance: Imaginary part of impedance. Given in Ohms (:math:`\\Omega`).
            inductance: Inductance of the element. Given in Henrys (:math:`\\text{H}`).
            capacitance: Capacitance of the element. Given in Farads (:math:`\\text{F}`).
            face: Integer-valued face index for the port.
            junction: Whether this port models a SQUID/Junction. Used in EPR calculations.
        """
        self.number = number
        self.resistance = resistance
        self.reactance = reactance
        self.inductance = inductance
        self.capacitance = capacitance
        self.face = face
        self.junction = junction
        self.type = type(self).__name__

    def as_dict(self):
        """Returns attributes as a dictionary."""
        return vars(self)


class InternalPort(Port):
    """Data structure for ports inside the simulation area."""
    def __init__(self, number: int, signal_location: DPoint, ground_location: DPoint = None,
                 resistance: float = 50, reactance: float = 0, inductance: float = 0, capacitance: float = 0,
                 face: int = 0, junction: bool = False, signal_layer: str = 'signal'):
        """
        Args:
            number: Port number.
            signal_location: Edge location for signal source.
            ground_location: Edge location to connect signal to. Usually ground.
            resistance: Real part of impedance. Given in Ohms (:math:`\\Omega`).
            reactance: Imaginary part of impedance. Given in Ohms (:math:`\\Omega`).
            inductance: Inductance of the element. Given in Henrys (:math:`\\text{H}`).
            capacitance: Capacitance of the element. Given in Farads (:math:`\\text{F}`).
            face: Integer-valued face index for the port.
            junction: Whether this port models a SQUID/Junction. Used in EPR calculations.
            signal_layer: Manual override for simulation signal layer.
                May be used to set ports across the ground layer with ``ground``.
        """
        super().__init__(number, resistance, reactance, inductance, capacitance, face, junction)
        self.signal_location = signal_location
        self.signal_layer = signal_layer
        if ground_location is not None:
            self.ground_location = ground_location


class EdgePort(Port):
    """Data structure for ports at the edge of the simulation area."""
    def __init__(self, number: int, signal_location: DPoint,
                 resistance: float = 50, reactance: float = 0, inductance: float = 0, capacitance: float = 0,
                 deembed_len: float = None, face: int = 0, junction: bool = False):
        """
        Args:
            number: Port number.
            signal_location: Edge location for signal source.
            resistance: Real part of impedance. Given in Ohms (:math:`\\Omega`).
            reactance: Imaginary part of impedance. Given in Ohms (:math:`\\Omega`).
            inductance: Inductance of the element. Given in Henrys (:math:`\\text{H}`).
            capacitance: Capacitance of the element. Given in Farads (:math:`\\text{F}`).
            deembed_len: Port de-embedding length. Given in simulation units, usually microns (:math:`\\text{um}`).
            face: Integer-valued face index for the port.
            junction: Whether this port models a SQUID/Junction. Used in EPR calculations.
        """
        super().__init__(number, resistance, reactance, inductance, capacitance, face, junction)
        self.signal_location = signal_location
        self.deembed_len = deembed_len
