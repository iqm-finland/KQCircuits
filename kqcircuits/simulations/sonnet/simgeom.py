from kqcircuits.pya_resolver import pya

import kqcircuits.simulations.sonnet.parser as parser
from kqcircuits.defaults import default_layers
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar


class Port():
    def __init__(self, sonnet_nr, location, group="",
                 resist=50, react=0, induct=0, capac=0
                 ):
        self.sonnet_nr = sonnet_nr
        self.ref_location = location
        self.group = group
        self.resist = resist
        self.react = react
        self.induct = induct
        self.capac = capac

    def location(self):
        return self.ref_location


class SidePort(Port):
    def __init__(self, sonnet_nr, location, side, termination=False, group="",
                 resist=50, react=0, induct=0, capac=0):
        super().__init__(sonnet_nr, location, group, resist, react, induct, capac)
        self.side = {
            "l": "LEFT",
            "r": "RIGHT",
            "t": "TOP",
            "b": "BOTTOM",  # Y-coordinate in sonnet goes the other way around
        }[side]
        self.termination = termination  # width of the ground plane gap in the end for the transmission line
        self.dbox = None

    def location(self):
        dbox = self.dbox
        return {
            "LEFT": pya.DVector(dbox.p1.x, self.ref_location.y),
            "RIGHT": pya.DVector(dbox.p2.x, self.ref_location.y),
            "TOP": pya.DVector(self.ref_location.x, dbox.p2.y),
            "BOTTOM": pya.DVector(self.ref_location.x, dbox.p1.y),
        }[self.side]




def add_sonnet_geometry(
        cell,
        simualtion_safety=300,  # microns
        ports=[],
        grid_size=1,  # microns
        calgroup="",
        symmetry=False  # top-bottom symmetry for sonnet
):
    layout = cell.layout()
    dbu = layout.dbu
    layer_opt = layout.layer(default_layers["b base metal gap wo grid"])
    layer_son = layout.layer(default_layers["simulation signal"])
    region_neg = pya.Region(cell.begin_shapes_rec(layer_opt))

    # safety ground
    region_pos = cell.dbbox()  # _per_layer(layer_opt)
    region_pos = pya.Region(region_pos.enlarge(
        simualtion_safety,
        simualtion_safety + (region_pos.height() % 2) / 2  # also esnure summetry for 1 um grid
    ).to_itype(dbu))

    # add port feedlines
    for port in ports:
        if isinstance(port, SidePort):
            port.dbox = region_pos.bbox().to_dtype(dbu)

            cell.shapes(layer_son).insert(
                pya.DText("port {}{}".format(port.sonnet_nr, port.group), pya.DTrans(port.location())))
            driveline = WaveguideCoplanar.create_cell(layout, {
                "path": pya.DPath([
                    port.ref_location,
                    port.location()
                ], 1),
                "term1": port.termination
            })
            region_neg = region_neg + pya.Region(driveline.begin_shapes_rec(layer_opt))
        else:
            cell.shapes(layer_son).insert(
                pya.DText("port {}{}".format(port.sonnet_nr, port.group), pya.DTrans(port.location())))
    region_pos -= region_neg
    simregion = simple_region(region_pos);
    simpolygons = [p for p in simregion.each()];
    cell.shapes(layer_son).insert(simregion)

    # find port edges
    # to preserv the port edge indexes the geometry must not be changed after this
    sstring_ports = ""
    refplane_dirs = []
    for port in ports:
        if isinstance(port, SidePort):
            refplane_dirs.append(port.side)
        sstring_ports += poly_and_edge_indeces(simpolygons, dbu, port)

    return {
        "polygons": parser.polygons(simpolygons, pya.DVector(-cell.dbbox().p1.x, -cell.dbbox().p2.y), dbu),
        "box": parser.box_from_cell(cell, 1),
        "ports": sstring_ports,
        "calgroup": calgroup,
        "refpalnes": parser.refplanes(refplane_dirs, simualtion_safety),
        "symmetry": parser.symmetry(symmetry),
        "nports": len(set([abs(port.sonnet_nr) for port in ports])),
    }


def poly_and_edge_indeces(polygons, dbu, port):
    # port location
    port_loc = port.location()

    print("Looking for ports")
    # port polygon and edge
    for i, poly in enumerate(polygons):
        for j, edge in enumerate(poly.each_edge()):
            if edge.to_dtype(dbu).contains(port_loc):
                print(i, j)
                return parser.port(
                    portnum=port.sonnet_nr,
                    ipolygon=i + 1,
                    ivertex=j,
                    port_type=("CUP" if port.group else "STD"),
                    group=port.group,
                    resist=port.resist,
                    react=port.react,
                    induct=port.induct,
                    capac=port.capac
                )
    raise ValueError("No edge found for Sonnet port {}{}".format(port.sonnet_nr, port.group))
    return ""
