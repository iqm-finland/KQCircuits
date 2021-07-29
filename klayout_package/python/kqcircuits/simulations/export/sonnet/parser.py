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
from string import Template


def apply_template(filename_template, filename_output, rules):
    with open(filename_template) as filein:
        src = Template(filein.read())
    results = src.substitute(rules)
    with open(filename_output, "w") as fileout:
        fileout.write(results)
    # dirname_sondata = os.path.join(os.path.dirname(filename_output), "sondata")
    # if not os.path.exists(dirname_sondata):
    #     os.mkdir(dirname_sondata)
    # dirname_project = os.path.join(dirname_sondata, os.path.splitext(os.path.basename(filename_output))[0])
    # if not os.path.exists(dirname_project):
    #     os.mkdir(dirname_project)


def polygon_head(
        nvertices,  # number of vertices of the polygon
        debugid,  # unique number for sonnet internal debugging
        ilevel=0,  # sonnet layer number
        mtype=-1,  # metallization type index, -1 for lossless
        filltype="N",  # N for staircase, T for diagonal, V for conformal
        xmin=1,  # minimum subsection size
        ymin=1,  # minimum subsection size
        xmax=100,  # maximum subsection size
        ymax=100,  # maximum subsection size
        conmax=0,  # maximum length for conformal mesh subsection, 0 for auto
        res=0,  # reserved for sonnet future
        edge_mesh="Y"  # edge mesh on (Y) or off (N)
):
    return f"{ilevel} {nvertices} {mtype} {filltype} {debugid} {xmin} {ymin} {xmax} {ymax} {conmax} {res} {res} " \
           f"{edge_mesh}\n"


def symmetry(sym: bool = False):
    sonnet_str = ""
    if sym:
        sonnet_str = "SYM"
    return sonnet_str


def box(
        xwidth: float = 8000.,
        ywidth: float = 8000.,
        xcells: int = 8000,
        ycells: int = 8000,
        materials_type: str = "Si BT"
):
    xcells2 = 2 * xcells
    ycells2 = 2 * ycells
    nsubs = 20  # placeholder for deprecated parameter
    eeff = 0  # placeholder for deprecated parameter

    materials = {
        "Si RT": "3000 1 1 0 0 0 0 \"vacuum\"\n500 11.7 1 0 0 0 0 \"Silicon (room temperature)\"",
        "Si BT": "3000 1 1 0 0 0 0 \"vacuum\"\n500 11.45 1 1e-006 0 0 0 \"Silicon (10mK)\"",
        "SiOx+Si": "3000 1 1 0 0 0 0 \"vacuum\"\n0.55 3.78 11.7 1 0 0 0 \"SiOx (10mK)\"\n525 11.45 1 1e-06 0 0 0 \"Si "
                   "(10mK)\"",
        "Si+Al": "3000 1 1 0 0 0 0 \"vacuum\"\n0.5 9.9 1 0.0001 0 0 0 \"Alumina (99.5%)\"\n0.45 1 1 0 0 0 0 \"vacuum\""
                 "\n525 11.45 1 1e-06 0 0 0 \"Si (10mK)\"",
    }[materials_type]

    nlev = {
        "Si": 1,
        "Si BT": 1,
        "SiOx+Si": 2,
        "Si+Al": 3
    }[materials_type]

    return f"BOX {nlev} {xwidth} {ywidth} {xcells2} {ycells2} {nsubs} {eeff}\n{materials}"


def refplane(
        position: str,  # "LEFT" | "RIGHT" | "TOP" | "BOTTOM",
        length: int = 0,
        port_ipoly: str = "" # "LINK" or "FIX"
        ):
    if port_ipoly != "":
        plane_type = "LINK"
        poly = "POLY {} 1\n0\n".format(port_ipoly[0])
        length = ""
    else:
        plane_type = "FIX"
        poly = ""
    return f"DRP1 {position} {plane_type} {length}\n{poly}"


def refplanes(positions, length, port_ipolys):
    sonnet_str = ""
    for i, pos in enumerate(positions):
        sonnet_str += refplane(pos, length, port_ipolys[i])
    return sonnet_str


def port(
        portnum,
        ipolygon,
        ivertex,
        port_type="STD",  # STD for standard | AGND autogrounded | CUP cocalibrated
        xcord=0,  # pylint: disable=unused-argument
        ycord=0,  # pylint: disable=unused-argument
        group="",
        resist=50,
        react=0,
        induct=0,
        capac=0
):
    if group:
        group = '"' + group + '"'
    logging.info(locals())
    return f"POR1 {port_type} {group}\nPOLY {ipolygon} 1\n{ivertex}\n{portnum} {resist} {react} {induct} {capac}\n"
    # {xcord} {ycord} [reftype rpcallen]


# def ports(shapes):
#  sonnet_str = ""
#  polygons = 0
#
#  # FIXME Maybe the shapes will not have the same indexes as polygons in the region!
#  for shape in shapes.each():
#    if shape:
#      polygons += 1
#      ivertex = shape.property("sonnet_port_edge")
#      portnum = shape.property("sonnet_port_nr")
#      if ivertex!=None and portnum!=None:
#        sonnet_str += port(ipolygon=polygons-1, portnum=portnum, ivertex=ivertex)
#
#  return sonnet_str

def control(control_type):
    return {
        "Simple": "SIMPLE",  # Linear frequency sweep
        "ABS": "ABS", # Sonnet guesses the resonances, simulates about 5 points around the resonance and interpolates
                      # the rest
        "Sweep": "VARSWP"
    }[control_type]


def polygons(polygons, v, dbu, ilevel, fill_type):
    sonnet_str = 'NUM {}\n'.format(len(polygons))
    for i, hole_poly in enumerate(polygons):
        poly = hole_poly.resolved_holes()

        if hasattr(poly, 'isVia'):
            sonnet_str += via(poly, debugid=i, ilevel=next(ilevel))
        else:
            sonnet_str += polygon_head(nvertices=poly.num_points_hull() + 1,
                                   debugid=i + 1, ilevel=next(ilevel),
                                   filltype=fill_type)  # "Debugid" is actually used for mapping ports to polygons, 0 is
                                                        # not allowed

        for _, point in enumerate(poly.each_point_hull()):
            sonnet_str += "{} {}\n".format(point.x * dbu + v.x,
                                           -(point.y * dbu + v.y))  # sonnet Y-coordinate goes in the other direction
        point = next(poly.each_point_hull())  # first point again to close the polygon
        sonnet_str += "{} {}\nEND\n".format(point.x * dbu + v.x, -(point.y * dbu + v.y))

    return sonnet_str


def via(poly, debugid, ilevel):
    via_head = polygon_head(nvertices=poly.num_points_hull() + 1, debugid=debugid, ilevel=ilevel, mtype=0)
    return "VIA POLYGON\n" + via_head + "TOLEVEL 1 RING COVERS\n"
