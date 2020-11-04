import logging

import os.path
from kqcircuits.pya_resolver import pya
from kqcircuits.defaults import default_layers
from kqcircuits.simulations.export.simulation_export import SimulationExport
from kqcircuits.simulations.export.sonnet import parser
from kqcircuits.simulations.export.util import find_edge_from_point_in_polygons
from kqcircuits.simulations.port import InternalPort, EdgePort


class SonnetExport(SimulationExport):
    PARAMETERS = [
        *SimulationExport.PARAMETERS,
        'detailed_resonance', 'lower_accuracy', 'control', 'current', 'fill_type', 'simulation_safety'
    ]

    # default values for parameters
    detailed_resonance = False
    lower_accuracy = False
    current = False
    control = 'ABS'
    fill_type = 'Staircase'
    simulation_safety = 0

    @property
    def son_filename(self):
        return self.path.joinpath(self.file_prefix + '.son')

    def write(self):

        # detect airbridges
        shapes_in_air = self.simulation.layout.begin_shapes(self.simulation.cell, self.simulation.layout.layer(
            default_layers["b airbridge flyover"]))
        materials_type = "Si+Al" if not shapes_in_air.shape().is_null() else "Si BT"

        sonnet_strings = self.get_sonnet_strings(
            materials_type=materials_type,
            grid_size=1,  # microns
            symmetry=False,  # top-bottom symmetry for sonnet -> could be 4-8x faster
        )
        sonnet_strings["control"] = parser.control(self.control)

        filename = str(self.son_filename)
        parser.apply_template(
            os.path.join(os.path.dirname(os.path.abspath(parser.__file__)), "template.son"),
            filename,
            sonnet_strings
        )

    def get_sonnet_strings(
            self,
            materials_type="Si BT",
            grid_size=1,  # microns
            symmetry=False,  # top-bottom symmetry for sonnet
    ):
        layout = self.simulation.cell.layout()
        dbu = layout.dbu
        layer_pad = layout.layer(default_layers["b simulation airbridge pads"])
        layer_bridge = layout.layer(default_layers["b simulation airbridge flyover"])
        layer_son = layout.layer(default_layers["b simulation signal"])
        layer_son_ground = layout.layer(default_layers["b simulation ground"])

        def simple_region(region):
            return pya.Region([poly.to_simple_polygon() for poly in region.each()]) #.to_itype(dbu)

        simpolygons = [p.polygon for p in self.simulation.cell.shapes(layer_son).each()] + \
                      [p.polygon for p in self.simulation.cell.shapes(layer_son_ground).each()]
        airbridge_polygons = [p.polygon for p in self.simulation.cell.shapes(layer_bridge).each()]
        airpads_polygons = [p.polygon for p in self.simulation.cell.shapes(layer_pad).each()]
        for p in airpads_polygons:
            p.isVia = True

        level_iter = iter(len(simpolygons) * [(2 if materials_type=="Si+Al" else 0)] +
                len(airbridge_polygons) * [1] + len(airpads_polygons) * [2])

        polys = parser.polygons(simpolygons + airbridge_polygons + airpads_polygons,
                                pya.DVector(-self.simulation.box.p1.x, -self.simulation.box.p2.y), dbu,  # get the bottom left corner
                                ilevel=level_iter, fill_type=("V" if (self.fill_type=="Conformal") else "N")
                                )

        # find port edges
        sstring_ports = ""
        refplane_dirs = []
        port_ipolys = []
        group_ascii = ord('A')
        calgroup = ''

        if self.simulation.use_ports:
            for port in self.simulation.ports:
                if isinstance(port, InternalPort):
                    sstring_ports += poly_and_edge_indeces(
                        simpolygons + airbridge_polygons, dbu,
                        port, port.number, port.signal_location, chr(group_ascii))
                    sstring_ports += poly_and_edge_indeces(
                        simpolygons + airbridge_polygons, dbu,
                        port, -port.number, port.ground_location, chr(group_ascii))
                    calgroup += 'CUPGRP "{}"\nID 28\nGNDREF F\nTWTYPE FEED\nEND\n'.format(chr(group_ascii))
                    group_ascii += 1
                elif isinstance(port, EdgePort):
                    # TODO: re-implement calibration
                    #
                    #     refplane_dirs.append(port.side)
                    #     ipoly = poly_and_edge_indeces(cell, simpolygons + airbridge_polygons, dbu, port, ls)
                    #     logging.info(re.findall(r'POLY (\d+)', ipoly))
                    #     port_ipolys.append(re.findall(r'POLY (\d+)', ipoly)) # scan ipolygon
                    sstring_ports += poly_and_edge_indeces(
                        simpolygons + airbridge_polygons, dbu,
                        port, port.number, port.signal_location, "")

        sonnet_box = parser.box(
            xwidth=self.simulation.box.width(),
            ywidth=self.simulation.box.height(),
            xcells=int(self.simulation.box.width() / grid_size),
            ycells=int(self.simulation.box.height() / grid_size),
            materials_type=materials_type
        )

        return {
            "polygons": polys,
            "box": sonnet_box,
            "ports": sstring_ports,
            "calgroup": calgroup,
            "refplanes": parser.refplanes(refplane_dirs, self.simulation_safety, port_ipolys),
            "symmetry": parser.symmetry(symmetry),
            "nports": len(set([abs(port.number) for port in self.simulation.ports])),
            "resonance_abs": "DET_ABS_RES Y" if self.detailed_resonance else "DET_ABS_RES N",
            "lower_accuracy": "1" if self.lower_accuracy else "0",
            "current": "j" if self.current else ""
            }


def poly_and_edge_indeces(polygons, dbu, port, number, location, group):
    i, j, signal_edge = find_edge_from_point_in_polygons(
        polygons,
        location,
        dbu,
        tolerance=5.0  # hardcoded, feel free to change
        )

    return parser.port(
        portnum=number,
        ipolygon=i + 1,
        ivertex=j,
        port_type=("CUP" if group else "STD"),
        group=group,
        resist=port.resistance,
        react=port.reactance,
        induct=port.inductance,
        capac=port.capacitance
    )
