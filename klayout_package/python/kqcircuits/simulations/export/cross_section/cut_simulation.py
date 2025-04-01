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
import ast
import logging
from math import ceil
from typing import Any

from klayout import pya
from kqcircuits.simulations.cross_section_simulation import CrossSectionSimulation
from kqcircuits.simulations.simulation import Simulation
from kqcircuits.util.parameters import Param, pdt, add_parameters_from


@add_parameters_from(Simulation, "tls_layer_thickness", "tls_layer_material")
class CutSimulation(CrossSectionSimulation):
    """Class for cross-section simulations with geometry generated from a 3D Simulation.

    By default, renames the layers such that partition regions of source simulation are basically ignored.
    The ``region_map`` can be used to define new partition regions or copy partition regions from source simulation.

    Adds interface layers 'ma', 'ms', and 'sa' if ``tls_layer_thickness`` and ``tls_layer_material`` are set properly.
    """

    source_sim = Param(pdt.TypeNone, "Instance of Simulation subclass from which the cross section is generated", None)
    cut_start = Param(pdt.TypeShape, "Start point of the cut segment", pya.DPoint(0, 0))
    cut_end = Param(pdt.TypeShape, "End point of the cut segment", pya.DPoint(100, 0))
    cut_bottom = Param(pdt.TypeDouble, "Bottom of the cross section", -1e30, unit="µm")
    cut_top = Param(pdt.TypeDouble, "Top of the cross section", 1e30, unit="µm")
    region_map = Param(
        pdt.TypeString,
        "Dictionary with new partition region suffixes as keys and region definitions as values",
        "{}",
        docstring="The region definition is a list of pya.DBox or string instances. Use string instance to copy "
        "partition region from the source simulation.",
    )
    metal_height = Param(pdt.TypeDouble, "Thickness of metal layer if sheet in the source simulation.", 0.2, unit="µm")

    def build(self):
        self.insert_cross_section_layers()
        partition_regions = self.get_partition_regions()
        self.process_geometry()
        self.apply_partition_regions(partition_regions)

    def process_geometry(self):
        self.regroup_layers()
        self.insert_tls_layers()

    def limited_region(self, box: pya.DBox):
        bottom = max(box.bottom, self.cut_bottom)
        top = min(box.top, self.cut_top)
        if bottom >= top:
            return pya.Region()
        return pya.Region(pya.DBox(box.left, bottom, box.right, top).to_itype(self.layout.dbu))

    def insert_cross_section_layers(self):
        """Insert cross sections from each layer of ``self.source_sim`` into ``self.layers``.
        Thicken sheet metals by ``self.metal_height``.
        """
        layout = self.source_sim.layout
        cut_edge = pya.DEdge(self.cut_start, self.cut_end).to_itype(layout.dbu)
        cut_vector = cut_edge.d()

        # Place constants related to non-orthogonal edges warning
        appr_edge_slope_tolerance = 0.2  # warning is given if edge slope compared to orthogonal exceeds appr. this
        database_unit_tolerance = 2  # the database unit tolerance

        # Compute variables related to non-orthogonal edges warning
        cut_region_width = ceil(0.5 * database_unit_tolerance / appr_edge_slope_tolerance) * 2
        max_cut_vector_sprod = cut_region_width * appr_edge_slope_tolerance * cut_vector.abs()

        # Simple path region for cut with small width. Use KLayout's boolean operators to detect the intersections.
        cut_region = pya.Region(pya.Path([cut_edge.p1, cut_edge.p2], cut_region_width))

        # Scale intersection dot products within confines of the cut
        crossing_edges = [e for s in cut_region.each() for e in s.each_edge() if cut_edge.crossed_by(e)]
        prods = [cut_vector.sprod(cut_edge.crossing_point(e)) for e in crossing_edges]
        cut_min = min(prods)
        cut_length = (self.cut_end - self.cut_start).abs()
        cut_scale = cut_length / (max(prods) - cut_min)

        regions = {}
        sheet_metals = {}
        for name, data in self.source_sim.layers.items():
            if "layer" not in data:
                segments = [(0.0, cut_length)]
            else:
                layer_region = pya.Region(self.source_sim.cell.begin_shapes_rec(layout.layer(data["layer"], 0)))
                intersection = (cut_region & layer_region).merged()
                segments = []
                for polygon in intersection.each():
                    crossing_edges = [e for e in polygon.each_edge() if cut_edge.crossed_by(e)]

                    # Warn if cross-section is taken with non-orthogonal edges
                    skew_edges = [e for e in crossing_edges if abs(cut_vector.sprod(e.d())) > max_cut_vector_sprod]
                    for skew_edge in skew_edges:
                        logging.warning(
                            f"Cross section is taken with non-orthogonal edge from simulation '{self.source_sim.name}' "
                            f"layer '{name}' at location ({cut_edge.crossing_point(skew_edge).to_dtype(layout.dbu)})."
                        )

                    # Calculate intersection as value between 0 and cut length
                    dists = [
                        (cut_vector.sprod(cut_edge.crossing_point(e)) - cut_min) * cut_scale for e in crossing_edges
                    ]
                    segments.append((min(dists), max(dists)))

            if not segments:
                continue

            # Add sheet metal cross sections to sheet_metals dictionary (to insert them later)
            if data["thickness"] == 0 and "excitation" in data:
                edges = [pya.DEdge(left, data["z"], right, data["z"]) for left, right in segments]
                sheet_metals[name] = {
                    "edges": pya.Edges([e.to_itype(self.layout.dbu) for e in edges]),
                    "material": data["material"],
                    "excitation": data["excitation"],
                }
                continue

            # Build region out of segments
            bottom, top = data["z"], data["z"] + data["thickness"]
            regions[name] = pya.Region()
            for left, right in segments:
                regions[name] += self.limited_region(pya.DBox(left, bottom, right, top))

            # Apply subtractions defined by layers
            for subtract in data.get("subtract", []):
                if subtract in regions:
                    regions[name] -= regions[subtract]

            # Insert layer that has material and non-empty region
            if data.get("material") is not None:
                excitation = {"excitation": data["excitation"]} if "excitation" in data else {}
                self.insert_layer(name, regions[name], data["material"], **excitation)

        self.insert_sheet_metals(sheet_metals)

    def insert_sheet_metals(self, sheet_metals: dict[str, dict[str, Any]]):
        """Inserts sheet metal layers thickened by ``self.metal_height`` on vacuum side."""
        if self.metal_height <= 0.0:
            return

        vacuum_regions = [d["region"] for d in self.layers.values() if d.get("material") == "vacuum"]
        for name, data in sheet_metals.items():
            extended_region = data["edges"].extents(0, round(self.metal_height / self.layout.dbu))
            region = pya.Region()
            for vacuum_region in vacuum_regions:
                region += extended_region & vacuum_region
                vacuum_region -= extended_region

            data = self.source_sim.layers[name]
            self.insert_layer(name, region, **{k: v for k, v in data.items() if k != "edges"})

    def get_partition_regions(self) -> dict[str, pya.Region]:
        """Return partition regions defined by ``self.region_map``.

        Returns:
             dictionary containing the layer name suffixes as keys and regions as values.
        """
        region_map = ast.literal_eval(self.region_map) if isinstance(self.region_map, str) else self.region_map
        regions = {}
        for part, definitions in region_map.items():
            regions[part] = pya.Region()

            for definition in definitions:
                if isinstance(definition, pya.DBox):
                    regions[part] += self.limited_region(definition)
                elif isinstance(definition, str):
                    for name, data in self.layers.items():
                        if name.endswith(definition):
                            regions[part] += data["region"].extents()  # add bboxes of each polygon of data["region"]
                            # The above could be relaxed to regions[part] += data["region"] if ma_layer was extended
                            # from metal to vacuum and not the opposite.
                else:
                    logging.warning(f"The region_map term {definition} is ignored due to unsupported type.")

            regions[part].merge()
        return regions

    def apply_partition_regions(self, regions: dict[str, pya.Region]):
        """Partition every non-metal layer into regions.

        Args:
            regions: dictionary containing the layer name suffixes as keys and regions as values.
        """
        for name, data in list(self.layers.items()):
            if "excitation" in data:
                continue
            for part, region in regions.items():
                self.insert_layer(f"{name}{part}", **{**data, "region": region & data["region"]})
                data["region"] -= region

    def regroup_layers(self):
        """Group and rename layers such that a layer name doesn't start other layer name.

        For example, if there are two source layers 'vacuum', 'vacuum_part', then both are merged into 'vacuum' layer.
        """
        old_layers = self.layers.copy()
        self.layers.clear()
        base_names = [n for n in old_layers if not any(n.startswith(k) for k in old_layers if n != k)]

        for name, data in old_layers.items():
            base_name = next(n for n in base_names if name.startswith(n))
            if base_name in self.layers:
                self.layers[base_name]["region"] += data["region"]
                base_wo_region = {k: v for k, v in self.layers[base_name].items() if k != "region"}
                data_wo_region = {k: v for k, v in data.items() if k != "region"}
                if base_wo_region != data_wo_region:
                    raise ValueError(f"Inconsistent layer data for '{base_name}'.")
            else:
                self.insert_layer(base_name, **data)

    def insert_tls_layers(self):
        """Insert TLS interface layers into the model."""
        metals, vacuums, substrates = self.get_metals_vacuums_substrates()
        names = ["ma_layer", "ms_layer", "sa_layer"]
        sources = [vacuums, metals, vacuums]
        targets = [metals, substrates, substrates]
        interfaces = [self.sum_region(s).edges() & self.sum_region(t).edges() for s, t in zip(sources, targets)]
        thickness = [float(Simulation.ith_value(self.tls_layer_thickness, i)) for i in range(3)]
        material = [Simulation.ith_value(self.tls_layer_material, i) for i in range(3)]

        for i in range(3):
            extension = round(thickness[i] / self.layout.dbu)
            region = interfaces[i].extended(0, 0, extension, 0, True) & self.sum_region(targets[i])
            self.insert_layer(names[i], region, material[i])
            self.subtract_region(targets[i], region)

    def get_metals_vacuums_substrates(self) -> tuple[list[str], list[str], list[str]]:
        """Return layer names for metals, vacuums, and substrates."""
        metals = [n for n, d in self.layers.items() if "excitation" in d]
        vacuums = [n for n, d in self.layers.items() if d.get("material") == "vacuum"]
        substrates = [n for n in self.layers if n not in metals + vacuums]
        return metals, vacuums, substrates

    def sum_region(self, layers):
        """Return union of regions of given layers."""
        region = pya.Region()
        for layer in layers:
            region += self.layers[layer]["region"]
        return region

    def subtract_region(self, layers, region):
        """Subtract region from given layers."""
        for layer in layers:
            self.layers[layer]["region"] -= region

    def get_material_dict(self):
        """Override CrossSectionSimulation method to combine source simulation and self materials"""
        return {**self.source_sim.get_material_dict(), **super().get_material_dict()}

    def get_parameters(self):
        """Override CrossSectionSimulation method to combine source simulation and self parameters"""
        return {
            **super().get_parameters(),
            "source_sim": self.source_sim.__class__.__name__,
            **{f"source_{k}": v for k, v in self.source_sim.get_parameters().items()},
        }
