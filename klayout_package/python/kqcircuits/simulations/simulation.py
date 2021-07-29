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


import abc
from typing import List

from kqcircuits.elements.airbridges.airbridge import Airbridge
from kqcircuits.elements.element import Element
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
from kqcircuits.pya_resolver import pya
from kqcircuits.simulations.port import Port, InternalPort, EdgePort
from kqcircuits.util.geometry_helper import region_with_merged_polygons, region_with_merged_points
from kqcircuits.util.parameters import Param, pdt, add_parameters_from


@add_parameters_from(Element)
class Simulation:
    """Base class for simulation geometries.

    Generally, this class is intended to be subclassed by a specific simulation implementation; the
    implementation defines the simulation geometry ad ports in `build`.

    A convenience class method `Simulation.from_cell` is provided to create a Simulation from an
    existing cell. In this case no ports will be added.
    """

    # Metadata associated with simulation
    ports: List[Port]

    # Parameters
    box = Param(pdt.TypeShape, "Border", pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000)))
    name = Param(pdt.TypeString, "Name of the simulation", "Simulation")

    use_ports = Param(pdt.TypeBoolean, "Turn off to disable all ports (for debugging)", True)
    use_internal_ports = Param(pdt.TypeBoolean, "Use internal (lumped) ports. The alternative is wave ports.", True)
    port_width = Param(pdt.TypeDouble, "Width (um) of wave ports", 400.0)

    box_height = Param(pdt.TypeDouble, "Height (um) of vacuum above chip in case of single chip.", 1000.0)
    substrate_height = Param(pdt.TypeDouble, "Height (um) of the bottom substrate.", 550.0)
    permittivity = Param(pdt.TypeDouble, "Permittivity of the substrates.", 11.45)

    wafer_stack_type = Param(pdt.TypeDouble,
                             "Defines whether to use single chip ('planar') or flip chip ('multiface').", 'planar')
    chip_distance = Param(pdt.TypeDouble, "Height (um) of vacuum between two chips in case of flip chip.", 8.0)
    substrate_height_top = Param(pdt.TypeDouble,
                                 "Height (um) of the substrate of the top chip in case of flip chip.", 375.0)

    airbridge_height = Param(pdt.TypeDouble, "Height (um) of airbridges.", 3.4)

    waveguide_length = Param(pdt.TypeDouble,
                             "Length of waveguide stubs or distance between couplers and waveguide turning point", 100)
    over_etching = Param(pdt.TypeDouble, "Expansion of metal gaps (negative to shrink the gaps).", 0, unit="μm")

    minimum_point_spacing = Param(pdt.TypeDouble, "Tolerance (um) for merging adjacent points in polygon", 0.01)
    polygon_tolerance = Param(pdt.TypeDouble, "Tolerance (um) for merging adjacent polygons in a layer", 0.002)

    def __init__(self, layout, **kwargs):
        """Initialize a Simulation.

        The initializer parses parameters, creates a top cell, and then calls `self.build` to create
        the simulation geometry, followed by `self.create_simulation_layers` to process the geometry
        so it is ready for exporting.

        Args:
            layout: the layout on which to create the simulation

        Keyword arguments:
            `**kwargs`:
                Any parameter can be passed as a keyword argument.

                In addition, `cell` can be passed as keyword argument. If `cell` is supplied, it will be
                used as the top cell for the simulation. Otherwise, a new cell will be created. See
                `Simulation.from_cell` for creating simulations from existing cells.
        """
        super().__init__()
        if layout is None or not isinstance(layout, pya.Layout):
            error_text = "Cannot create simulation with invalid or nil layout."
            error = ValueError(error_text)
            self.__log.exception(error_text, exc_info=error)
            raise error

        self.layout = layout
        schema = type(self).get_schema()

        # Apply kwargs or default value
        # TODO: Validation? Could reuse the validation for Element
        for parameter, item in schema.items():
            if parameter in kwargs:
                setattr(self, parameter, kwargs[parameter])
            else:
                setattr(self, parameter, item.default)

        self.ports = []
        if 'cell' in kwargs:
            self.cell = kwargs['cell']
        else:
            self.cell = layout.create_cell(self.name)

        self.build()
        self.create_simulation_layers()

    @classmethod
    def from_cell(cls, cell, margin=300, grid_size=1, **kwargs):
        """Create a Simulation from an existing cell.

        Arguments:
            cell: existing top cell for the Simulation
            margin: distance [μm] to expand the simulation box (ground plane) around the bounding
                box of the cell If the `box` keyword argument is given, margin is ignored.
            grid_size: size of the simulation box will be rounded to this resolution
                If the `box` keyword argument is given, grid_size is ignored.
            `**kwargs`: any simulation parameters passed

        Returns:
            Simulation instance
        """
        extra_kwargs = {}

        if 'box' not in kwargs:
            box = cell.dbbox().enlarge(margin, margin)
            if grid_size > 0:
                box.left = round(box.left / grid_size) * grid_size
                box.right = round(box.right / grid_size) * grid_size
                box.bottom = round(box.bottom / grid_size) * grid_size
                box.top = round(box.top / grid_size) * grid_size
            extra_kwargs['box'] = box

        return cls(cell.layout(), cell=cell, **kwargs, **extra_kwargs)

    @abc.abstractmethod
    def build(self):
        """Build simulation geometry.

        This method is to be overridden, and the overriding method should create the geometry to be
        simulated and add any ports to `self.ports`.
        """
        return

    # Inherit specific methods from Element
    get_schema = classmethod(Element.get_schema.__func__)
    face = Element.face
    insert_cell = Element.insert_cell
    get_refpoints = Element.get_refpoints
    add_element = Element.add_element
    get_layer = Element.get_layer

    def create_simulation_layers(self):
        """Create the layers used for simulation export.

        Based on any geometry defined on the relevant lithography layers.

        This method is called from `__init__` after `build`, and should not be called directly.

        Geometry is added to the following layers:
            - For each face ``b`` and ``t``, the inverse of ``base_metal_gap_wo_grid`` is divided into

                - ``simulation_ground``, containing any metalization not galvanically connected to a port
                - ``simulation_signal``, containing the remaining metalization.
            - ``simulation_airbridge_pads``, containing the geometry of ``airbridge_pads``
            - ``simulation_airbridge_flyover``, containing the geometry of ``airbridge_flyover``

        In the simulation layers, all geometry has been merged and converted to simple polygons
        (that is, polygons without holes).
        """
        def merged_region_from_layer(face_id, layer_name, expansion=0.0):
            """ Returns a `Region` containing all geometry from a specified layer merged together """
            return region_with_merged_polygons(
                pya.Region(self.cell.begin_shapes_rec(self.layout.layer(self.face(face_id)[layer_name]))),
                tolerance=self.polygon_tolerance / self.layout.dbu, expansion=expansion / self.layout.dbu)

        def insert_region(region, face_id, layer_name):
            """Merges points in the `region` and inserts the result in a target layer."""
            self.cell.shapes(self.layout.layer(self.face(face_id)[layer_name])).insert(
               region_with_merged_points(region, tolerance=self.minimum_point_spacing / self.layout.dbu))

        for face_id in [0, 1]:
            ground_box_region = pya.Region(self.box.to_itype(self.layout.dbu))
            lithography_region = merged_region_from_layer(face_id, "base_metal_gap_wo_grid", self.over_etching)

            if lithography_region.is_empty():
                sim_region = pya.Region()
                ground_region = ground_box_region
            else:
                sim_region = ground_box_region - lithography_region

                # Find the ground plane and subtract it from the simulation area
                # First, add all polygons touching any of the edges
                ground_region = pya.Region()
                for edge in ground_box_region.edges():
                    ground_region += sim_region.interacting(edge)
                # Now, remove all edge polygons which are also a port
                if self.use_ports:
                    for port in self.ports:
                        if port.face == face_id:
                            location_itype = port.signal_location.to_itype(self.layout.dbu)
                            ground_region -= ground_region.interacting(pya.Edge(location_itype, location_itype))
                ground_region.merge()
                sim_region -= ground_region

            insert_region(sim_region, face_id, "simulation_signal")
            insert_region(ground_region, face_id, "simulation_ground")

        # Export airbridge regions as merged simple polygons
        insert_region(merged_region_from_layer(0, "airbridge_flyover"), 0, "simulation_airbridge_flyover")
        insert_region(merged_region_from_layer(0, "airbridge_pads"), 0, "simulation_airbridge_pads")

    def produce_waveguide_to_port(self, location, towards, port_nr, side,
                                  use_internal_ports=None, waveguide_length=None,
                                  term1=0, turn_radius=None,
                                  a=None, b=None, over_etching=None,
                                  airbridge=False, airbridge_a=None, airbridge_b=None,
                                  face=0):
        """Create a waveguide connection from some `location` to a port, and add the corresponding port to
        `simulation.ports`.

        Arguments:
            location (pya.DPoint): Point where the waveguide connects to the simulation
            towards (pya.DPoint): Point that sets the direction of the waveguide.
                The waveguide will start from `location` and go towards `towards`
            port_nr (int): Port index for the simulation engine starting from 1
            side (str): Indicate on which edge the port should be located. Ignored for internal ports.
                Must be one of `left`, `right`, `top` or `bottom`
            use_internal_ports (bool, optional): if True, ports will be inside the simulation. If False, ports will be
                brought out to an edge of the box, determined by `side`.
                Defaults to the value of the `use_internal_ports` parameter
            waveguide_length (float, optional): length of the waveguide [μm], used only for internal ports
                Defaults to the value of the `waveguide_length` parameter
            term1 (float, optional): Termination gap [μm] at `location`. Default 0
            turn_radius (float, optional): Turn radius of the waveguide. Not relevant for internal ports.
                Defaults to the value of the `r` parameter
            a (float, optional): Center conductor width. Defaults to the value of the `a` parameter
            b (float, optional): Conductor gap width. Defaults to the value of the `b` parameter
            over_etching (float, optional): Expansion of gaps. Defaults to the value of the `over_etching` parameter
            airbridge (bool, optional): if True, an airbridge will be inserted at `location`. Default False.
            airbridge_a (float, optional): Center conductor width for the airbridge part of the waveguide.
                Defaults to the value of the `a` parameter
            airbridge_b (float, optional): Gap conductor width for the airbridge part of the waveguide.
                Defaults to the value of the `b` parameter
            face: face to place waveguide and port on. Either 0 (default) or 1, for bottom or top face.
        """

        waveguide_safety_overlap = 0.005  # Extend waveguide by this amount to avoid gaps due to nm-scale rounding
                                          # errors
        waveguide_gap_extension = 1  # Extend gaps beyond waveguides into ground plane to define the ground port edge

        if turn_radius is None:
            turn_radius = self.r
        if a is None:
            a = self.a
        if b is None:
            b = self.b
        if over_etching is None:
            over_etching = self.over_etching
        if airbridge_a is None:
            airbridge_a = self.a
        if airbridge_b is None:
            airbridge_b = self.b
        if use_internal_ports is None:
            use_internal_ports = self.use_internal_ports
        if waveguide_length is None:
            waveguide_length = self.waveguide_length

        # Create a new path in the direction of path but with length waveguide_length
        direction = towards - location
        direction = direction / direction.length()

        # First node may be an airbridge
        if airbridge:
            first_node = Node(location, Airbridge, _a=airbridge_a, _b=airbridge_b)
        else:
            first_node = Node(location)

        if use_internal_ports:
            signal_point = location + (waveguide_length + over_etching) * direction
            ground_point = location + (waveguide_length + a - 3 * over_etching) * direction

            nodes = [
                first_node,
                Node(signal_point + waveguide_safety_overlap * direction),
            ]
            port = InternalPort(port_nr, *self.etched_line(signal_point, ground_point), face=face)

            extension_nodes = [
                Node(ground_point),
                Node(ground_point + waveguide_gap_extension * direction)
            ]
        else:
            corner_point = location + (waveguide_length + turn_radius) * direction
            port_edge_point = {
                "left": pya.DPoint(self.box.left, corner_point.y),
                "right": pya.DPoint(self.box.right, corner_point.y),
                "top": pya.DPoint(corner_point.x, self.box.top),
                "bottom": pya.DPoint(corner_point.x, self.box.bottom)
            }[side]

            nodes = [
                first_node,
                Node(corner_point),
                Node(port_edge_point),
            ]
            port = EdgePort(port_nr, port_edge_point, face=face)

        tl = self.add_element(WaveguideComposite,
                              nodes=nodes,
                              r=turn_radius,
                              term1=term1,
                              term2=0,
                              a=a,
                              b=b,
                              face_ids=[self.face_ids[face]]
                              )

        self.cell.insert(pya.DCellInstArray(tl.cell_index(), pya.DTrans()))
        feedline_length = tl.length()

        if use_internal_ports:
            port_end_piece = self.add_element(WaveguideComposite,
                                              nodes=extension_nodes,
                                              a=a,
                                              b=b,
                                              term1=a-4*over_etching,
                                              term2=0,
                                              face_ids=[self.face_ids[face]]
                                              )
            self.cell.insert(pya.DCellInstArray(port_end_piece.cell_index(), pya.DTrans()))
        else:
            port.deembed_len = feedline_length

        self.ports.append(port)

    def get_parameters(self):
        """Return dictionary with all parameters and their values."""

        return {param: getattr(self, param) for param in type(self).get_schema()}

    def etched_line(self, p1: pya.DPoint, p2: pya.DPoint):
        """
            Return the end points of line segment after extending it at both ends by amount of over_etching.
            This function must be used when initializing InternalPort.

            Arguments:
                p1 (pya.DPoint): first end of line segment
                p2 (pya.DPoint): second end of line segment

            Returns:
                 [p1 - d, p2 + d]: list of extended end points.
        """
        d = (self.over_etching / p1.distance(p2)) * (p2 - p1)
        return [p1 - d, p2 + d]
