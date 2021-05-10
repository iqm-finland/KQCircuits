# Copyright (c) 2019-2021 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

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
