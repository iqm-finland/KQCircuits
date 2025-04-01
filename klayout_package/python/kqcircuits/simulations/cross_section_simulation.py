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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).


import abc

import logging

from kqcircuits.elements.element import Element
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.simulation import Simulation, get_simulation_layer_by_name
from kqcircuits.util.geometry_helper import merge_points_and_match_on_edges
from kqcircuits.util.parameters import add_parameters_from


@add_parameters_from(Simulation, "name", "material_dict", "extra_json_data")
class CrossSectionSimulation:
    """Base class for cross-section simulation geometries.

    The geometry consist of 2-dimensional layers which are thought as cross sections of 3-dimensional geometry.
    This allows for modeling waveguide-like geometries where the cross section is constant for relatively long segments.

    This class is intended to be subclassed by a specific simulation implementation; The subclass should implement the
    method 'build' which defines the simulation geometry and material properties. The helper function 'insert_layer'
    should be called internally to build the geometry.
    """

    LIBRARY_NAME = None  # This is needed by some methods inherited from Element.

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

        self.cell = kwargs["cell"] if "cell" in kwargs else layout.create_cell(self.name)

        self.layers = {}
        self.units = kwargs.get("units", "um")
        self.build()
        self.process_layers()

    # Inherit specific methods from Element
    get_schema = classmethod(Element.get_schema.__func__)
    get_layers = Simulation.get_layers
    get_parameters = Simulation.get_parameters
    is_metal = Simulation.is_metal
    get_material_dict = Simulation.get_material_dict
    check_material_dict = Simulation.check_material_dict

    @abc.abstractmethod
    def build(self):
        """Build simulation geometry.

        This method is to be overridden, and the overriding method should create the geometry to be simulated.
        """
        return

    def process_layers(self):
        """Process and check validity of self.layers. Is called after build method.

        Internally,
        * call merge_points_and_match_on_edges to avoid small-scale geometry artifacts
        * ignore layers with empty region
        * check if 'excitation' keywords are set correctly
        * insert layer shapes to self.cell.shapes and replace 'region' keyword with 'layer' keyword.
        """
        merge_points_and_match_on_edges([layer["region"] for layer in self.layers.values()], tolerance=1)

        layers = {}
        for name, data in self.layers.items():
            if data["region"].is_empty():
                continue  # ignore layer with empty region

            # check if excitation keyword is set correctly
            if self.is_metal(data.get("material")):
                if "excitation" not in data:
                    raise ValueError(f"Layer {name} is metal but integer excitation value is not set.")
                if not isinstance(data["excitation"], int):
                    raise ValueError(f"Excitation should be integer but {data['excitation']} is set for layer {name}.")
            elif "excitation" in data:
                raise ValueError(f"Layer {name} is dielectric but excitation value is set.")

            # insert layer shape to self.cell.shapes and replace region keyword with layer keyword
            layer_info = get_simulation_layer_by_name(name)
            self.cell.shapes(self.layout.layer(layer_info)).insert(data["region"])
            layers[name] = {"layer": layer_info.layer, **{k: v for k, v in data.items() if k != "region"}}

        self.layers = layers

    def insert_layer(self, layer_name: str, region: pya.Region, material: str, **params):
        """Add layer parameters into 'self.layers' if region is non-empty."""
        if not region.is_empty():
            self.layers[layer_name] = {"region": region.dup(), "material": material, **params}

    def restrict_layer_regions(self, bbox: pya.DBox):
        """Limit the regions of self.layers inside the bounding box."""
        region = pya.Region(bbox.to_itype(self.layout.dbu))
        for layer in self.layers.values():
            layer["region"] &= region

    def get_unfilled_region(self, bbox: pya.DBox) -> pya.Region:
        """Return region inside bbox that is not covered yet by layers."""
        region = pya.Region(bbox.to_itype(self.layout.dbu))
        for layer in self.layers.values():
            region -= layer["region"]
        return region

    def get_simulation_data(self):
        """Return the simulation data in dictionary form.

        Returns:
            dictionary of relevant parameters for simulation
        """
        simulation_data = {
            "simulation_name": self.name,
            "units": self.units,
            "layers": self.layers,
            "material_dict": self.check_material_dict(),
        }
        return simulation_data
