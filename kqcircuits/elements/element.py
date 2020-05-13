# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from autologging import logged, traced

from kqcircuits.defaults import default_layers, default_circuit_params, default_faces
from kqcircuits.util.library_helper import LIBRARY_NAMES, load_library, to_library_name
from kqcircuits.util.parameter_helper import normalize_rules, Validator


@traced
def get_refpoints(layer, cell, cell_transf=pya.DTrans(), rec_levels=None):
    """ Extract reference points from cell from layer as dictionary.

    Args:
        layer: layer specification for source of refpoints
        cell: cell containing the refpoints
        cell_transf: transform for converting refpoints into target coordinate system
        rec_levels: recursion level when looking for refpoints from subcells. Set to 0 to disable recursion.

    Returns:
        Dictionary, where keys are refpoints names, values are DPoints.

    """

    refpoints = {}
    shapes_iter = cell.begin_shapes_rec(layer)
    if rec_levels is not None:
        shapes_iter.max_depth = rec_levels
    while not shapes_iter.at_end():
        shape = shapes_iter.shape()
        if shape.type() in (pya.Shape.TText, pya.Shape.TTextRef):
            refpoints[shape.text_string] = cell_transf * (shapes_iter.dtrans() * (pya.DPoint(shape.text_dpos)))
        shapes_iter.next()

    return refpoints


@logged
@traced
class Element(pya.PCellDeclarationHelper):
    """Base PCell declaration for elements.

    The PARAMETERS_SCHEMA class attribute defines the PCell parameters for an element. Notice, that to get the
    combined PARAMETERS_SCHEMA of the element and all its ancestors, you should use the "get_schema()" method instead
    of accessing PARAMETERS_SCHEMA directly.
    """

    LIBRARY_NAME = LIBRARY_NAMES["Element"]
    LIBRARY_DESCRIPTION = "Superconducting quantum circuit library for elements."

    PARAMETERS_SCHEMA = {
        "la": {
            "type": pya.PCellParameterDeclaration.TypeLayer,
            "description": "Layer annotation",
            "default": default_layers["annotations"]
        },
        "a": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Width of center conductor (um)",
            "default": default_circuit_params["a"]
        },
        "b": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Width of gap (um)",
            "default": default_circuit_params["b"]
        },
        "n": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Number of points on turns",
            "default": default_circuit_params["n"]
        },
        "r": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Turn radius (um)",
            "default": default_circuit_params["r"]
        },
        "refpoints": {
            "type": pya.PCellParameterDeclaration.TypeNone,
            "description": "Reference points",
            "default": {"base": pya.DVector(0, 0)},
            "hidden": True
        },
        "margin": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Margin of the protection layer (um)",
            "default": 5
        },
        "face_ids": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Chip face IDs, list of b | t | c ",
            "default": ["b", "t", "c"],
        },
    }

    def __init__(self):
        super().__init__()
        self.__set_parameters()

    @staticmethod
    def create_cell_from_shape(layout, name):
        load_library(Element.LIBRARY_NAME)
        return layout.create_cell(name, Element.LIBRARY_NAME)

    @classmethod
    def create_cell(cls, layout, parameters):
        """Create cell for this element in layout.

        Args:
            layout: pya.Layout object where this cell is created
            parameters: PCell parameters for the element

        """
        cell_library_name = to_library_name(cls.__name__)
        schema = cls.get_schema()
        validator = Validator(schema)
        if validator.validate(parameters):
            load_library(cls.LIBRARY_NAME)
            return layout.create_cell(cell_library_name, cls.LIBRARY_NAME, parameters)

    def insert_cell(self, cell, trans=None, name=None):
        """ Inserts a subcell into the present cell.
        Arguments:
            cell: placed cell
            trans: used transformation for placement. None by default, which places the subcell into the coordinate
                origin of the parent cell
            name: possible instance name inserted into subcell properties under `id`. Default is None

        Return:
            tuple of placed cell instance and reference points with the same transformation
            """
        if trans is None:
            trans = pya.DTrans()
        cell_inst = self.cell.insert(pya.DCellInstArray(cell.cell_index(), trans))
        if name is not None:
            cell_inst.set_property("id", name)
        refpoints_abs = self.get_refpoints(cell, cell_inst.dcplx_trans)  # should use .dtrans, if possible
        return cell_inst, refpoints_abs

    def face(self, face_index=0):
        """Returns the face dictionary corresponding to self.face_ids[face_index].

        The face dictionary contains key "id" for the face ID and keys for all the available layers in that face.

        Args:
            face_index: index of the face_id in self.face_ids, default=0

        """
        return default_faces[self.face_ids[face_index]]

    def pcell_params_by_name(self, whitelist=None):
        """ Give PCell parameters as a dictionary

        Arguments:
            whitelist: list of dictionary for filtering the returned parameters. If dictionary, keys used for
            filtering.

        Returns:
            Dictionary with all parameter names in the PCell declaration `PARAMETER_SCHEMA` as keys and
            corresponding current values.
            """
        d = {}
        if type(whitelist) is dict:
            whitelist = whitelist.keys()
        for name in self.__class__.get_schema().keys():
            if whitelist is not None and name not in whitelist:
                continue
            d[name] = self.__getattribute__(name)
        return d

    @classmethod
    def get_schema(cls):
        """Returns the combined PARAMETERS_SCHEMA of the class "cls" and all its ancestor classes."""
        if not hasattr(cls, "schema"):
            schema = {}
            for c in cls.__mro__:
                if hasattr(c, "PARAMETERS_SCHEMA") and c.PARAMETERS_SCHEMA is not None:
                    schema = {**c.PARAMETERS_SCHEMA, **schema}
            return schema
        else:
            return cls.schema

    def produce_impl(self):
        # call the super.produce_impl once all the refpoints have been added to self.refpoints
        # add all ref points to user properties and draw to annotations
        for name, refpoint in self.refpoints.items():
            self.cell.set_property(name, refpoint)
            # self.cell.shapes(self.layout.layer(self.la)).insert(pya.DPath([pya.DPoint(0,0),pya.DPoint(0,0)+refpoint],1))
            text = pya.DText(name, refpoint.x, refpoint.y)
            self.cell.shapes(self.layout.layer(self.la)).insert(text)
        self.cell.refpoints = self.refpoints

    def get_refpoints(self, cell, cell_transf=pya.DTrans(), rec_levels=None):
        """ See `get_refpoints`. """
        return get_refpoints(self.layout.layer(default_layers["annotations"]), cell, cell_transf, rec_levels)

    def __set_parameters(self):
        schema = self.__class__.get_schema()
        for name, rules in schema.items():
            rules = normalize_rules(name, rules)
            self.param(
                rules["name"],
                rules["type"],
                rules["description"],
                hidden=rules["hidden"],
                readonly=rules["readonly"],
                unit=rules["unit"],
                default=rules["default"],
                choices=rules["choices"]
            )
