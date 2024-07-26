# This code is part of KQCircuits
# Copyright (C) 2025 IQM Finland Oy
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


# This file shouldn't import anything substantial from kqcircuits to prevent cyclical import

import logging
import re
from typing import Any, Callable, Sequence
from kqcircuits.pya_resolver import pya


SimulationFunction = Callable[["Simulation"], Any]


def _wrap_constant_or_function(value: Any) -> SimulationFunction:
    """If value is constant, returns function that returns value for any argument"""
    if not callable(value):
        return lambda simulation: value
    return value


def _collect_layers_from_regexes(layer_keys: Sequence[pya.LayerInfo], regexes: Sequence[str]) -> set[pya.LayerInfo]:
    """Given set of layers ``layer_keys``, select layers whose name matches at least one regex from ``regexes``"""
    return set(
        layer_info
        for layer_regex in regexes
        for layer_info in [l for l in layer_keys if re.fullmatch(layer_regex, l.name)]
    )


class CrossSectionProfile:
    """Defines vertical level (bottom, top) values for each layer in order to produce cross section geometry.

    Also contains following features::
        * Level values can be configured using functions ``Simulation -> float``
            so that the value is calculated from Simulation's parameters
        * Set priority by regex - if a shape from one layer overlaps with shape from another layer,
            keep regions disjoint by cutting out the overlap region on former layer
        * Layer in original layout may have its cross section placed at another layer in cross section layout.

    When developing class methods here, please maintain the assumption that a simulation instance passed
    here is not modified.
    """

    def __init__(self):
        self._levels = {}
        self._layer_priority = {}
        self._layer_change_map = {}

        # TODO: This member adjusts the y position of cross section shapes such that they match exactly
        # the cross section geometry generated with XSection. Remove this member eventually.
        self.add_this_to_xor_with_master = 0

    def level(
        self,
        regex: str,
        bottom_function: float | SimulationFunction,
        top_function: float | SimulationFunction,
        change_to_layer: str | SimulationFunction = "",
    ) -> None:
        """Define level values for layers whose name matches ``regex``.

        Args:
            regex: this level configuration takes effect for layers whose name matches regex.
            bottom_function: z value for the bottom of the cross section shape, can be defined as function
            top_function: z value for the top of the cross section shape, can be defined as function
            change_to_layer: (Optional) cross section shapes on layers that match ``regex`` will be placed to
                ``change_to_layer`` layer in cross section layout.
        """
        self._levels[regex] = (_wrap_constant_or_function(bottom_function), _wrap_constant_or_function(top_function))
        self._layer_change_map[regex] = _wrap_constant_or_function(change_to_layer)

    def priority(self, target_layer_regex: str, dominant_layer_regex: str) -> None:
        """Configure profile so that in case a region from a layer that matches ``target_layer_regex``
        overlaps a region that matches ``dominant_layer_regex``, the regions will be made disjoint
        by removing the overlapping region from layer matching ``target_layer_regex``.
        """
        self._layer_priority[target_layer_regex] = _wrap_constant_or_function(dominant_layer_regex)

    def get_layers(self, layout: pya.Layout) -> set[pya.LayerInfo]:
        """Collect all layers from ``layout`` that were configured to this profile using ``level`` function"""
        return _collect_layers_from_regexes(layout.layer_infos(), self._levels)

    def get_level(self, layer_name: str, simulation: "Simulation") -> tuple[float, float]:
        """Given concrete layer name, returns bottom and top level for such layer in cross section profile

        Args:
            layer_name: concrete layer name, not regex
            simulation: simulation object from which cross section is taken

        Returns:
            tuple - coordinate of bottom and top levels for given layer in the cross section profile
        """
        level, first_match = None, None
        for layer_regex, lvl in self._levels.items():
            if re.fullmatch(layer_regex, layer_name):
                if level:
                    logging.warning(f"Layer {layer_name} matches both {first_match} and {layer_regex} regexes")
                else:
                    first_match = layer_regex
                level = lvl
        if not level:
            logging.warning(f"Layer {layer_name} matches no regex configured in the cross section profile")
            return None
        return (level[0](simulation), level[1](simulation))

    def get_dominant_layer_regex(self, layer_name: str, simulation: "Simulation") -> str:
        """Constructs a regex for all layers that have higher priority than ``layer_name``.

        Args:
            layer_name: Name of the layer (not regex) for which we wish to know what layers it is dominated by
            simulation: simulation object from which cross section is taken

        Returns:
            Regex, matching any layer that dominates layer with name ``layer_name``
        """
        dominant_layer_regex = None
        for layer_regex, dom_layers in self._layer_priority.items():
            if re.fullmatch(layer_regex, layer_name):
                dom_layers_value = dom_layers(simulation)
                if dominant_layer_regex:
                    dominant_layer_regex += f"{dominant_layer_regex}|({dom_layers_value})"
                dominant_layer_regex = f"({dom_layers_value})"
        return dominant_layer_regex

    def get_invisible_layers(self, simulation: "Simulation") -> set[pya.LayerInfo]:
        """Setting ``change_to_layer`` to None causes the level to not be written to any layer.
        This function returns all layers that are configured in such way.

        Args:
            simulation: simulation object from which cross section is taken

        Returns:
            Set of layers that will be made invisible in the cross section
        """
        invis_layers = [l_regex for l_regex, l_output in self._layer_change_map.items() if l_output(simulation) is None]
        return _collect_layers_from_regexes(simulation.layout.layer_infos(), invis_layers)

    def change_layer(self, input_layer: pya.LayerInfo, simulation: "Simulation") -> pya.LayerInfo:
        """Given ``input_layer`` on original layout, returns which layer on the cross section layout
        the shapes should be added to.

        Args:
            input_layer: Layer in original layout, for which to look up the layer on the cross section layout
            simulation: simulation object from which cross section is taken

        Returns:
            Layer on the cross section layout, where the cross section shape of ``input_layer`` will be written to.
        """
        output_layer = None
        previous_layer_regex = None
        for layer_regex, layer in self._layer_change_map.items():
            if re.fullmatch(layer_regex, input_layer.name):
                if output_layer:
                    logging.warning(
                        f"Layer {input_layer} matching '{layer_regex}' already matched '{previous_layer_regex}'"
                    )
                layer_value = layer(simulation)
                if layer_value != "":
                    output_layer = layer_value
                    previous_layer_regex = layer_regex

        # input_layer not configured to change, so we just write the cross section to input_layer
        if not output_layer:
            return input_layer

        # Find pya.LayerInfo with output_layer as name
        layer_info_matches = [l for l in set(simulation.layout.layer_infos()) if l.name == output_layer]
        if len(layer_info_matches) > 1:
            logging.warning(
                f"Multiple layers with name {output_layer} found: {layer_info_matches}. Returning first layer."
            )
        if not layer_info_matches:
            logging.warning(f"No layers found with name {output_layer}. Initialising such layer")
            return pya.LayerInfo(output_layer)
        return layer_info_matches[0]

    def add_face(self, face_id: str) -> None:
        """Add standard configuration within KQC context for given face"""
        # Use face_z_levels to determine levels for ground metal
        self.level(
            f"{face_id}_ground", lambda s: s.face_z_levels()[face_id][0], lambda s: s.face_z_levels()[face_id][1]
        )
        # Do the same for all signal metals
        self.level(
            f"{face_id}_signal_?[0-9]*",
            lambda s: s.face_z_levels()[face_id][0],
            lambda s: s.face_z_levels()[face_id][1],
        )
        # Also determine level for possible dielectric layer between metals
        self.level(
            f"{face_id}_dielectric", lambda s: s.face_z_levels()[face_id][0], lambda s: s.face_z_levels()[face_id][2]
        )
        # Remove parts of dielectric if metal shapes overlap with it
        self.priority(f"{face_id}_dielectric", f"{face_id}_ground|({face_id}_signal_?[0-9]*)")


