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


import numpy

from kqcircuits.pya_resolver import pya


def make_grid(boundbox, avoid_region, grid_step=10, grid_size=5, group_n=10):
    """Generates ground grid covering `boundbox` with holes not overlapping with the `avoid_region`.

    Args:
        boundbox: bounding box of grid in database unit
        avoid_region: area on which grid is avoided
        grid_step: step between consecutive holes in database unit
        grid_size: hole edge length in database unit
        group_n: number of adjacent holes in a group (is used to speed up grid generation)

    Returns:
        grid region
  """
    def grid_region(box, step, size):
        square = pya.Box(0, 0, size, size)
        x_region = pya.Region()
        for x in numpy.arange(box.p1.x, box.p2.x, step):
            x_region.insert(square.transformed(pya.Trans(pya.Vector(x, 0))))
        xy_region = pya.Region()
        for y in numpy.arange(box.p1.y, box.p2.y, step):
            xy_region.insert(x_region.transformed(pya.Trans(pya.Vector(0, y))))
        return xy_region

    # Create box grid, where each box can include group_n x group_n holes.
    box_step = group_n * grid_step
    box_size = box_step - grid_step + grid_size
    boxes_region = grid_region(boundbox, box_step, box_size)
    # Filter boxes that do not overlap with avoid_region. These will be used to speed up filtering of holes.
    masked_boxes_region = ((boxes_region & pya.Region(boundbox)) - avoid_region).with_area(box_size**2, None, False)

    # Create grid of holes and duplicate it on boxes that overlap with avoid_region.
    holes_region = grid_region(pya.Box(0, 0, box_step, box_step), grid_step, grid_size)
    overlap_region = pya.Region()
    for poly in (boxes_region - masked_boxes_region).each():
        overlap_region.insert(holes_region.transformed(pya.Trans(pya.Vector(poly.bbox().p1))))

    # Create grid of holes that do not overlap with avoid region.
    masked_holes_region = ((overlap_region & pya.Region(boundbox)) - avoid_region).with_area(grid_size**2, None, False)
    for poly in masked_boxes_region.each():
        masked_holes_region.insert(holes_region.transformed(pya.Trans(pya.Vector(poly.bbox().p1))))

    return masked_holes_region
