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
import logging
from os import cpu_count
from time import perf_counter

from kqcircuits.pya_resolver import pya


class AreaReceiver(pya.TileOutputReceiver):
    """ Class for handling and storing output from :class:`TilingProcessor` """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.area = 0.0

    def put(self, ix, iy, tile, obj, dbu, clip):
        """ Function called by :class:`TilingProcessor` on output """
        #pylint: disable=unused-argument
        logging.debug(f"Area for tile {ix},{iy}: {obj} ({dbu})")
        self.area = obj * (dbu * dbu)  # report as um^2


def get_area_and_density(cell: pya.Cell, layer_infos=None):
    """ Get total area and density :math:`\\rho=\\frac{area}{bbox.area}` of all layers.

    Args:
        cell: target cell to get area from
        layer_infos: list of ``LayerInfo`` to get area for, or None to get area for all layers.

    Returns:
        tuple: tuple containing lists of

          * layer names as str
          * total area as float
          * density between 0 and 1 as float

    """
    start_time = perf_counter()
    layout = cell.layout()

    tp = pya.TilingProcessor()
    tp.threads = cpu_count()
    tp.tile_size = (2000, 2000)  # microns
    if layer_infos is None:
        layer_infos = list(layout.layer_infos())
    layer_areas = [AreaReceiver() for _ in layer_infos]
    layer_bboxes = [AreaReceiver() for _ in layer_infos]

    for layer_info, area_receiver, bbox_receiver in zip(layer_infos, layer_areas, layer_bboxes):
        name = f"_{layer_info.name}"  # if `name` starts with a number, tp.execute() fails, so we add an underscore
        area, bbox = name + '_area', name + '_bbox'
        tp.input(name, cell.begin_shapes_rec(layout.layer(layer_info)))
        tp.output(area, area_receiver)
        tp.output(bbox, bbox_receiver)
        tp.queue(f"_output({area}, {name}.area)")
        tp.queue(f"_output({bbox}, {name}.bbox.area)")
    tp.execute("Calculate polygon and bounding box area")

    areas = [area.area for area in layer_areas]
    bboxes = [bbox.area for bbox in layer_bboxes]
    layer_names = [layer_info.name for layer_info in layer_infos]
    densities = [area / bbox if bbox != 0.0 else 0.0 for area, bbox in zip(areas, bboxes)]
    if len(areas) > 0:
        logging.info(f'For cell {cell.name} got layer areas: {areas}')
        logging.info(f'Area calculation took {perf_counter() - start_time:.1f} seconds')

    return layer_names, areas, densities
