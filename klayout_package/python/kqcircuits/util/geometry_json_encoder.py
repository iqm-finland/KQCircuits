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

import json

from kqcircuits.pya_resolver import pya


class GeometryJsonEncoder(json.JSONEncoder):
    """JSON encoder that converts several pya D* types into JSON objects."""
    def default(self, o):
        if isinstance(o, pya.DPoint):
            return {"_pya_type": "DPoint", "x": o.x, "y": o.y}
        if isinstance(o, pya.DVector):
            return {"_pya_type": "DVector", "x": o.x, "y": o.y}
        if isinstance(o, pya.DBox):
            return {
                "_pya_type": "DBox",
                "p1": self.default(o.p1),
                "p2": self.default(o.p2)
            }
        if isinstance(o, pya.LayerInfo):
            return {"_pya_type": "LayerInfo", "layer": o.layer, "datatype": o.datatype}
        if isinstance(o, pya.DPath):
            return {
                "_pya_type": "DPath",
                "points": [self.default(p) for p in o.each_point()],
                "width": o.width
            }
        if isinstance(o, pya.DEdge):
            return {
                "_pya_type": "DEdge",
                "p1": self.default(o.p1),
                "p2": self.default(o.p2)
            }
        if isinstance(o, pya.DPolygon):
            return {
                "_pya_type": "DPolygon",
                "hull": [self.default(p) for p in o.each_point_hull()],
                "holes": [[self.default(p) for p in o.each_point_hole(i)] for i in range(o.holes())]
            }
        # Defer to standard json encoder for other cases
        return json.JSONEncoder.default(self, o)

class GeometryJsonDecoder(json.JSONDecoder):
    """JSON decoder that converts JSON objects into pya D* type objects."""
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=GeometryJsonDecoder._decode_geometry, *args, **kwargs)

    @staticmethod
    def _decode_geometry(js):
        if "_pya_type" not in js:
            return js
        if js["_pya_type"] == "DPoint":
            return pya.DPoint(js["x"], js["y"])
        if js["_pya_type"] == "DVector":
            return pya.DVector(js["x"], js["y"])
        if js["_pya_type"] == "DBox":
            return pya.DBox(js["p1"], js["p2"])
        if js["_pya_type"] == "LayerInfo":
            return pya.LayerInfo(js["layer"], js["datatype"])
        if js["_pya_type"] == "DPath":
            return pya.DPath(js["points"], js["width"])
        if js["_pya_type"] == "DEdge":
            return pya.DEdge(js["p1"], js["p2"])
        if js["_pya_type"] == "DPolygon":
            polygon = pya.DPolygon(js["hull"])
            for hole in js["holes"]:
                polygon.insert_hole(hole)
            return polygon
        raise json.JSONDecodeError(f"_pya_type '{js['_pya_type']}' not currently deserializable: {js}", js, 0)

def encode_python_obj_as_dict(o):
    """Encodes a Python object into a JSON parseable dict

    Args:
        o - Python object
    """
    return json.loads(GeometryJsonEncoder().encode(o))

def decode_dict_as_python_obj(o):
    """Decodes a JSON parseable dict into a Python object

    Args:
        o - JSON parseable dict
    """
    return GeometryJsonDecoder().decode(json.dumps(o))
