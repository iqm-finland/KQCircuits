from kqcircuits.pya_resolver import pya

import re # regex
import logging
import kqcircuits.simulations.sonnet.parser as parser
from kqcircuits.defaults import default_layers
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar


class Port():
    def __init__(self, number, location, group="",
                 resistance=50, reactance=0, inductance=0, capacitance=0):
        self.number = number
        self.ref_location = location
        self.group = group
        self.resistance = resistance
        self.reactance = reactance
        self.inductance = inductance
        self.capacitance = capacitance

    def location(self):
        return self.ref_location


class SidePort(Port):
    def __init__(self, number, location, side, termination=False, group="",
                 resistance=50, reactance=0, inductance=0, capacitance=0):
        super().__init__(number, location, group, resistance, reactance, inductance, capacitance)
        self.side = {
            "l": "LEFT",
            "r": "RIGHT",
            "t": "TOP",
            "b": "BOTTOM",  # Y-coordinate in sonnet goes the other way around
        }[side]
        self.termination = termination  # width of the ground plane gap in the end for the transmission line
        self.dbox = None
        self.ref_location = location
        self.signal_location = location

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
        ls,
        materials_type="Si BT",
        simulation_safety=300,  # microns
        ports=[],
        grid_size=1,  # microns
        calgroup="",
        symmetry=False,  # top-bottom symmetry for sonnet
        detailed_resonance=False,
        lower_accuracy=False,
        current=False,
        fill_type="Staircase"
):
    layout = cell.layout()
    dbu = layout.dbu
    layer_opt = layout.layer(default_layers["b base metal gap wo grid"])
    layer_pad = layout.layer(default_layers["b airbridge pads"])
    layer_bridge = layout.layer(default_layers["b airbridge flyover"])
    layer_son = layout.layer(default_layers["simulation signal"])
    region_neg = pya.Region(cell.begin_shapes_rec(layer_opt))

    # safety ground
    region_pos = cell.dbbox()  # _per_layer(layer_opt)
    region_pos = pya.Region(region_pos.enlarge(
        simulation_safety,
        simulation_safety + (region_pos.height() % 2) / 2  # also ensure symmetry for 1 um grid
    ).to_itype(dbu)) if simulation_safety != 0 else pya.Region(region_pos.to_itype(dbu))

    for port in ports:
        port.location = port.signal_location
        port.termination = 10 # or False

        if isinstance(port, SidePort):
            port.dbox = region_pos.bbox().to_dtype(dbu)

            cell.shapes(layer_son).insert(
                pya.DText("port {}{}".format(port.number, port.group), pya.DTrans(port.location)))
            driveline = WaveguideCoplanar.create_cell(layout, {
                "path": pya.DPath([
                    port.signal_location,
                    port.location
                ], 1),
                "term1": port.termination
            })
            region_neg = region_neg + pya.Region(driveline.begin_shapes_rec(layer_opt)) + pya.Region(driveline.begin_shapes_rec(layer_pad))
        else:
            cell.shapes(layer_son).insert(
                pya.DText("port {}{}".format(port.number, port.group), pya.DTrans(port.location)))
    region_pos -= region_neg

    def simple_region(region):
        return pya.Region([poly.to_simple_polygon() for poly in region.each()]) #.to_itype(dbu)
    simregion = simple_region(region_pos)
    simpolygons = [p for p in simregion.each()];
    cell.shapes(layer_son).insert(simregion)

    # polygons in layers to sonnet string
    airbridge_polygons = []
    airpads_polygons = []
    if (materials_type=="Si+Al"):
        simple_airbridge = simple_region(pya.Region(layout.begin_shapes(cell, layer_bridge)))
        airbridge_polygons = [p for p in simple_airbridge.each()]

        simple_pads = simple_region(pya.Region(layout.begin_shapes(cell, layer_pad))
            .overlapping(pya.Region(layout.begin_shapes(cell, layer_bridge))))
        airpads_polygons = [p for p in simple_pads.each()]
        for p in airpads_polygons:
            setattr(p, 'isVia', True)


    level_iter = iter(len(simpolygons) * [(2 if materials_type=="Si+Al" else 0)] +
            len(airbridge_polygons) * [1] + len(airpads_polygons) * [2])

    polys = parser.polygons(simpolygons + airbridge_polygons + airpads_polygons,
        pya.DVector(-cell.dbbox().p1.x, -cell.dbbox().p2.y), dbu, # get the bottom left corner
        ilevel=level_iter, fill_type=("V" if (fill_type=="Conformal") else "N")
        )

    # find port edges
    # to preserve the port edge indices the geometry must not be changed after this
    sstring_ports = ""
    refplane_dirs = []
    port_ipolys = []
    for port in ports:
        if isinstance(port, SidePort):
            refplane_dirs.append(port.side)
            ipoly = poly_and_edge_indeces(cell, simpolygons + airbridge_polygons, dbu, port, ls)
            logging.info(re.findall(r'POLY (\d+)', ipoly))
            port_ipolys.append(re.findall(r'POLY (\d+)', ipoly)) # scan ipolygon
        sstring_ports += poly_and_edge_indeces(cell, simpolygons + airbridge_polygons, dbu, port, ls)

    return {
        "polygons": polys,
        "box": parser.box_from_cell(cell, 1, materials_type),
        "ports": sstring_ports,
        "calgroup": calgroup,
        "refplanes": parser.refplanes(refplane_dirs, simulation_safety, port_ipolys),
        "symmetry": parser.symmetry(symmetry),
        "nports": len(set([abs(port.number) for port in ports])),
        "resonance_abs": "DET_ABS_RES Y" if detailed_resonance else "DET_ABS_RES N",
        "lower_accuracy": "1" if lower_accuracy else "0",
        "current": "j" if current else ""
        }


