# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import abc
from typing import List

from kqcircuits.pya_resolver import pya
from kqcircuits.elements.element import Element
from kqcircuits.simulations.port import Port
from kqcircuits.util.geometry_helper import region_with_merged_polygons, simple_region_with_merged_points


class Simulation:
    """Base class for simulation geometries.

    Generally, this class is intended to be subclassed by a specific simulation implementation; the
    implementation defines the simulation geometry ad ports in `build`.

    A convenience class method `Simulation.from_cell` is provided to create a Simulation from an
    existing cell. In this case no ports will be added.
    """

    # Metadata associated with simulation
    ports: List[Port]

    # Parameter type hints
    box: pya.DBox
    name: str
    use_ports: bool
    minimum_point_spacing: float

    PARAMETERS_SCHEMA = {
        **Element.PARAMETERS_SCHEMA,
        "box": {
            "type": pya.PCellParameterDeclaration.TypeShape,
            "description": "Border",
            "default": pya.DBox(pya.DPoint(0, 0), pya.DPoint(10000, 10000))
        },
        "name": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Name of the simulation",
            "default": "Simulation"
        },
        "use_ports": {
            "type": pya.PCellParameterDeclaration.TypeBoolean,
            "description": "Turn off to disable all ports (for debugging)",
            "default": True
        },
        "minimum_point_spacing": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Tolerance (um) for merging adjacent points in polygon",
            "default": 0.01
        },
        "polygon_tolerance": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Tolerance (um) for merging adjacent polygons in a layer",
            "default": 0.000
        }
    }

    def __init__(self, layout, **kwargs):
        """Initialize a Simulation.

        The initializer parses parameters, creates a top cell, and then calls `self.build` to create
        the simulation geometry, followed by `self.create_simulation_layers` to process the geometry
        so it is ready for exporting.

        Args:
            layout: the layout on which to create the simulation

        Keyword arguments:
            `**kwargs`:
                any parameter defined in the `PARAMETERS_SCHEMA` can be passed as a keyword
                argument, see `PCell parameters` section in the bottom

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
        else:
            self.layout = layout

        schema = self.__class__.get_schema()

        # Apply kwargs or default value
        # TODO: Validation? Could reuse the validation for Element
        for parameter, item in schema.items():
            if parameter in kwargs:
                setattr(self, parameter, kwargs[parameter])
            else:
                setattr(self, parameter, item['default'])

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
                box.left = round(box.left/grid_size)*grid_size
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
    pcell_params_by_name = Element.pcell_params_by_name

    def create_simulation_layers(self):
        """Create the layers used for simulation export.

        Based on any geometry defined on the relevant lithography layers.

        This method is called from `__init__` after `build`, and should not be called directly.

        Geometry is added to the following layers:
            - For each face ``b`` and ``t``, the inverse of ``base metal gap wo grid`` is divided into

                - ``simulation ground``, containing any metalization not galvanically connected to a port
                - ``simulation signal``, containing the remaining metalization.
            - ``simulation airbridge pads``, containing the geometry of ``airbridge pads``
            - ``simulation airbridge flyover``, containing the geometry of ``airbridge flyover``

        In the simulation layers, all geometry has been merged and converted to simple polygons
        (that is, polygons without holes).
        """
        def merged_region_from_layer(face_id, layer_name):
            """ Returns a `Region` containing all geometry from a specified layer merged together """
            return region_with_merged_polygons(pya.Region(self.cell.begin_shapes_rec(self.layout.layer(self.face(face_id)[layer_name]))), tolerance=self.polygon_tolerance / self.layout.dbu)

        def insert_simple_region(region, face_id, layer_name):
            """Converts a `Region` to simple polygons and inserts the result in a target layer."""
            self.cell.shapes(self.layout.layer(self.face(face_id)[layer_name])).insert(
                simple_region_with_merged_points(region, tolerance=self.minimum_point_spacing / self.layout.dbu))

        for face_id in [0, 1]:
            ground_box_region = pya.Region(self.box.to_itype(self.layout.dbu))
            lithography_region = merged_region_from_layer(face_id, "base metal gap wo grid")

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
                        location_itype = port.signal_location.to_itype(self.layout.dbu)
                        ground_region -= ground_region.interacting(pya.Edge(location_itype, location_itype))
                sim_region -= ground_region

            insert_simple_region(sim_region, face_id, "simulation signal")
            insert_simple_region(ground_region, face_id, "simulation ground")

        # Export airbridge regions as merged simple polygons
        insert_simple_region(merged_region_from_layer(0, "airbridge flyover"), 0, "simulation airbridge flyover")
        insert_simple_region(merged_region_from_layer(0, "airbridge pads"), 0, "simulation airbridge pads")

    def get_parameters(self):
        """Return dictionary with all parameters in PARAMETERS_SCHEMA and their values."""

        return {param: getattr(self, param) for param in self.__class__.get_schema()}
