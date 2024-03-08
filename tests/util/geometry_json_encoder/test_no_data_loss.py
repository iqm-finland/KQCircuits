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


import json
import pytest
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_json_encoder import (
    GeometryJsonEncoder,
    GeometryJsonDecoder,
    encode_python_obj_as_dict,
    decode_dict_as_python_obj,
)


@pytest.mark.parametrize(
    "parameters",
    [
        pya.DPoint(-1000, 5.67),
        pya.DVector(1000, -5.67),
        pya.DBox(-1000, 5.67, 0, 1234.56),
        pya.LayerInfo(1001, 2),
        pya.DPath([pya.DPoint(1.2, 3), pya.DPoint(-3.4, 5), pya.DPoint(6, -7.8), pya.DPoint(-1000, 1000)], 13),
        pya.DEdge(1000, -5.67, 0, -1234.56),
        pya.DPolygon([pya.DPoint(-1.2, -3), pya.DPoint(3.4, -5), pya.DPoint(-6, 7.8), pya.DPoint(1000, -1000)]),
        pya.DPolygon(pya.DBox(-100, -100, 100, 100)).insert_hole(pya.DBox(-50, -50, 50, 50)),
        pya.DPolygon(pya.DBox(-100, -100, 100, 100))
        .insert_hole(pya.DBox(-50, -50, -10, -10))
        .insert_hole(pya.DBox(10, 10, 50, 50)),
    ],
    ids=["DPoint", "DVector", "DBox", "LayerInfo", "DPath", "DEdge", "DPolygon", "DPolygonOneHole", "DPolygonTwoHoles"],
)
def test_no_data_loss(parameters):
    assert parameters == json.loads(
        json.dumps(parameters, cls=GeometryJsonEncoder), cls=GeometryJsonDecoder
    ), "Original instance not equal to encoded then decoded instance"
    assert parameters == decode_dict_as_python_obj(
        encode_python_obj_as_dict(parameters)
    ), "Original instance not equal to encoded then decoded instance"
