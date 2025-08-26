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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).
import logging
from os import cpu_count
from time import perf_counter

from kqcircuits.pya_resolver import pya
from kqcircuits.defaults import default_faces


class AreaReceiver(pya.TileOutputReceiver):
    """Class for handling and storing output from :class:`TilingProcessor`"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.area = 0.0

    def put(self, ix, iy, tile, obj, dbu, clip):
        """Function called by :class:`TilingProcessor` on output"""
        # pylint: disable=unused-argument
        logging.debug(f"Area for tile {ix},{iy}: {obj} ({dbu})")
        self.area = obj * (dbu * dbu)  # report as um^2


def get_area_and_density(cell: pya.Cell, layer_infos=None, optimize_ground_grid_calculations=True):
    """Get total area and density :math:`\\rho=\\frac{area}{bbox.area}` of all layers.

    This calculation is slow for geometries with many polygons, and in practice the layers containing ground grid
    take the majority of time. When ``optimize_ground_grid_calculations`` is set to ``True``, the ``ground_grid``
    layer area is calculated by assuming all polygons in this layer are identical and don't overlap each other
    (which they should be by definition). Further, the area of ``base_metal_gap`` is calculated by combining the areas
    of ``base_metal_gap_wo_grid`` and ``ground_grid`` areas.

    Args:
        cell: target cell to get area from
        layer_infos: list of ``LayerInfo`` to get area for, or None to get area for all layers.
        optimize_ground_grid_calculations:  ``True`` (default) to optimize ground grid area calculations.

    Returns: dictionary ``{layer_name: {'area': area, 'density': density}}``, where ``area`` is in um^2 and ``density``
       is a fraction < 1.
    """
    start_time = perf_counter()
    layout = cell.layout()

    all_layer_infos = {layer_info.name: layer_info for layer_info in layout.layer_infos()}
    if layer_infos is None:
        layer_infos = all_layer_infos.values()
    layer_infos = set(layer_infos)

    def _grid_area_and_density(layer_info):
        """Calculate the area and density for a layer where all shapes are known to be identical"""
        shapes = list(cell.begin_shapes_rec(layout.layer(layer_info)).each())
        shape_count = len(shapes)
        shape_area = shapes[0].shape().area() if shape_count > 0 else 0
        area = shape_count * float(shape_area)
        bbox_area = cell.bbox_per_layer(layout.layer(layer_info)).area()
        density = area / bbox_area if bbox_area != 0.0 else 0.0
        return area * layout.dbu**2, density

    # Separate out `ground_grid` and `base_metal_gap` layers in `layer_infos` for optimization
    ground_grid_faces = set()
    if optimize_ground_grid_calculations:
        for face, layers in default_faces.items():
            if (
                "ground_grid" in layers
                and "base_metal_gap" in layers
                and "base_metal_gap_wo_grid" in layers
                and (layers["ground_grid"] in layer_infos or layers["base_metal_gap"] in layer_infos)
            ):
                ground_grid_faces.add(face)
        for face in ground_grid_faces:
            ground_grid_layer = default_faces[face]["ground_grid"]
            base_metal_gap_wo_grid_layer = default_faces[face]["base_metal_gap_wo_grid"]
            base_metal_gap_layer = default_faces[face]["base_metal_gap"]

            layer_infos -= {ground_grid_layer, base_metal_gap_layer}  # Skip brute force calculation for these layers
            layer_infos.add(
                base_metal_gap_wo_grid_layer
            )  # Ensure base_metal_gap_wo_grid is included in the calculation

    # Perform tiled area calculation for all other layers
    tp = pya.TilingProcessor()
    tp.threads = cpu_count()
    tp.tile_size = (2000, 2000)  # microns
    layer_areas = [AreaReceiver() for _ in layer_infos]
    layer_bboxes = [AreaReceiver() for _ in layer_infos]
    for layer_info, area_receiver, bbox_receiver in zip(layer_infos, layer_areas, layer_bboxes):
        name = f"_{layer_info.name}"  # if `name` starts with a number, tp.execute() fails, so we add an underscore
        area, bbox = name + "_area", name + "_bbox"
        tp.input(name, cell.begin_shapes_rec(layout.layer(layer_info)))
        tp.output(area, area_receiver)
        tp.output(bbox, bbox_receiver)
        tp.queue(f"_output({area}, {name}.area)")
        tp.queue(f"_output({bbox}, {name}.bbox.area)")
    tp.execute("Calculate polygon and bounding box area")

    areas = [area.area for area in layer_areas]
    bboxes = [bbox.area for bbox in layer_bboxes]
    results = {
        layer_info.name: {"area": area, "density": area / bbox if bbox != 0.0 else 0.0}
        for layer_info, area, bbox in zip(layer_infos, areas, bboxes)
    }

    # Add optimized ground grid calculation results
    for face in ground_grid_faces:
        ground_grid_layer = default_faces[face]["ground_grid"]
        base_metal_gap_wo_grid_layer = default_faces[face]["base_metal_gap_wo_grid"]
        base_metal_gap_layer = default_faces[face]["base_metal_gap"]

        # Calculate ground grid area assuming all shapes in ``ground_grid`` are identical
        ground_grid_area, ground_grid_density = _grid_area_and_density(ground_grid_layer)
        results[ground_grid_layer.name] = {"area": ground_grid_area, "density": ground_grid_density}

        # Calcualte base_metal_gap area assuming the ground grid does not overlap with base_metal_gap_wo_grid
        gap_area = results[base_metal_gap_wo_grid_layer.name]["area"] + ground_grid_area
        gap_bbox = cell.bbox_per_layer(layout.layer(base_metal_gap_layer)).area() * layout.dbu**2
        gap_density = gap_area / gap_bbox if gap_bbox != 0.0 else 0.0
        results[base_metal_gap_layer.name] = {"area": gap_area, "density": gap_density}

    if len(results) > 0:
        logging.info(f"Area calculation took {perf_counter() - start_time:.1f} seconds")

    return results
