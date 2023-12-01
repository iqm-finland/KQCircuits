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


import json
from inspect import isclass

from kqcircuits.defaults import default_layers, default_faces, default_parameter_values
from kqcircuits.pya_resolver import pya, is_standalone_session
from kqcircuits.util.geometry_helper import get_cell_path_length
from kqcircuits.util.library_helper import load_libraries, to_library_name, to_module_name, element_by_class_name
from kqcircuits.util.parameters import Param, pdt
from kqcircuits.util.refpoints import Refpoints, WaveguideToSimPort


def get_refpoints(layer, cell, cell_transf=pya.DTrans(), rec_levels=None):
    """Returns Refpoints object for extracting reference points from given layer and cell.

    Args:
        layer: layer specification for source of refpoints
        cell: cell containing the refpoints
        cell_transf: transform for converting refpoints into target coordinate system
        rec_levels: recursion level when looking for refpoints from subcells. Set to 0 to disable recursion.

    Returns:
        Refpoints object, which behaves like dictionary, where keys are refpoints names, values are DPoints.

    """
    return Refpoints(layer, cell, cell_transf, rec_levels)


def insert_cell_into(target_cell, cell, trans=None, inst_name=None, label_trans=None, align_to=None, align=None,
                     rec_levels=0, **parameters):
    """Inserts a subcell into a given target cell.

    Note: This general method is useful to insert cells or elements into a static cell. To insert cells into an
    ``Element``, use the elements' ``insert_cell`` method, which has additional features such as parameter inheritance.

    It will use the given ``cell`` object or if ``cell`` is an Element class' name then directly
    take the provided keyword arguments to first create the cell object.

    If `inst_name` given, a label ``inst_name`` is added to labels layer at the ``base`` refpoint and `label_trans`
    transformation.

    Arguments:
        target_cell: Cell object to insert into
        cell: cell object or Element class name
        trans: used transformation for placement. None by default, which places the subcell into the coordinate
            origin of the parent cell. If `align` and `align_to` arguments are used, `trans` is applied to the
            `cell` before alignment transform which allows for example rotation of the `cell` before placement.
        inst_name: possible instance name inserted into subcell properties under `id`. Default is None
        label_trans: relative transformation for the instance name label
        align_to: ``DPoint`` or ``DVector`` location in parent cell coordinates for alignment of cell. Default is None
        align: name of the ``cell`` refpoint aligned to argument ``align_to``. Default is None
        rec_levels: recursion level when looking for refpoints from subcells. Set to 0 to disable recursion.
        **parameters: PCell parameters for the element, as keyword argument

    Return:
        tuple of placed cell instance and reference points with the same transformation
    """
    layout = target_cell.layout()
    if isclass(cell):
        cell = cell.create(layout, **parameters)

    if trans is None:
        trans = pya.DTrans()
    if (align_to and align) is not None:
        align = get_refpoints(layout.layer(default_layers["refpoints"]), cell, trans, rec_levels=rec_levels)[align]
        trans = pya.DCplxTrans(align_to - align) * trans

    cell_inst = target_cell.insert(pya.DCellInstArray(cell.cell_index(), trans))

    refpoints_abs = get_refpoints(layout.layer(default_layers["refpoints"]), cell, cell_inst.dcplx_trans, rec_levels)
    if inst_name is not None:
        cell_inst.set_property("id", inst_name)
        if label_trans is not None:
            label_trans_str = pya.DCplxTrans(label_trans).to_s()  # must be saved as string to avoid errors
            cell_inst.set_property("label_trans", label_trans_str)
    return cell_inst, refpoints_abs

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
    face_ids = Param(pdt.TypeList, "Chip face IDs list", ["1t1", "2b1", "1b1", "2t1"])
    display_name = Param(pdt.TypeString, "Name displayed in GUI (empty for default)", "")
    protect_opposite_face = Param(pdt.TypeBoolean, "Add opposite face protection too", False)
    opposing_face_id_groups = Param(pdt.TypeList, "Opposing face ID groups (list of lists)", [["1t1", "2b1"]],
                                    hidden=True)

    def __init__(self):
        ""
        super().__init__()

        cls = type(self)
        mro = cls.__mro__

        # We may need to redefine a Param object, because multiple classes may refer to the same Param object
        # due to inheritance, so modifying the existing Param object could affect other classes.
        def _redef_param(p, v, **kwargs):
            np = Param(p.data_type, p.description, v, **{**p.kwargs, **kwargs})
            np.__set_name__(cls, p.name)
            setattr(type(self), p.name, np)
            return np

        # Set and hide *_type parameter in classes inheriting from a * abstract class
        base = cls._get_abstract()
        if hasattr(base, "default_type") and getattr(base, "build") == getattr(Element, "build"):
            params = Param.get_all(base)
            mod = to_module_name(base.__name__)
            if f"{mod}_type" in params:
                subtype = to_library_name(cls.__name__)
                _redef_param(params[f"{mod}_type"], subtype, choices=[subtype], hidden=True)

        # create KLayout's PCellParameterDeclaration objects
        self._param_value_map = {}
        for name, p in cls.get_schema().items():
            self._param_value_map[name] = len(self._param_decls)
            # Override default value based on default_parameter_values if needed.
            for cl in mro:
                cls_name = cl.__qualname__
                if cls_name in default_parameter_values and name in default_parameter_values[cls_name]:
                    # Ensure that the `cl` default overrides the value only if it is not overridden
                    # by another class below `cl` in the hierarchy.
                    if cl != cls and cl.__dict__[name] != p:
                        break
                    p = _redef_param(p, default_parameter_values[cls_name][name])
                    break
            self._add_parameter(name, p.data_type, p.description, default=p.default, **p.kwargs)

    @staticmethod
    def create_cell_from_shape(layout, name):
        load_libraries(path=Element.LIBRARY_PATH)
        return layout.create_cell(name, Element.LIBRARY_NAME)

    @classmethod
    def create(cls, layout, library=None, **parameters) -> pya.Cell:
        """Create cell for this element in layout.

        Args:
            layout: pya.Layout object where this cell is created
            library: LIBRARY_NAME of the calling PCell instance
            **parameters: PCell parameters for the element as keyword arguments
        """
        cell = Element._create_cell(cls, layout, library, **parameters)
        setattr(cell, "length", lambda: get_cell_path_length(cell))
        return cell

    @classmethod
    def create_subtype(cls, layout, library=None, subtype=None, **parameters):
        """Create cell from an abstract class using the specified sub-class type.

        This is to be called from the ``create()`` function of abstract classes. It takes care of
        creating a code generated or a file based cell.

        Args:
            layout: pya.Layout object where this cell is created
            library: LIBRARY_NAME of the calling PCell instance
            subtype: name (str) of the desired sub-class of ``cls``
            **parameters: PCell parameters for the element as keyword arguments

        Return:
            tuple of the cell instance and a boolean indicating code generated cell
        """

        library_layout = (load_libraries(path=cls.LIBRARY_PATH)[cls.LIBRARY_NAME]).layout()

        if subtype is None:  # derive type from the class name
            subtype = to_library_name(cls.__name__)

        cl = cls._get_abstract()
        module = to_module_name(cl.__name__)
        pname = f"{module}_parameters"
        if pname in parameters:
            jp = dict(json.loads(parameters[pname]).items())
            del parameters[pname], parameters[f"_{pname}"]
            parameters = {**jp, **parameters}

        if subtype in library_layout.pcell_names():   # code generated
            pcell_class = type(library_layout.pcell_declaration(subtype))
            return Element._create_cell(pcell_class, layout, library, **parameters), True
        elif library_layout.cell(subtype):    # manually designed
            return layout.create_cell(subtype, cl.LIBRARY_NAME), False
        else:   # fallback is the default
            return cl.create_subtype(layout, library, cl.default_type, **parameters)

    @classmethod
    def create_with_refpoints(cls, layout, library=None, refpoint_transform=pya.DTrans(), rec_levels=None,
                              **parameters):
        """Convenience function to create cell and return refpoints too.

        Args:
            layout: pya.Layout object where this cell is created
            library: LIBRARY_NAME of the calling PCell instance
            refpoint_transform: transform for converting refpoints into target coordinate system
            rec_levels: recursion level when looking for refpoints from subcells. Set to 0 to disable recursion.
            **parameters: PCell parameters for the element, as keyword argument
        """
        cell = cls.create(layout, library, **parameters)
        refp = get_refpoints(layout.layer(default_layers["refpoints"]), cell, refpoint_transform, rec_levels)
        return cell, refp

    def add_element(self, cls, **parameters):
        """Create a new cell for the given element in this layout.

        Args:
            cls: Element subclass to be created
            **parameters: PCell parameters for the element as keyword arguments

        Returns:
           the created cell
        """
        parameters = self.pcell_params_by_name(cls, **parameters)
        return cls.create(self.layout, library=self.LIBRARY_NAME, **parameters)

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
            parameters = self.pcell_params_by_name(cell, **parameters)
            cell = cell.create(self.layout, library=self.LIBRARY_NAME, **parameters)

        if isinstance(align_to, str):
            align_to = self.refpoints[align_to]

        cell_inst, refpoints_abs = insert_cell_into(self.cell, cell, trans, inst_name, label_trans, align_to, align,
                                                    rec_levels, **parameters)

        if inst_name is not None:
            # copies probing refpoints to chip level with unique names using subcell id property
            for ref_name, pos in refpoints_abs.items():
                new_name = "{}_{}".format(inst_name, ref_name)
                self.refpoints[new_name] = pos
        return cell_inst, refpoints_abs

    def _resolve_face(self, face_id):
        """Returns face_id if the parameter is given as string or self.face_ids[face_id] otherwise.
        The face_id as a string must be a key in default_faces but does not necessarily need to be in self.face_ids.
        """
        return face_id if isinstance(face_id, str) else self.face_ids[face_id]

    def face(self, face_id=0):
        """Returns the face dictionary corresponding to face_id.

        The face dictionary contains key "id" for the face ID and keys for all the available layers in that face.

        Args:
            face_id: name or index of the face, default=0
        """
        return default_faces[self._resolve_face(face_id)]

    def pcell_params_by_name(self, cls=None, **parameters):
        """Give PCell parameters as a dictionary.

        Arguments:
            cls: Return only parameters present in this class. All by default.
            **parameters: Optionally update with other keyword arguments

        Returns:
            A dictionary of all PCell parameter names and corresponding current values.
        """
        keys = type(self).get_schema().keys()

        if cls is not None:  # filter keys by cls
            if Element.build == cls.build:  # Abstract class? Find subclass specified by *_type.
                cls = cls._get_abstract()
                mod_type = f"{to_module_name(cls.__name__)}_type"
                subtype = parameters[mod_type] if mod_type in parameters else getattr(self, mod_type, "")
                if subtype:
                    library_layout = (load_libraries(path=cls.LIBRARY_PATH)[cls.LIBRARY_NAME]).layout()
                    if subtype in library_layout.pcell_names():
                        cls = type(library_layout.pcell_declaration(subtype))
            keys = list(set(cls.get_schema().keys()) & set(keys))

        p = {k: self.__getattribute__(k) for k in keys if k != "refpoints"}
        return {**p, **parameters}

    def add_port(self, name, pos, direction=None, face_id=0):
        """ Add a port location to the list of reference points as well as ports layer for netlist extraction

        Args:
            name: name for the port. Will be "decorated" for annotation layer, left as is for port layer. If evaluates
                to False, it will be replaced with `port`
            pos: pya.DVector or pya.DPoint marking the position of the port in the Element base
            direction: direction of the signal going _to_ the port to determine the location of the "corner" reference
                point which is used for waveguide direction. If evaluates to False as is the default, no corner point is
                added.
            face_id: name or index of the face, default=0
        """
        text = pya.DText(name, pos.x, pos.y)
        self.cell.shapes(self.get_layer("ports", face_id)).insert(text)

        port_name = name if "port" in name else ("port_"+name if name else "port")
        self.refpoints[port_name] = pos
        if direction:
            self.refpoints[port_name+"_corner"] = pos+direction/direction.length()*self.r

    def copy_port(self, name, cell_inst, new_name=None):
        """ Copy a port definition from a different cell and instance; typically used to expose a specific subcell port.

        Args:
            name: Name of the port as it was specified to ``add_port``
            cell_inst: Instance of the cell, used to transform the port location correctly.
            new_name: Optionally rename the port
        """
        copy_name = name if new_name is None else new_name
        port_name = "port" if name == "" else f"port_{name}"
        port_corner_name = f"{port_name}_corner"

        # workaround for getting the cell due to KLayout bug, see
        # https://www.klayout.de/forum/discussion/1191/cell-shapes-cannot-call-non-const-method-on-a-const-reference
        # TODO: replace by `cell = cell_inst.cell` once KLayout bug is fixed (may be fixed in 0.27 but seems untested)
        cell = self.layout.cell(cell_inst.cell_index)

        cell_refpoints = self.get_refpoints(cell, cell_inst.dcplx_trans)
        for i in range(len(self.face_ids)):
            if "ports" in self.face(i):
                if name in get_refpoints(self.get_layer("ports", i), cell, cell_inst.dcplx_trans):
                    if port_corner_name in cell_refpoints:
                        self.add_port(copy_name, cell_refpoints[port_name],
                                      cell_refpoints[port_corner_name] - cell_refpoints[port_name], i)
                    else:
                        self.add_port(copy_name, cell_refpoints[port_name], face_id=i)
                    break

    @classmethod
    def get_schema(cls, noparents=False, abstract_class=None):
        """Returns the combined parameters of the class "cls" and all its ancestor classes.

        Args:
            noparents: If True then only return the parameters of "cls", not including ancestors.
            abstract_class: Return parameters up to this abstract class if specified.
        """
        schema = {}
        for pc in cls.__mro__:
            if not hasattr(pc, 'LIBRARY_NAME'):
                break
            schema = {**Param.get_all(pc), **schema}
            if noparents or abstract_class == pc:  # not interested in more parent classes
                break
        return schema

    def produce_impl(self):
        """This method builds the PCell.

        Adds all refpoints to user properties and draws their names to the annotation layer.
        """
        self.refpoints = {}

        # Put general "infrastructure actions" here, before build()
        self.refpoints["base"] = pya.DPoint(0, 0)

        self.build()

        self.post_build()

        for name, refpoint in self.refpoints.items():
            text = pya.DText(name, refpoint.x, refpoint.y)
            self.cell.shapes(self.get_layer("refpoints")).insert(text)

    def build(self):
        """Child classes re-define this method to build the PCell."""

    def post_build(self):
        """Child classes re-define this method for post-build operations"""

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
            face_id: Name or index of the face to use, default=0
        """
        if (face_id == 0) and (layer_name not in self.face(0)):
            return self.layout.layer(default_layers[layer_name])
        return self.layout.layer(self.face(face_id)[layer_name])

    @staticmethod
    def _create_cell(elem_cls, layout, library=None, **parameters) -> pya.Cell:
        """Create cell for elem_cls in layout.

        This is separated from the class method `create` to enable invocation from classes where `create` is shadowed.

        Args:
            elem_cls: element class for which the cell is created
            layout: pya.Layout object where this cell is created
            library: LIBRARY_NAME of the calling PCell instance
            **parameters: PCell parameters for the element as keyword arguments
        """
        cell_library_name = to_library_name(elem_cls.__name__)
        if elem_cls.LIBRARY_NAME == library:  # Matthias' workaround: https://github.com/KLayout/klayout/issues/905
            return layout.create_cell(cell_library_name, parameters)
        else:
            load_libraries(path=elem_cls.LIBRARY_PATH)
            return layout.create_cell(cell_library_name, elem_cls.LIBRARY_NAME, parameters)

    @classmethod
    def _get_abstract(cls):
        """Helper function to return ``cls``'s abstract class, if available, otherwise just return ``cls``."""
        if not hasattr(cls, "default_type"):
            return cls
        prev = cls
        abstract = cls.__bases__[0]
        while hasattr(abstract, "default_type"):
            prev = abstract
            abstract = prev.__bases__[0]
        return prev

    def _add_parameter(self, name, value_type, description,
                       default=None, unit=None, hidden=False, readonly=False, choices=None, docstring=None):
        """Creates a `pya.PCellParameterDeclaration` object and appends it to `self._param_decls`

        The arguments to this function define the PCellParameterDeclaration attributes with the same names,
        except:

            * `value_type` defines the `type` attribute
            * `docstring` is a more verbose parameter description, used in documentation generation.
            * `choices` argument is a list of `(description, value)` tuples. For convenience it also accepts
              self-describing, plain string elements, these will be converted to the expected tuple format.

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
                if  isinstance(choice, str):  # description-is-value shorthand
                    choice = (choice, choice)
                if len(choice) != 2:
                    raise ValueError("Each item in choices list/tuple must be a two-element array [description, value]")
                param_decl.add_choice(choice[0], choice[1])
        self._param_decls.append(param_decl)

    def raise_error_on_cell(self, error_msg, position=pya.DPoint()):
        """Replaces cell with error text in the annotation layer, and raises ValueError with the same error message.

        Args:
             error_msg: the error message
             position: location of the text center (optional)
        """
        self.cell.clear()
        error_text_cell = self.layout.create_cell("TEXT", "Basic", {
            "layer": default_layers["annotations"],
            "text": error_msg,
            "mag": 10.0
        })
        text_center = error_text_cell.bbox().center().to_dtype(self.layout.dbu)
        self.insert_cell(error_text_cell, pya.DTrans(position - text_center))
        raise ValueError(error_msg)

    def add_protection(self, shape, face_id=0):
        """Add ground grid protection shape

        Args:
             shape: The shape (Region, DPolygon, etc.) to add to ground_grid_avoidance layer
             face_id: Name or index of the primary face of ground_grid_avoidance layer, default=0
        """
        face = self._resolve_face(face_id)
        self.cell.shapes(self.get_layer("ground_grid_avoidance", face)).insert(shape)
        if self.protect_opposite_face:
            for group in self.opposing_face_id_groups:
                if face in group:
                    for other_face in group:
                        if other_face != face:
                            self.cell.shapes(self.get_layer("ground_grid_avoidance", other_face)).insert(shape)
                    break

    def sync_parameters(self, abc):
        """Syncronise the calling class' parameters with a JSON representation.

        This is called several times from coerce_parameters_impl() while using the PCell editor GUI. Particularly, each
        time a parameter of abc's sub-class is changed by the user. It figures out which parameter is changed and
        updates the ``*_parameters`` JSON strings accordingly, or the other way around.

        For example, if abc is Fluxline and the fluxline_width parameter is changed in GUI then the fluxline_parameters
        JSON string will be updated with this value. Or if fluxline_parameters string is changed then the corresponding
        fluxline parameter of the calling pcell is updated.

        Args:
            abc: An abstract class. Only consider parameters of this class' descendants
        """
        if is_standalone_session():
            return

        def pformat(a):
            if a.data_type == pdt.TypeInt:
                return int(a.default)
            elif a.data_type == pdt.TypeDouble:
                return float(a.default)
            return a.default

        module = to_module_name(abc.__name__)
        pname = f"{module}_parameters"
        json_str = getattr(self, pname)
        saved = getattr(self, f"_{pname}")
        params = json.loads(json_str) if json_str else {}
        subtype = getattr(self, f"{module}_type")
        pd = {}

        if subtype == "none":
            return
        if  json_str == "{}" or params[f"{module}_type"] != subtype:  # initialise defaults
            if f"{module}_type" in params and json_str != saved and saved != {}:
                subtype = params[f"{module}_type"]
                setattr(self, f"{module}_type", subtype)
            cls = element_by_class_name(subtype.replace(" ", ""), abc.LIBRARY_PATH, abc.LIBRARY_NAME)
            schema = cls.get_schema(abstract_class=abc)
            for k, v in schema.items():
                if not k.endswith("_parameters"):
                    pd[k] = getattr(self, k) if hasattr(self, k) else pformat(v)
            json_str = json.dumps(pd)
            setattr(self, pname, json_str)
            Param.get_all(abc)[pname].default = json_str
        elif saved == json_str:  # some parameters changed, update the JSON string
            for k, v in params.items():
                pd[k] = getattr(self, k) if hasattr(self, k) else v
            json_str = json.dumps(pd)
            setattr(self, pname, json_str)
        else:  # the JSON string changed, use it to update other parameters
            for k, v in params.items():
                if hasattr(self, k):
                    setattr(self, k, v)
        setattr(self, f"_{pname}", json_str)

    @classmethod
    def get_sim_ports(cls, simulation): # pylint: disable=unused-argument
        """List of RefpointToSimPort objects defining which refpoints
        should be turned to simulation ports for the given element class

        Returns empty list if not implemented for Element subclass.
        When implementing this method, the best practice is for this method
        to have no "side effects", that is all code contained within this method
        should only serve to derive the list of RefpointToSimPort objects and nothing
        else: no change in element's geometry or parameter values.

        Args:
            cls: Element class, this is a class method
            simulation: Simulation object where a cell of this element class is placed.
                Use this argument if you need to decide certain arguments
                for RefpointToSimPort objects based on simulation's parameters

        Returns:
            List of RefpointToSimPort objects, empty list by default
        """
        return []

    @staticmethod
    def left_and_right_waveguides(simulation):
        """A common implementation of get_sim_ports that adds left and right waveguides
        to port_a and port_b respectively. The a and b values of right waveguide
        can be adjusted separately.
        """
        a2 = simulation.a if simulation.a2 < 0 else simulation.a2
        b2 = simulation.b if simulation.b2 < 0 else simulation.b2
        return [WaveguideToSimPort("port_a", side='left', a=simulation.a, b=simulation.b),
                WaveguideToSimPort("port_b", side='right', a=a2, b=b2)]
