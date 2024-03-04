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


def format_position(x, units):
    if isinstance(x, list):
        return [format_position(p, units) for p in x]
    elif isinstance(x, str):
        return x
    else:
        return str(x) + units


def create_rectangle(oEditor, name, x, y, z, w, h, axis, units):
    if w != 0.0 and h != 0.0:
        oEditor.CreateRectangle(
            [
                "NAME:RectangleParameters",
                "IsCovered:=",
                True,
                "XStart:=",
                format_position(x, units),
                "YStart:=",
                format_position(y, units),
                "ZStart:=",
                format_position(z, units),
                "Width:=",
                format_position(w, units),
                "Height:=",
                format_position(h, units),
                "WhichAxis:=",
                axis,
            ],
            ["NAME:Attributes", "Name:=", name, "PartCoordinateSystem:=", "Global"],
        )


def create_polygon(oEditor, name, points, units):
    oEditor.CreatePolyline(
        [
            "NAME:PolylineParameters",
            "IsPolylineCovered:=",
            True,
            "IsPolylineClosed:=",
            True,
            ["NAME:PolylinePoints"]
            + [
                [
                    "NAME:PLPoint",
                    "X:=",
                    format_position(p[0], units),
                    "Y:=",
                    format_position(p[1], units),
                    "Z:=",
                    format_position(p[2], units),
                ]
                for p in points + [points[0]]
            ],
            ["NAME:PolylineSegments"]
            + [
                ["NAME:PLSegment", "SegmentType:=", "Line", "StartIndex:=", i, "NoOfPoints:=", 2]
                for i in range(len(points))
            ],
            [
                "NAME:PolylineXSection",
                "XSectionType:=",
                "None",
                "XSectionOrient:=",
                "Auto",
                "XSectionWidth:=",
                "0" + units,
                "XSectionTopWidth:=",
                "0" + units,
                "XSectionHeight:=",
                "0" + units,
                "XSectionNumSegments:=",
                "0",
                "XSectionBendType:=",
                "Corner",
            ],
        ],
        ["NAME:Attributes", "Name:=", name, "Flags:=", "", "PartCoordinateSystem:=", "Global"],
    )


def create_box(oEditor, name, x, y, z, sx, sy, sz, units):
    if sx != 0.0 and sy != 0.0 and sz != 0.0:
        oEditor.CreateBox(
            [
                "NAME:BoxParameters",
                "XPosition:=",
                format_position(x, units),
                "YPosition:=",
                format_position(y, units),
                "ZPosition:=",
                format_position(z, units),
                "XSize:=",
                format_position(sx, units),
                "YSize:=",
                format_position(sy, units),
                "ZSize:=",
                format_position(sz, units),
            ],
            [
                "NAME:Attributes",
                "Name:=",
                name,
                "MaterialValue:=",
                '""',
                "Flags:=",
                "",
                "PartCoordinateSystem:=",
                "Global",
            ],
        )


def thicken_sheet(oEditor, objects, thickness, units):
    """Thickens sheet to solid with given thickness and material"""
    if objects and thickness != 0.0:
        oEditor.SweepAlongVector(
            ["NAME:Selections", "Selections:=", ",".join(objects), "NewPartsModelFlag:=", "Model"],
            [
                "NAME:VectorSweepParameters",
                "DraftAngle:=",
                "0deg",
                "DraftType:=",
                "Round",
                "CheckFaceFaceIntersection:=",
                False,
                "SweepVectorX:=",
                "0um",
                "SweepVectorY:=",
                "0um",
                "SweepVectorZ:=",
                "{} {}".format(thickness, units),
            ],
        )


def set_material(oEditor, objects, material=None, solve_inside=None):
    if objects:
        if solve_inside is not None:
            oEditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Geometry3DAttributeTab",
                        ["NAME:PropServers"] + objects,
                        ["NAME:ChangedProps", ["NAME:Solve Inside", "Value:=", solve_inside]],
                    ],
                ]
            )
        if material is not None:
            oEditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Geometry3DAttributeTab",
                        ["NAME:PropServers"] + objects,
                        ["NAME:ChangedProps", ["NAME:Material", "Value:=", '"{}"'.format(material)]],
                    ],
                ]
            )
        else:
            oEditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Geometry3DAttributeTab",
                        ["NAME:PropServers"] + objects,
                        ["NAME:ChangedProps", ["NAME:Model", "Value:=", False]],
                    ],
                ]
            )


