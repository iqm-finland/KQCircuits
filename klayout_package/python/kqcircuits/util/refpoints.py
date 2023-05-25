# This code is part of KQCircuits
# Copyright (C) 2022 IQM Finland Oy
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


class Refpoints:
    """Helper class for extracting reference points from given layer and cell.

    Once Refpoints is initialized, it can be used similar way as dictionary, where reference point text (string) field
    is the key and reference point position (pya.DPoint) is the value.

    Refpoints is implemented such that the dictionary is extracted from given layer and cell only when it's used for the
    first time. Extracting the dictionary can be relatively time-demanding process, so this way we can speed up the
    element creation process in KQC.

    Attributes:
        layer: layer specification for source of reference points
        cell: cell containing the reference points
        trans: transform for converting reference points into target coordinate system
        rec_levels: recursion level when looking for reference points from subcells. Set to 0 to disable recursion.
    """
    def __init__(self, layer, cell, trans, rec_levels):
        self.layer = layer
        self.cell = cell
        self.trans = trans
        self.rec_levels = rec_levels
        self.refpoints = None

    def dict(self):
        """Extracts and returns reference points as dictionary, where text is the key and position is the value."""
        if self.refpoints is None:
            self.refpoints = {}
            shapes_iter = pya.RecursiveShapeIterator(self.cell.layout(), self.cell, self.layer)
            if self.rec_levels is not None:
                shapes_iter.max_depth = self.rec_levels
            while not shapes_iter.at_end():
                shape = shapes_iter.shape()
                if shape.type() in (pya.Shape.TText, pya.Shape.TTextRef):
                    self.refpoints[shape.text_string] = self.trans * (shapes_iter.dtrans()*pya.DPoint(shape.text_dpos))
                shapes_iter.next()
        return self.refpoints

    def __iter__(self):
        """Returns iterator"""
        return iter(self.dict())

    def __getitem__(self, item):
        """The [] operator to return position for given reference point text."""
        return self.dict()[item]

    def __setitem__(self, item, value):
        """The [] operator to set a new reference point."""
        self.dict()[item] = value

    def items(self):
        """Returns a list of text-position pairs."""
        return self.dict().items()

    def keys(self):
        """Returns a list of texts."""
        return self.dict().keys()

    def values(self):
        """Returns a list of positions."""
        return self.dict().values()

class RefpointToSimPort:
    """Class that takes a refpoint of an Element class with given string
    and places appropriate Simulation port(s) at the refpoint's location
    if the simulation object was instantiated using the `get_single_element_sim_class`
    class builder.

    Attributes:
        refpoint: Refpoint name string
        face: index of the face where the refpoint is located
    """
    def __init__(self, refpoint, face=0):
        self.refpoint, self.face = refpoint, face

class RefpointToInternalPort(RefpointToSimPort):
    """Creates an InternalPort at refpoint with given string
    """
    def __init__(self, refpoint, ground_refpoint,
                 resistance=50, reactance=0, inductance=0, capacitance=0,
                 face=0, junction=False, signal_layer='signal'):
        super().__init__(refpoint, face)
        self.ground_refpoint, self.resistance, self.reactance, self.inductance, self.capacitance, \
            self.junction, self.signal_layer = \
            ground_refpoint, resistance, reactance, inductance, capacitance, junction, signal_layer

class RefpointToEdgePort(RefpointToSimPort):
    """Creates an EdgePort at refpoint with given string
    """
    def __init__(self, refpoint,
                 resistance=50, reactance=0, inductance=0, capacitance=0,
                 face=0, deembed_len=None, junction=False):
        super().__init__(refpoint, face)
        self.resistance, self.reactance, self.inductance, self.capacitance, \
            self.deembed_len, self.junction = \
            resistance, reactance, inductance, capacitance, deembed_len, junction


class WaveguideToSimPort(RefpointToSimPort):
    """A waveguide is created leading to the port at the refpoint with given string in the Simulation object

    Attributes:
        refpoint: Refpoint name string
        face: index of the face where the `refpoint` is located
        towards: Another refpoint name string towards which direction the waveguide will extend.
                 If set to None, will default to "{refpoint}_corner"
        side: Indicate on which edge the port should be located. Ignored for internal ports.
              Must be one of `left`, `right`, `top` or `bottom`
        use_internal_ports: if True, ports will be inside the simulation. If False, ports will be
            brought out to an edge of the box, determined by `side`.
            Defaults to the value of the `use_internal_ports` parameter
        waveguide_length: length of the waveguide (μm), used only for internal ports
            Defaults to the value of the `waveguide_length` parameter
        term1: Termination gap (μm) at the location of `refpoint`
        turn_radius: Turn radius of the waveguide. Not relevant for internal ports.
            Defaults to the value of the `r` parameter
        a: Center conductor width. Defaults to the value of the `a` parameter
        b: Conductor gap width. Defaults to the value of the `b` parameter
        over_etching: Expansion of gaps. Defaults to the value of the `over_etching` parameter
        airbridge: if True, an airbridge will be inserted at location of the `refpoint`. Default False
    """
    def __init__(self, refpoint, face=0, towards=None, side=None, use_internal_ports=None,
                 waveguide_length=None, term1=0, turn_radius=None, a=None, b=None, over_etching=None, airbridge=False):
        super().__init__(refpoint, face)
        self.towards, self.side, self.use_internal_ports, self.waveguide_length, \
            self.term1, self.turn_radius, self.a, self.b, self.over_etching, self.airbridge = \
            towards, side, use_internal_ports, waveguide_length, term1, turn_radius, a, b, over_etching, airbridge

class JunctionSimPort(RefpointToSimPort):
    """Creates internal ports for a junction in the Simulation object.

    Depending on the value of the `separate_island_internal_ports` parameter, will either create
    two internal ports at both ends of the junction, or one port that covers both junctions.

    Attributes:
        refpoint: Refpoint name string. Defaults to "port_squid_a" as most commonly used junction port name
        other_refpoint: Refpoint name string of the other end of the junction
                        Defaults to "port_squid_b" as most commonly used junction port name
        face: index of the face where the `refpoint` is located
    """
    def __init__(self, refpoint="port_squid_a", other_refpoint="port_squid_b", face=0):
        super().__init__(refpoint, face)
        self.other_refpoint = other_refpoint
