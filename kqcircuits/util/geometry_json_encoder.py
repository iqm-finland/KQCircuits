# This code is part of KQCirquits
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


import json
from kqcircuits.pya_resolver import pya


class GeometryJsonEncoder(json.JSONEncoder):
    """JSON encoder that converts several pya D* types into nested lists."""
    def default(self, obj):
        if isinstance(obj, pya.DPoint) or isinstance(obj, pya.DVector):
            return [obj.x, obj.y]
        if isinstance(obj, pya.DBox):
            return [[obj.p1.x, obj.p1.y], [obj.p2.x, obj.p2.y]]
        if isinstance(obj, pya.LayerInfo):
            return obj.layer
        if isinstance(obj, pya.DPath):
            return [(p.x, p.y) for p in obj.each_point()]

        # Use the default JSON encoder for any other types
        return json.JSONEncoder.default(self, obj)
