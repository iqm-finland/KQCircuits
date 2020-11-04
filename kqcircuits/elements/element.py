# Copyright (c) 2019-2020 IQM Finland Oy.
#
# All rights reserved. Confidential and proprietary.
#
# Distribution or reproduction of any information contained herein is prohibited without IQM Finland Oy’s prior
# written permission.

from kqcircuits.pya_resolver import pya
from autologging import logged, traced
from inspect import isclass

from kqcircuits.defaults import default_layers, default_circuit_params, default_faces
from kqcircuits.util.library_helper import load_libraries, to_library_name
from kqcircuits.util.parameter_helper import normalize_rules, Validator


@traced
def get_refpoints(layer, cell, cell_transf=pya.DTrans(), rec_levels=None):
    """Extract reference points from cell from layer as dictionary.

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


@traced
@logged
class Element(pya.PCellDeclarationHelper):
    """Base PCell declaration for elements.

    The PARAMETERS_SCHEMA class attribute defines the PCell parameters for an element. Notice, that to get the
    combined PARAMETERS_SCHEMA of the element and all its ancestors, you should use the "get_schema()" method instead
    of accessing PARAMETERS_SCHEMA directly.

    Elements have ports.
    """

    LIBRARY_NAME = "Element Library"
    LIBRARY_DESCRIPTION = "Superconducting quantum circuit library for elements."
    LIBRARY_PATH = "elements"

    PARAMETERS_SCHEMA = {
        "a": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Width of center conductor [μm]",
            "default": default_circuit_params["a"]
        },
        "b": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Width of gap [μm]",
            "default": default_circuit_params["b"]
        },
        "n": {
            "type": pya.PCellParameterDeclaration.TypeInt,
            "description": "Number of points on turns",
            "default": default_circuit_params["n"]
        },
        "r": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Turn radius [μm]",
            "default": default_circuit_params["r"]
        },
        "refpoints": {
            # such that child_element.produce function already would have the refpoints initialized
            # initializing it in the constructor of PCellDeclarationHelper child has no effect
            "type": pya.PCellParameterDeclaration.TypeNone,
            "description": "Reference points",
            "default": {"base": pya.DVector(0, 0)},
            "hidden": True
        },
        "margin": {
            "type": pya.PCellParameterDeclaration.TypeDouble,
            "description": "Margin of the protection layer [μm]",
            "default": 5
        },
        "face_ids": {
            "type": pya.PCellParameterDeclaration.TypeList,
            "description": "Chip face IDs, list of b | t | c",
            "default": ["b", "t", "c"],
        },
        "display_name": {
            "type": pya.PCellParameterDeclaration.TypeString,
            "description": "Name displayed in GUI (empty for default)",
            "default": "",
        },
    }

    def __init__(self):
        ""
        super().__init__()
        self.__set_parameters()

    @staticmethod
    def create_cell_from_shape(layout, name):
        load_libraries(path=Element.LIBRARY_PATH)
        return layout.create_cell(name, Element.LIBRARY_NAME)

    @classmethod
    def create(cls, layout, **parameters):
        """Create cell for this element in layout.

        Args:
            layout: pya.Layout object where this cell is created
            **parameters: PCell parameters for the element as keyword arguments
        """
        cell_library_name = to_library_name(cls.__name__)
        schema = cls.get_schema()
        validator = Validator(schema)
        if validator.validate(parameters):
            load_libraries(path=cls.LIBRARY_PATH)
            return layout.create_cell(cell_library_name, cls.LIBRARY_NAME, parameters)

    @classmethod
    def create_with_refpoints(cls, layout, refpoint_transform, **parameters):
        """Convenience function to create cell and return refpooints too.

        Args:
            layout: pya.Layout object where this cell is created
            refpoint_transform: transform for converting refpoints into target coordinate system
            **parameters: PCell parameters for the element, as keyword argument
        """
        cell = cls.create(layout, **parameters)
        refp = get_refpoints(layout.layer(default_layers["annotations"]), cell, refpoint_transform)
        return cell, refp

    def add_element(self, cls, whitelist=None, **parameters):
        """Create a new cell for the given element in this layout.

        Args:
            cls: Element subclass to be created
            whitelist: parameter dictionary where keys are used as a whitelist for passing
                       parameters of `self` to the `cls` cell used for parameter inheritance.
            **parameters: PCell parameters for the element as keyword arguments

        Returns:
           the created cell
        """
        if whitelist is not None:
            parameters = {**self.pcell_params_by_name(whitelist), **parameters}

        return cls.create(self.layout, **parameters)

    def insert_cell(self, cell, trans=None, inst_name=None, label_trans=None, align_to=None, align=None, rec_levels=0, **parameters):
        """Inserts a subcell into the present cell.

        It will use the given `cell` object or if `cell` is an Element class' name then directly
        take the provided keyword arguments to first create the cell object.

        If `inst_name` given, the refpoints of the cell are added to the `self.refpoints` with `inst_name` as a prefix,
        and also adds a label `inst_name` to "`"labels layer" at the `base` refpoint and `label_trans` transformation.

        Arguments:
            cell: cell object or Element class name
            trans: used transformation for placement. None by default, which places the subcell into the coordinate
                origin of the parent cell. If `align` and `align_to` arguments are used, `trans` is applied to the
                `cell` before alignment transform which allows for example rotation of the `cell` before placement.
            inst_name: possible instance name inserted into subcell properties under `id`. Default is None
            label_trans: relative transformation for the instance name label
            align_to: location in parent cell coordinates for alignment of cell. Can be either string indicating
                the parent refpoint name, `DPoint` or `DVector`. Default is None
            align: name of the `cell` refpoint aligned to argument `align_to`. Default is None
            rec_levels: recursion level when looking for refpoints from subcells. Set to 0 to disable recursion.
            **parameters: PCell parameters for the element, as keyword argument

        Return:
            tuple of placed cell instance and reference points with the same transformation
            """
        if isclass(cell):
            cell = cell.create(self.layout, **parameters)

        if trans is None:
            trans = pya.DTrans()
        if (align_to and align) is not None:
            align = self.get_refpoints(cell, trans)[align]
            if type(align_to) == str:
                align_to = self.refpoints[align_to]
            trans = pya.DTrans(align_to - align) * trans

        cell_inst = self.cell.insert(pya.DCellInstArray(cell.cell_index(), trans))

        refpoints_abs = self.get_refpoints(cell, cell_inst.dcplx_trans, rec_levels)  # should use .dtrans, if possible
        if inst_name is not None:
            cell_inst.set_property("id", inst_name)
            # copies probing refpoints to chip level with unique names using subcell id property
            for ref_name, pos in refpoints_abs.items():
                new_name = "{}_{}".format(inst_name, ref_name)
                self.refpoints[new_name] = pos
            if label_trans is not None:
                label_trans_str = pya.DCplxTrans(label_trans).to_s()  # must be saved as string to avoid errors
                cell_inst.set_property("label_trans", label_trans_str)
        return cell_inst, refpoints_abs

    def face(self, face_index=0):
        """Returns the face dictionary corresponding to self.face_ids[face_index].

        The face dictionary contains key "id" for the face ID and keys for all the available layers in that face.

        Args:
            face_index: index of the face_id in self.face_ids, default=0

        """
        return default_faces[self.face_ids[face_index]]

    def pcell_params_by_name(self, whitelist=None):
        """Give PCell parameters as a dictionary.

        Arguments:
            whitelist: list of dictionary for filtering the returned parameters. If dictionary, keys used for
            filtering.

        Returns:
            Dictionary with all parameter names in the PCell declaration `PARAMETER_SCHEMA` as keys and
            corresponding current values.
            """

        keys = self.__class__.get_schema().keys()
        if type(whitelist) is dict:
            keys = list(set(whitelist.keys()) & set(keys))
        return {k:self.__getattribute__(k) for k in keys}

    def add_port(self, name, pos, direction=None):
        """ Add a port location to the list of reference points as well as ports layer for netlist extraction

        Args
            name: name for the port. Will be "decorated" for annotation layer, left as is for port layer. If evaluates
            to False, it will be replaced with `port`
            pos: pya.DVector or pya.DPoint marking the position of the port in the Element base
            direction: direction of the signal going _to_ the port to determine the location of the "corner" reference
            point which is used for waveguide direction. If evaluates to False as is the default, no corner point is
            added.
        """
        text = pya.DText(name, pos.x, pos.y)
        self.cell.shapes(self.get_layer("ports")).insert(text)

        port_name = "port_"+name if name else "port"
        self.refpoints[port_name] = pos
        if direction:
            self.refpoints[port_name+"_corner"] = pos+direction/direction.length()*self.r

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
        """This method builds the PCell.

        Adds all refpoints to user properties and draws their names to the annotation layer.
        """
        for name, refpoint in self.refpoints.items():
            text = pya.DText(name, refpoint.x, refpoint.y)
            self.cell.shapes(self.get_layer("annotations")).insert(text)

    def display_text_impl(self):
        if self.display_name:
            return self.display_name
        return type(self).__name__

    def get_refpoints(self, cell, cell_transf=pya.DTrans(), rec_levels=None):
        """See `get_refpoints`."""
        return get_refpoints(self.layout.layer(default_layers["annotations"]), cell, cell_transf, rec_levels)

    def get_layer(self, layer_name, face_id=0):
        """Returns the specified Layer object.

        Args:
            layer_name: layer name text
            face_id: index of the face id, default=0

        """
        if (face_id == 0 and layer_name not in self.face(0)):
            return self.layout.layer(default_layers[layer_name])
        else:
            return self.layout.layer(self.face(face_id)[layer_name])

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