# Prepared cross section profiles


def get_single_face_cross_section_profile() -> CrossSectionProfile:
    """Standard KQC single face cross section profile"""
    profile = CrossSectionProfile()
    profile.add_this_to_xor_with_master = 0.0  # TODO: remove this
    # Add standard 1t1 face
    profile.add_face("1t1")
    # Define levels for bottom substrate
    profile.level(
        "substrate_1",
        lambda s: s.face_z_levels()["1t1"][0] - s.substrate_height[0],
        lambda s: s.face_z_levels()["1t1"][0],
    )
    # Define levels for gaps (including possible over etching) and change it to vacuum layer
    profile.level(
        "1t1_gap",
        lambda s: s.face_z_levels()["1t1"][0] - s.vertical_over_etching,
        lambda s: s.face_z_levels()["1t1"][0],
        change_to_layer="vacuum",
    )
    # Make sure gap regions eat away from substrate
    profile.priority("substrate_1", "1t1_gap")
    return profile


def get_flip_chip_cross_section_profile() -> CrossSectionProfile:
    """Standard KQC flip chip cross section profile"""
    # Take single face profile and add stuff on top of it
    profile = get_single_face_cross_section_profile()
    profile.add_this_to_xor_with_master = -383.4  # TODO: remove this
    # Add standard 2b1 face
    profile.add_face("2b1")
    # Define levels for top substrate
    profile.level(
        "substrate_2",
        lambda s: s.face_z_levels()["2b1"][0] + s.substrate_height[1],
        lambda s: s.face_z_levels()["2b1"][0],
    )
    # Define levels for gaps (including possible over etching) and change it to vacuum layer
    profile.level(
        "2b1_gap",
        lambda s: s.face_z_levels()["2b1"][0] + s.vertical_over_etching,
        lambda s: s.face_z_levels()["2b1"][0],
        change_to_layer="vacuum",
    )
    # Make sure gap regions eat away from substrate
    profile.priority("substrate_2", "2b1_gap")
    return profile


def get_cross_section_profile(simulation: "Simulation") -> CrossSectionProfile:
    """Given simulation's face_stack, either returns single face or flip chip cross section profile"""
    if len(simulation.face_stack) > 1:
        return get_flip_chip_cross_section_profile()
    return get_single_face_cross_section_profile()