def add_layer(layer_map, order_map, layer_num, dest_layer, order, layer_type="signal"):
    """Appends layer data to layer_map and order_map."""
    layer_map.append(
        ["NAME:LayerMapInfo", "LayerNum:=", layer_num, "DestLayer:=", dest_layer, "layer_type:=", layer_type]
    )
    order_map += ["entry:=", ["order:=", order, "layer:=", dest_layer]]


def move_vertically(oEditor, objects, z_shift, units):
    """Moves objects in z-direction by z_shift."""
    if objects and z_shift != 0.0:
        oEditor.Move(
            ["NAME:Selections", "Selections:=", ",".join(objects), "NewPartsModelFlag:=", "Model"],
            [
                "NAME:TranslateParameters",
                "TranslateVectorX:=",
                "0 {}".format(units),
                "TranslateVectorY:=",
                "0 {}".format(units),
                "TranslateVectorZ:=",
                "{} {}".format(z_shift, units),
            ],
        )


def copy_paste(oEditor, objects):
    """Duplicates objects and returns new object names."""
    if objects:
        oEditor.Copy(["NAME:Selections", "Selections:=", ",".join(objects)])
        return oEditor.Paste()
    else:
        return []


def delete(oEditor, objects):
    """Delete given objects"""
    if objects:
        oEditor.Delete(["NAME:Selections", "Selections:=", ",".join(objects)])


def subtract(oEditor, objects, tool_objects, keep_originals=False):
    """Subtract tool_objects from objects."""
    if objects and tool_objects:
        oEditor.Subtract(
            ["NAME:Selections", "Blank Parts:=", ",".join(objects), "Tool Parts:=", ",".join(tool_objects)],
            ["NAME:SubtractParameters", "KeepOriginals:=", keep_originals, "TurnOnNBodyBoolean:=", True],
        )


def unite(oEditor, objects, keep_originals=False):
    """Unite objects into the first object."""
    if len(objects) > 1:
        oEditor.Unite(
            ["NAME:Selections", "Selections:=", ",".join(objects)],
            ["NAME:UniteParameters", "KeepOriginals:=", keep_originals, "TurnOnNBodyBoolean:=", True],
        )


def objects_from_sheet_edges(oEditor, objects, thickness, units):
    """Creates boundary objects for each sheet and returns object names in list."""
    edges = []
    for o in objects:
        boundary_ids = [int(i) for i in oEditor.GetEdgeIDsFromObject(o)]
        edge_list = oEditor.CreateObjectFromEdges(
            ["NAME:Selections", "Selections:=", o, "NewPartsModelFlag:=", "Model"],
            ["NAME:Parameters", ["NAME:BodyFromEdgeToParameters", "Edges:=", boundary_ids]],
            ["CreateGroupsForNewObjects:=", False],
        )
        thicken_sheet(oEditor, edge_list, thickness, units)
        unite(oEditor, edge_list, False)
        edges.append(edge_list[0])
    return edges


def add_material(oDefinitionManager, name, **parameters):
    """Adds material with given name and parameters."""
    param_list = [
        "NAME:" + name,
        "CoordinateSystemType:=",
        "Cartesian",
        "BulkOrSurfaceType:=",
        1,
        ["NAME:PhysicsTypes", "set:=", ["Electromagnetic"]],
    ]
    for key, value in parameters.items():
        param_list += ["{}:=".format(key), str(value)]
    oDefinitionManager.AddMaterial(param_list)


def set_color(oEditor, objects, red, green, blue, transparency):
    """Sets color and transparency for given objects."""
    if objects:
        oEditor.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:Geometry3DAttributeTab",
                    ["NAME:PropServers"] + objects,
                    [
                        "NAME:ChangedProps",
                        ["NAME:Color", "R:=", red, "G:=", green, "B:=", blue],
                        ["NAME:Transparent", "Value:=", transparency],
                    ],
                ],
            ]
        )
