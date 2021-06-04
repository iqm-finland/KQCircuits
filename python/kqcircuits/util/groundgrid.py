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


def make_grid(boundbox, avoid_region, grid_step=10, grid_size=5):
    """Generates the ground grid.

  Returns a `Region` covering `boundbox` with `Box`es not overlapping with
  the avoid `Region`.

  All arguments are in database unit, not in micrometers!

  """

    grid_region = pya.Region()
    for y in numpy.arange(boundbox.p1.y, boundbox.p2.y, grid_step):
        for x in numpy.arange(boundbox.p1.x, boundbox.p2.x, grid_step):
            hole = pya.Box(x, y, x + grid_size, y + grid_size)
            grid_region.insert(hole)
    grid_masked_region = (grid_region - avoid_region).with_area(grid_size ** 2, None, False)

    return grid_masked_region
