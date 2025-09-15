# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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

from typing import Callable
from kqcircuits.elements.element import Element
from kqcircuits.junctions import junction_type_choices
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.partition_region import PartitionRegion
from kqcircuits.simulations.port import InternalPort, EdgePort
from kqcircuits.util.parameters import Param, pdt, add_parameters_from
from kqcircuits.util.refpoints import RefpointToInternalPort, RefpointToEdgePort, WaveguideToSimPort, JunctionSimPort


def _get_build_function(
    element_class, ignore_ports, transformation_from_center, sim_junction_type, deembed_cross_sections
):
    def _build_for_element_class(self):
        if sim_junction_type not in junction_type_choices:
            raise ValueError(
                f"Unknown sim_junction_type {sim_junction_type}. "
                f"Junction type should be listed in junction_type_choices"
            )

        simulation_cell = self.add_element(
            element_class, **{**self.get_parameters(), "junction_type": sim_junction_type, "fluxline_type": "none"}
        )

        element_trans = pya.DTrans(0, False, self.box.center())
        if transformation_from_center is not None:
            element_trans *= transformation_from_center(simulation_cell)
        _, refp = self.insert_cell(simulation_cell, element_trans, rec_levels=None)
        self.refpoints = refp

        if deembed_cross_sections is not None:
            deembed_cs_names = deembed_cross_sections.keys()
        else:
            deembed_cs_names = set()

        # Add ports
        port_i = 0
        for port in element_class.get_sim_ports(self):
            if ignore_ports is not None and port.refpoint in ignore_ports:
                continue

            if port.refpoint in deembed_cs_names:
                port.deembed_cross_section = deembed_cross_sections[port.refpoint]

            if isinstance(port, RefpointToInternalPort):
                self.ports.append(
                    InternalPort(
                        number=(port_i := port_i + 1),
                        signal_location=refp[port.refpoint],
                        ground_location=None if not port.ground_refpoint else refp[port.ground_refpoint],
                        resistance=port.resistance,
                        reactance=port.reactance,
                        inductance=port.inductance,
                        capacitance=port.capacitance,
                        face=port.face,
                        junction=port.junction,
                    )
                )
            elif isinstance(port, RefpointToEdgePort):
                self.ports.append(
                    EdgePort(
                        number=(port_i := port_i + 1),
                        signal_location=refp[port.refpoint],
                        resistance=port.resistance,
                        reactance=port.reactance,
                        inductance=port.inductance,
                        capacitance=port.capacitance,
                        deembed_len=port.deembed_len,
                        face=port.face,
                        junction=port.junction,
                        size=port.size,
                        deembed_cross_section=port.deembed_cross_section,
                    )
                )
            elif isinstance(port, WaveguideToSimPort):
                towards = port.towards
                if port.towards is None:
                    towards = f"{port.refpoint}_corner"
                self.produce_waveguide_to_port(
                    refp[port.refpoint],
                    refp[towards],
                    (port_i := port_i + 1),
                    side=port.side,
                    a=port.a,
                    b=port.b,
                    term1=port.term1,
                    turn_radius=port.turn_radius,
                    use_internal_ports=port.use_internal_ports,
                    waveguide_length=port.waveguide_length,
                    face=port.face,
                    airbridge=port.airbridge,
                    deembed_cross_section=port.deembed_cross_section,
                )

            elif isinstance(port, JunctionSimPort):
                if self.separate_island_internal_ports:
                    self.ports.append(InternalPort((port_i := port_i + 1), refp[port.refpoint], face=port.face))
                    self.ports.append(InternalPort((port_i := port_i + 1), refp[port.other_refpoint], face=port.face))
                else:  # Junction between the islands
                    self.ports.append(
                        InternalPort(
                            (port_i := port_i + 1),
                            *self.etched_line(refp[port.refpoint], refp[port.other_refpoint]),
                            face=port.face,
                            inductance=self.junction_inductance,
                            capacitance=self.junction_capacitance,
                            junction=True,
                            floating=port.floating,
                        )
                    )

    return _build_for_element_class


def get_single_element_sim_class(
    element_class: Element,
    ignore_ports: list[str] | None = None,
    transformation_from_center: Callable[[pya.Cell], pya.DTrans] | None = None,
    partition_region_function: Callable[[Simulation], list[PartitionRegion]] | None = None,
    sim_junction_type: str = "Sim",
    deembed_cross_sections: dict[str] = None,
) -> type[Simulation]:
    """Formulates a simulation class containing a single cell of a given Element class

    Args:
        element_class: an Element class for which a simulation class is returned
        ignore_ports: If list of strings is given, simulation ports will not be created for the given
            refpoints in the simulation class.
        transformation_from_center: If None, simulated element is placed in the middle of simulation's box.
            Otherwise should be a function that takes an element cell as argument and returns a DTrans object.
            The returned transformation is applied to the element cell
            after placing it in the middle of simulation's box.
            The function should not cause any side-effects, i.e. change the cell parameters
        partition_region_function: optional. Function that the simulation instance will use to define
            partition regions, which may look up instances parameters and refpoints to derive the regions.
        deembed_cross_sections: optional dictionary for cross-section simulation that can be used for deembeding.
            The naming convention in the dictionary is `deembed_cross_sections[port_refpoint]=cross_section_name`,
            where `cross_section_name` is the name given to the correction cuts. For example, see
            `simulation.epr.smooth_capacitor.py`, deembed_cross_sections['port_a']='port_amer'.
    """
    overriden_class_attributes = {
        "separate_island_internal_ports": Param(
            pdt.TypeBoolean,
            "Add InternalPorts on both islands (if applicable). Use for capacitive simulations",
            False,
        ),
        "junction_inductance": Param(pdt.TypeList, "Junction inductance (if junction exists)", 11.497e-9, unit="H"),
        "junction_capacitance": Param(pdt.TypeList, "Junction capacitance (if junction exists)", 0.1e-15, unit="F"),
        "build": _get_build_function(
            element_class, ignore_ports, transformation_from_center, sim_junction_type, deembed_cross_sections
        ),
    }
    if partition_region_function:
        overriden_class_attributes["get_partition_regions"] = partition_region_function
    element_sim_class = type(
        f"SingleElementSimulationClassFor{element_class.__name__}",
        (Simulation,),
        overriden_class_attributes,
    )
    add_parameters_from(element_class)(element_sim_class)
    return element_sim_class
