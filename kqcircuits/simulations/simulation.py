# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

import abc
from typing import List

from kqcircuits.pya_resolver import pya
from kqcircuits.defaults import default_layers
from kqcircuits.elements.element import Element, get_refpoints
from kqcircuits.simulations.port import Port


class Simulation:
    """Base class for simulation geometries.

    Empty, has a box dimension
    """

    # Metadata associated with simulation
    ports: List[Port]

    # Parameter type hints
    box: pya.DBox
    name: str
    ls: pya.LayerInfo
    lg: pya.LayerInfo

    PARAMETERS_SCHEMA = {
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
        "ls": {
            "type": pya.PCellParameterDeclaration.TypeLayer,
            "description": "Layer simulation signal",
            "default": default_layers["simulation signal"]
        },
        "lg": {
            "type": pya.PCellParameterDeclaration.TypeLayer,
            "description": "Layer simulation ground",
            "default": default_layers["simulation ground"]
        },
    }

    def __init__(self, layout, **kwargs):
        super().__init__()
        if layout is None or not isinstance(layout, pya.Layout):
            error = ValueError("Cannot create simulation with invalid or nil layout.")
            # TODO: Set up logging
            self.__log.exception(exc_info=error)
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
        self.cell = layout.create_cell(self.name)
        self.build()
        self.create_simulation_layers()

    @abc.abstractmethod
    def build(self):
        """
        Build simulation geometry.
        """
        return

    @classmethod
    def get_schema(cls):
        if not hasattr(cls, "schema"):
            # Bit of a hack for now, "sideload" base schema from Elements
            schema = Element.get_schema()

            for c in cls.__mro__:
                if hasattr(c, "PARAMETERS_SCHEMA") and c.PARAMETERS_SCHEMA is not None:
                    schema = {**c.PARAMETERS_SCHEMA, **schema}
            return schema
        else:
            return cls.schema

    face = Element.face

    def get_refpoints(self, cell, cell_transf=pya.DTrans()):
        return get_refpoints(self.layout.layer(default_layers["annotations"]), cell, cell_transf)

    def simple_region(self, region):
        return pya.Region([poly.to_simple_polygon() for poly in region.each()])

    def insert_cell(self, cell, trans, name=None):
        """ Inserts a subcell into the present cell.
        Arguments:
            cell: placed cell
            trans: used transformation for placement
            name: possible instance name inserted into subcell properties under `id`. Default is None

        Return:
            tuple of placed cell instance and reference points with the same transformation
            """
        cell_inst = self.cell.insert(pya.DCellInstArray(cell.cell_index(), trans))
        if name is not None:
            cell_inst.set_property("id", name)
        refpoints_abs = self.get_refpoints(cell, cell_inst.dtrans)
        return cell_inst, refpoints_abs

    def create_simulation_layers(self):
        ground_box_region = pya.Region(self.box.to_itype(self.layout.dbu))
        lithography_region = pya.Region(self.cell.begin_shapes_rec(self.layout.layer(self.face()["base metal gap wo grid"]))).merged()
        airbridge_pad_region = pya.Region(self.cell.begin_shapes_rec(self.layout.layer(self.face()["airbridge pads"]))).merged()
        # airpad_flyover_region_ = pya.Region(self.cell.begin_shapes_rec(self.layout.layer(self.face()["airbridge pads"]))).merged()
        sim_region = ground_box_region - lithography_region + airpad_pad_region

        # Find the ground plane and subtract it from the simulation area
        # First, add all polygons touching any of the edges
        ground_region = pya.Region()
        for edge in ground_box_region.edges():
            ground_region += sim_region.interacting(edge)
        # Now, remove all edge polygons which are also a port
        for port in self.ports:
            location_itype = port.signal_location.to_itype(self.layout.dbu)
            ground_region -= ground_region.interacting(pya.Edge(location_itype , location_itype))
        sim_region -= ground_region

        self.cell.shapes(self.layout.layer(self.ls)).insert(self.simple_region(sim_region))
        self.cell.shapes(self.layout.layer(self.lg)).insert(self.simple_region(ground_region))

    def get_parameters(self):
        """ Return dictionary with all parameters in PARAMETER_SCHEMA and their values """

        return {param: getattr(self, param) for param in self.__class__.get_schema()}
