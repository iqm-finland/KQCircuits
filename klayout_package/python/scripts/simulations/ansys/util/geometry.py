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
    oEditor.CreateRectangle(
        ["NAME:RectangleParameters",
         "IsCovered:=", True,
         "XStart:=", format_position(x, units),
         "YStart:=", format_position(y, units),
         "ZStart:=", format_position(z, units),
         "Width:=", format_position(w, units),
         "Height:=", format_position(h, units),
         "WhichAxis:=", axis
         ],
        ["NAME:Attributes",
         "Name:=", name,
         "Flags:=", "",
         "Color:=", "(143 175 143)",
         "Transparency:=", 0,
         "PartCoordinateSystem:=", "Global",
         "UDMId:=", "",
         "MaterialValue:=", "\"vacuum\"",
         "SurfaceMaterialValue:=", "\"\"",
         "SolveInside:=", True,
         "IsMaterialEditable:=", True,
         "UseMaterialAppearance:=", False,
         "IsLightweight:=", False
         ])


def create_polygon(oEditor, name, points, units):
    oEditor.CreatePolyline(
        ["NAME:PolylineParameters",
         "IsPolylineCovered:=", True,
         "IsPolylineClosed:=", True,
         ["NAME:PolylinePoints"]
         + [["NAME:PLPoint",
             "X:=", format_position(p[0], units),
             "Y:=", format_position(p[1], units),
             "Z:=", format_position(p[2], units)]
            for p in points + [points[0]]
            ],
         ["NAME:PolylineSegments"]
         + [["NAME:PLSegment",
             "SegmentType:=", "Line",
             "StartIndex:=", i,
             "NoOfPoints:=", 2]
            for i in range(len(points))
            ],
         ["NAME:PolylineXSection",
          "XSectionType:=", "None",
          "XSectionOrient:=", "Auto",
          "XSectionWidth:=", "0" + units,
          "XSectionTopWidth:=", "0" + units,
          "XSectionHeight:=", "0" + units,
          "XSectionNumSegments:=", "0",
          "XSectionBendType:=", "Corner"
          ]
         ],
        ["NAME:Attributes",
         "Name:=", name,
         "Flags:=", "",
         "Color:=", "(143 175 143)",
         "Transparency:=", 0,
         "PartCoordinateSystem:=", "Global",
         "UDMId:=", "",
         "MaterialValue:=", "\"vacuum\"",
         "SurfaceMaterialValue:=", "\"\"",
         "SolveInside:=", True,
         "IsMaterialEditable:=", True,
         "UseMaterialAppearance:=", False,
         "IsLightweight:=", False
         ])


def create_box(oEditor, name, x, y, z, sx, sy, sz, material, units):
    oEditor.CreateBox(
        ["NAME:BoxParameters",
         "XPosition:=", format_position(x, units),
         "YPosition:=", format_position(y, units),
         "ZPosition:=", format_position(z, units),
         "XSize:=", format_position(sx, units),
         "YSize:=", format_position(sy, units),
         "ZSize:=", format_position(sz, units)
         ],
        ["NAME:Attributes",
         "Name:=", name,
         "Flags:=", "",
         "Color:=", "(143 175 143)",
         "Transparency:=", 0.6,
         "PartCoordinateSystem:=", "Global",
         "UDMId:=", "",
         "MaterialValue:=", "\"%s\"" % material,
         "SurfaceMaterialValue:=", "\"\"",
         "SolveInside:=", True,
         "IsMaterialEditable:=", True,
         "UseMaterialAppearance:=", False,
         "IsLightweight:=", False
         ])