def find_edge_from_point(polygons, layer: int, point: pya.DPoint, dbu, tolerance=0.01): #0.01
    # Find closest edge to point
    edges = [edge.to_dtype(dbu)
             for polygon in polygons
             for edge in polygon.each_edge()
             ]
    nearest = sorted([(edge.distance_abs(point), edge) for edge in edges])[0]
    if nearest[0] < tolerance:
        return nearest[1]
    else:
        raise ValueError("No edge found at point")


# TODO check all layers and not only base
def poly_and_edge_indeces(cell, polygons, dbu, port, layer, port_finder="brute_force"):
    logging.info("Looking for ports")

    signal_edge = find_edge_from_point(
        polygons,
        cell.layout().layer(layer),
        port.signal_location,
        dbu,
        tolerance=5.0 # hardcoded, feel free to change
        )
    logging.info(signal_edge)

    if port_finder == "brute_force":
        for i, poly in enumerate(polygons):
            for j, edge in enumerate(poly.each_edge()):
                edge = edge.to_dtype(dbu)

                if (signal_edge.x1 == edge.x1 and signal_edge.y1 == edge.y1 and
                    signal_edge.x2 == edge.x2 and signal_edge.y2 == edge.y2): # edge.to_dtype(dbu).contains(port_loc)
                    logging.info(i, j)
                    return parser.port(
                        portnum=port.number,
                        ipolygon=i + 1,
                        ivertex=j,
                        port_type=("CUP" if port.group else "STD"),
                        group=port.group,
                        resist=port.resistance,
                        react=port.reactance,
                        induct=port.inductance,
                        capac=port.capacitance
                    )
        raise ValueError("No edge found for Sonnet port {}{}".format(port.number, port.group))
        return
    else:
        """ The following would be faster but works only for
        simple geometry with even integers for points
        """
        for i, poly in enumerate(polygons):
            for j, edge in enumerate(poly.each_edge()):
                if edge.to_dtype(dbu).contains(port_loc):
                    logging.info(i, j)
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
