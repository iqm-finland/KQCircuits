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


from inspect import isclass

from autologging import logged, traced

from kqcircuits.defaults import default_layers, default_faces
from kqcircuits.pya_resolver import pya
from kqcircuits.util.geometry_helper import get_cell_path_length
from kqcircuits.util.library_helper import load_libraries, to_library_name
from kqcircuits.util.parameters import Param, pdt


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
    """Element PCell declaration.

    PCell parameters for an element are defined as class attributes of Param type.
    Elements have ports.
    """

    LIBRARY_NAME = "Element Library"
    LIBRARY_DESCRIPTION = "Superconducting quantum circuit library for elements."
    LIBRARY_PATH = "elements"

    a = Param(pdt.TypeDouble, "Width of center conductor", 10, unit="μm")
    b = Param(pdt.TypeDouble, "Width of gap", 6, unit="μm")
    n = Param(pdt.TypeInt, "Number of points on turns", 64)
    r = Param(pdt.TypeDouble, "Turn radius", 100, unit="μm")
    margin = Param(pdt.TypeDouble, "Margin of the protection layer", 5, unit="μm")
    face_ids = Param(pdt.TypeList, "Chip face IDs, list of b | t | c", ["b", "t", "c"])
    display_name = Param(pdt.TypeString, "Name displayed in GUI (empty for default)", "")
    # Initializing it in the constructor of PCellDeclarationHelper child has no effect so it has to
    # be a PCell parameter here.
    refpoints = Param(pdt.TypeNone, "Reference points", {"base": pya.DVector(0, 0)}, hidden=True)

    def __init__(self):
        ""
        super().__init__()

        # create KLayout's PCellParameterDeclaration objects
        self._param_value_map = {}
        for name, p in type(self).get_schema().items():
            self._param_value_map[name] = len(self._param_decls)
            self._add_parameter(name, p.data_type, p.description, default=p.default, **p.kwargs)

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
        cell = Element._create_cell(cls, layout, **parameters)
        if not cell.bbox_per_layer(layout.layer(default_layers['waveguide_length'])).empty():
            l = get_cell_path_length(cell, layout.layer(default_layers['waveguide_length']))
            setattr(cell, "length", lambda: l)
        return cell

    @classmethod
    def create_with_refpoints(cls, layout, refpoint_transform=pya.DTrans(), **parameters):
        """Convenience function to create cell and return refpoints too.

        Args:
            layout: pya.Layout object where this cell is created
            refpoint_transform: transform for converting refpoints into target coordinate system
            **parameters: PCell parameters for the element, as keyword argument
        """
        cell = cls.create(layout, **parameters)
        refp = get_refpoints(layout.layer(default_layers["refpoints"]), cell, refpoint_transform)
        return cell, refp

    def add_element(self, cls, whitelist=None, **parameters):
        """Create a new cell for the given element in this layout.

        Args:
            cls: Element subclass to be created
            whitelist: A classname. Its parameter names are used as a whitelist for passing
                       parameters of `self` to the `cls` cell.
            **parameters: PCell parameters for the element as keyword arguments

        Returns:
           the created cell
        """
        if whitelist is not None:
            parameters = {**self.pcell_params_by_name(whitelist), **parameters}

        return cls.create(self.layout, **parameters)

    def insert_cell(self, cell, trans=None, inst_name=None, label_trans=None, align_to=None, align=None, rec_levels=0,
                    **parameters):
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
            if isinstance(align_to, str):
                align_to = self.refpoints[align_to]
            trans = pya.DCplxTrans(align_to - align) * trans

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
            whitelist: A classname. Its parameter names are used for filtering.

        Returns:
            A dictionary of all PCell parameter names and corresponding current values.
        """
        keys = type(self).get_schema().keys()
        if whitelist is not None:
            keys = list(set(whitelist.get_schema().keys()) & set(keys))
        return {k: self.__getattribute__(k) for k in keys}

    def add_port(self, name, pos, direction=None):
        """ Add a port location to the list of reference points as well as ports layer for netlist extraction

        Args:
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
    def get_schema(cls, noparents=False):
        """Returns the combined parameters of the class "cls" and all its ancestor classes.

        Args:
            noparents: If True then only return the parameters of "cls", not including ancestors.
        """
        schema = {}
        for pc in cls.__mro__:
            schema = {**Param.get_all(pc), **schema}
            if noparents:   # not interested in parent classes
                break
        return schema

    def produce_impl(self):
        """This method builds the PCell.

        Adds all refpoints to user properties and draws their names to the annotation layer.
        """
        for name, refpoint in self.refpoints.items():
            text = pya.DText(name, refpoint.x, refpoint.y)
            self.cell.shapes(self.get_layer("refpoints")).insert(text)

    def display_text_impl(self):
        if self.display_name:
            return self.display_name
        return type(self).__name__

    def get_refpoints(self, cell, cell_transf=pya.DTrans(), rec_levels=None):
        """See `get_refpoints`."""
        return get_refpoints(self.layout.layer(default_layers["refpoints"]), cell, cell_transf, rec_levels)

    def get_layer(self, layer_name, face_id=0):
        """Returns the specified Layer object.

        Args:
            layer_name: layer name text
            face_id: index of the face id, default=0

        """
        if (face_id == 0) and (layer_name not in self.face(0)):
            return self.layout.layer(default_layers[layer_name])
        else:
            return self.layout.layer(self.face(face_id)[layer_name])

    @staticmethod
    def _create_cell(elem_cls, layout, **parameters):
        """Create cell for elem_cls in layout.

        This is separated from the class method `create` to enable invocation from classes where `create` is shadowed.

        Args:
            elem_cls: element class for which the cell is created
            layout: pya.Layout object where this cell is created
            **parameters: PCell parameters for the element as keyword arguments
        """
        cell_library_name = to_library_name(elem_cls.__name__)
        load_libraries(path=elem_cls.LIBRARY_PATH)
        return layout.create_cell(cell_library_name, elem_cls.LIBRARY_NAME, parameters)

    def _add_parameter(self, name, value_type, description,
                       default=None, unit=None, hidden=False, readonly=False, choices=None, docstring=None):
        """Creates a `pya.PCellParameterDeclaration` object and appends it to `self._param_decls`

        The arguments to this function define the PCellParameterDeclaration attributes with the same names,
        except:

            * `value_type` defines the `type` attribute
            * `docstring` is a more verbose parameter description, used in documentation generation.

        For TypeLayer parameters this also defines a `name_layer` read accessor for the layer index and modifies
        `self._layer_param_index` accordingly.
        """
        # pylint: disable=unused-argument

        # special handling of layer parameters
        if value_type == pya.PCellParameterDeclaration.TypeLayer:
            setattr(type(self), name + "_layer",
                    pya._PCellDeclarationHelperLayerDescriptor(len(self._layer_param_index)))
            self._layer_param_index.append(len(self._param_decls))

        # create the PCellParameterDeclaration and add to self._param_decls
        param_decl = pya.PCellParameterDeclaration(name, value_type, description, default, unit)
        param_decl.hidden = hidden
        param_decl.readonly = readonly
        if choices is not None:
            if not isinstance(choices, list) and not isinstance(choices, tuple):
                raise ValueError("choices must be a list or tuple.")
            for choice in choices:
                if len(choice) != 2:
                    raise ValueError("Each item in choices list/tuple must be a two-element array [description, value]")
                param_decl.add_choice(choice[0], choice[1])
        self._param_decls.append(param_decl)
