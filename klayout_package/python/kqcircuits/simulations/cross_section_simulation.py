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


import abc

import logging

from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.simulation import Simulation, get_simulation_layer_by_name
from kqcircuits.util.parameters import Param, pdt, add_parameters_from


@add_parameters_from(Simulation, 'name', 'box', 'extra_json_data')
class CrossSectionSimulation:
    """Class for co-planar waveguide cross-section simulations.

    This class is intended to be subclassed by a specific simulation implementation;  The subclass should implement the
    method 'build' which defines the simulation geometry and material properties.

    Layer names in cross-section geometry don't need to obey KQC default layers. The layers use following name coding:
    - Layer name 'vacuum' is reserved for vacuum material. The vacuum layer can be left empty; then the simulation
    export fills the empty space inside the 'box' with vacuum.
    - All layers that include word 'signal' are considered as signal metals. Different signal layers are considered as
    separate signals so that the result matrices has row and column for each signal layer. The order of signals is the
    same as where they are introduced by calling 'get_sim_layer' function.
    - All layers that include word 'ground'  are considered as ground metal.
    - Any other layer is considered as dielectric. The permittivity can be set using the 'set_permittivity' function.
    """

    LIBRARY_NAME = None  # This is needed by some methods inherited from Element.

    london_penetration_depth = Param(
        pdt.TypeDouble, "London penetration depth of metals", 0.0, unit='m',
        docstring="London penetration depth is implemented for one signal simulation only"
    )
    xsection_source_class = Param(
        pdt.TypeNone, "Simulation class XSection tool was used on", None, docstring=
        "Class from which the simulation was generated from using the XSection tool. Used to get the correct schema."
    )

    def __init__(self, layout, **kwargs):
        """Initialize a CrossSectionSimulation.

        The initializer parses parameters, creates a top cell, and then calls `self.build` to create
        the simulation geometry.

        Args:
            layout: the layout on which to create the simulation

        Keyword arguments:
            `**kwargs`:
                Any parameter can be passed as a keyword argument.
        """
        if layout is None or not isinstance(layout, pya.Layout):
            error_text = "Cannot create simulation with invalid or nil layout."
            error = ValueError(error_text)
            logging.error(error_text)
            raise error

        self.layout = layout
        schema = type(self).get_schema()

        # Apply kwargs or default value
        for parameter, item in schema.items():
            if parameter in kwargs:
                setattr(self, parameter, kwargs[parameter])
            else:
                setattr(self, parameter, item.default)

        self.cell = kwargs['cell'] if 'cell' in kwargs else layout.create_cell(self.name)

        self.layer_dict = dict()
        self.permittivity_dict = dict()
        self.units = kwargs.get('units', 'um')
        self.build()

    # Inherit specific methods from Element
    get_schema = classmethod(Element.get_schema.__func__)

    @abc.abstractmethod
    def build(self):
        """Build simulation geometry.

        This method is to be overridden, and the overriding method should create the geometry to be simulated.
        """
        return

    def register_cell_layers_as_sim_layers(self):
        """Takes all layers that contain any geometry and registers them as simulation layers

        This method resets the internal simulation layer dictionary.
        """
        self.layer_dict = dict()
        self.permittivity_dict = dict()
        for l in self.layout.layer_infos():
            if len(list(self.cell.each_shape(self.layout.layer(l)))) > 0:
                self.layer_dict[l.name] = l

    def get_sim_layer(self, layer_name):
        """Returns layer of given name. If layer doesn't exist, a new layer is created."""
        if layer_name not in self.layer_dict:
            layer_info = None
            for l in self.layout.layer_infos():
                if l.datatype == 0 and l.name == layer_name:
                    # If there is a layer with layer_name in layout (used by other cell), reuse that
                    layer_info = l
            if layer_info is None:
                layer_info = get_simulation_layer_by_name(layer_name)
            self.layer_dict[layer_name] = layer_info
        return self.layout.layer(self.layer_dict[layer_name])

    def set_permittivity(self, layer_name, permittivity):
        """Sets permittivity for layer of given name."""
        self.permittivity_dict[layer_name] = permittivity

    def get_parameters(self):
        """Return dictionary with all parameters and their values."""
        return {
            param: getattr(self, param)
            for param in (self.xsection_source_class or type(self)).get_schema()
        }

    def get_simulation_data(self):
        """Return the simulation data in dictionary form.

        Returns:
            dictionary of relevant parameters for simulation
        """
        simulation_data = {
            'gds_file': self.name + '.gds',
            'units': self.units,
            'box': self.box,
            "london_penetration_depth": self.london_penetration_depth,
            **{'{}_permittivity'.format(k): v for k, v in self.permittivity_dict.items()},
            'parameters': self.get_parameters(),
        }
        return simulation_data
