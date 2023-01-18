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

from sys import float_info
import textwrap

from kqcircuits.defaults import default_layers
from kqcircuits.elements.chip_frame import ChipFrame
from kqcircuits.elements.element import Element, get_refpoints
from kqcircuits.elements.waveguide_coplanar import WaveguideCoplanar
from kqcircuits.elements.waveguide_composite import WaveguideComposite, Node
from kqcircuits.util.parameters import pdt
from kqcircuits.pya_resolver import pya


def convert_cells_to_code(top_cell, print_waveguides_as_composite=False, add_instance_names=True, refpoint_snap=50.0,
                          grid_snap=1.0, output_format="insert_cell+chip", include_imports=True,
                          use_create_with_refpoints=True):

    """Prints out the Python code required to create the cells in top_cell.

    For each instance that is selected in GUI, prints out an `insert_cell()` command that can be copy pasted to a chip's
    `build()`. If no instances are selected, then it will do the same for all instances that are one level below
    the chip cell in the cell hierarchy. PCell parameters are taken into account. Waveguide points can automatically be
    snapped to closest refpoints in the generated code.

    Args:
        top_cell: cell whose child cells will be printed as code
        print_waveguides_as_composite: If true, then WaveguideCoplanar elements are printed as WaveguideComposite.
        add_instance_names: If true, then unique instance names will be added for each printed element. This is required
            if you want to have waveguides connect to refpoints of elements that were placed in GUI.
        refpoint_snap: If a waveguide point is closer than `refpoint_snap` to a refpoint, the waveguide point will be
            at that refpoint.
        grid_snap: If a waveguide point was not close enough to a refpoint, it will be snapped to a square grid with
            square side length equal to `grid_snap`
        output_format: Determines the format of the code for placing cells and if some extra code is printed. Has the
            following options:

            * "insert_cell": only insert_cell() calls which can be copied to existing chip's/element's build method
            * "insert_cell+chip": same as previous, but prints also the chip code, can copy to empty file to create
              new chip
            * "create": only create() and cell.insert() calls which can be copied to an existing macro with layout
              and top_cell
            * "create+macro": same as previous, but includes initial lines for macro, can copy to empty file to
              create new macro

        include_imports: If true, then import statements for all used elements are included in the generated code
        use_create_with_refpoints: If true, then create_with_refpoints() is used instead of create(). Only used when
            output_format is "create" or "create+macro". Required if you want to use refpoints as waveguide points.

    Returns:
        str: The generated Python code. This is also printed.
    """

    layout = top_cell.layout()

    instances = []
    inst_names = []
    pcell_classes = set()

    def add_instance(inst):
        cell = _get_cell(inst)
        inst_name = inst.property('id')
        pcell_decl = inst.pcell_declaration()
        # ChipFrame is always constructed by Chip, so we don't want to generate code for it
        if isinstance(pcell_decl, ChipFrame):
            return
        # Instance name labels are generated based on element instance names, we don't want to create them explicitly
        if cell.name == "TEXT":
            return
        instances.append(inst)
        if inst_name is not None:
            inst_names.append(inst_name)
        if pcell_decl is not None:
            pcell_classes.add(pcell_decl.__class__)

    # If some instances are selected, then we are only going to export code for them
    cell_view = pya.CellView.active() if hasattr(pya, "CellView") else None
    if cell_view and cell_view.is_valid() and len(cell_view.view().object_selection) > 0:
        for obj in cell_view.view().object_selection:
            if obj.is_cell_inst():
                add_instance(obj.inst())
    # Otherwise get all instances at one level below top_cell.
    else:
        for inst in top_cell.each_inst():
            add_instance(inst)

    # Order the instances according to cell type, x-coordinate, and y-coordinate
    instances = sorted(instances, key=lambda inst: (inst.cell.name, -inst.dtrans.disp.y, inst.dtrans.disp.x))
    pcell_classes = sorted(pcell_classes, key=lambda pcell_class: pcell_class.__module__)

    # Move all WaveguideComposite and WaveguideCoplanar elements to the end of the list. This is required so that the
    # refpoints from other instances can be used as waveguide path points. We can assume here that all
    # WaveguideComposite and WaveguideCoplanar are consecutive elements in the list due to the previous sorting
    instances = _move_to_end(instances, WaveguideComposite)
    instances = _move_to_end(instances, WaveguideCoplanar)

    # Add names to placed instances and create chip-level refpoints with those names
    if add_instance_names:
        for inst in instances:
            if inst.property("id") is None and \
                    not isinstance(inst.pcell_declaration(), (WaveguideComposite, WaveguideCoplanar)):
                inst_name = _get_unique_inst_name(inst, inst_names)
                inst_names.append(inst_name)
                inst.set_property("id", inst_name)
                inst_refpoints = get_refpoints(layout.layer(default_layers["refpoints"]), inst.cell, inst.dcplx_trans,
                                               0)
                for name, refpoint in inst_refpoints.items():
                    text = pya.DText(f"{inst_name}_{name}", refpoint.x, refpoint.y)
                    top_cell.shapes(layout.layer(default_layers["refpoints"])).insert(text)

    # Get refpoints used for snapping waveguide points
    refpoints = get_refpoints(layout.layer(default_layers["refpoints"]), top_cell)
    # only use refpoints of named instances
    refpoints = {name: point for name, point in refpoints.items() if name.startswith(tuple(inst_names))}

    # Generate code for importing the used element. More element imports may be added later when generating code from
    # waveguide nodes.
    element_imports = ""
    if include_imports:
        for pcell_class in pcell_classes:
            element_imports += f"from {pcell_class.__module__} import {pcell_class.__name__}\n"
        if print_waveguides_as_composite or WaveguideComposite in pcell_classes:
            element_imports += f"from {WaveguideComposite.__module__} import {Node.__name__}\n"

    def get_waveguide_code(inst, prefix, postfix, pcell_type, point_prefix, point_postfix="", refpoint_prefix="",
                           refpoint_postfix=""):
        path_str = prefix

        wg_points = []
        nodes = None
        _params = inst.pcell_parameters_by_name()
        if type(inst.pcell_declaration()).__name__ == "WaveguideCoplanar":
            wg_points = _params.pop("path").each_point()
        else:
            nodes = Node.nodes_from_string(_params.pop("nodes"))
            for node in nodes:
                wg_points.append(node.position)

        wg_params = ""  # non-default parameters of the cell
        for k, v in inst.pcell_declaration().get_schema().items():
            if k in _params and v.data_type != pdt.TypeShape and _params[k] != v.default:
                wg_params += f",  {k}={_params[k]}"

        for i, path_point in enumerate(wg_points):
            path_point += inst.dtrans.disp
            x_snapped = grid_snap*round(path_point.x/grid_snap)
            y_snapped = grid_snap*round(path_point.y/grid_snap)
            node_params = ""
            if nodes is not None:
                node_params, node_elem = get_node_params(nodes[i])
                if node_elem is not None and include_imports:
                    nonlocal element_imports
                    node_elem_import = f"from {node_elem.__module__} import {node_elem.__name__}\n"
                    if node_elem_import not in element_imports:
                        element_imports += node_elem_import

            # If a refpoint is close to the path point, snap the path point to it
            closest_dist = float_info.max
            closest_refpoint_name = None
            for name, point in refpoints.items():
                dist = point.distance(path_point)
                if dist <= closest_dist and dist < refpoint_snap:
                    # If this refpoint is at exact same position as closest_refpoint, compare also refpoint names.
                    # This should ensure that chip-level refpoints are chosen over lower-level refpoints.
                    if dist < closest_dist or (len(name) > len(closest_refpoint_name)):
                        closest_dist = dist
                        closest_refpoint_name = name
            if closest_refpoint_name is not None:
                if output_format.startswith("insert_cell"):
                    path_str += f"{refpoint_prefix}self.refpoints[\"{closest_refpoint_name}\"]{node_params}" \
                                f"{refpoint_postfix}, "
                elif use_create_with_refpoints:
                    refp_split = closest_refpoint_name.split("_")
                    refp_name = "_".join(refp_split[1:])
                    path_str += f"{refpoint_prefix}{refp_split[0].replace('-', '_')}_refpoints[\"{refp_name}\"]" \
                                f"{node_params}{refpoint_postfix}, "
                else:
                    path_str += f"{point_prefix}({x_snapped}, {y_snapped}){node_params}{point_postfix}, "
            else:
                path_str += f"{point_prefix}({x_snapped}, {y_snapped}){node_params}{point_postfix}, "
        path_str = path_str[:-2]  # Remove extra comma and space
        path_str += postfix + wg_params
        if output_format.startswith("insert_cell"):
            return f"self.insert_cell({pcell_type}, {path_str})\n"
        else:
            return f"view.insert_cell({pcell_type}, {path_str})\n"

    def transform_as_string(inst):
        trans = inst.dcplx_trans
        x, y = trans.disp.x, trans.disp.y
        if trans.mag == 1 and trans.angle % 90 == 0:
            if trans.rot() == 0 and not trans.is_mirror():
                if x == 0 and trans.disp.y == 0:
                    return ""
                else:
                    return f"pya.DTrans({x}, {y})"
            else:
                return f"pya.DTrans({trans.rot()}, {trans.is_mirror()}, {x}, {y})"
        else:
            return f"pya.DCplxTrans({trans.mag}, {trans.angle}, {trans.is_mirror()}, {x}, {y})"

    # Generate the code for creating each instance
    instances_code = ""
    for inst in instances:
        # Print python code for creating the instance at the given position
        cell = _get_cell(inst)
        transform = transform_as_string(inst)
        pcell_declaration = inst.pcell_declaration()
        if pcell_declaration is not None:
            if isinstance(pcell_declaration, Element):
                pcell_type = type(pcell_declaration).__name__
                # special handling for waveguides
                if isinstance(pcell_declaration, (WaveguideComposite, WaveguideCoplanar)):
                    if print_waveguides_as_composite or isinstance(pcell_declaration, WaveguideComposite):
                        instances_code += \
                            get_waveguide_code(inst, prefix="nodes=[", postfix="]", pcell_type="WaveguideComposite",
                                               point_prefix="Node(", point_postfix=")", refpoint_prefix="Node(",
                                               refpoint_postfix=")")
                    else:
                        instances_code += \
                            get_waveguide_code(inst, prefix="path=pya.DPath([", postfix="], 0)",
                                               pcell_type=pcell_type, point_prefix="pya.DPoint")
                # other elements
                else:
                    inst_name = inst.property('id') if (inst.property('id') is not None) else ""
                    var_name = inst_name.replace("-", "_")
                    transform_nonempty = transform if transform != "" else "pya.DTrans()"
                    if output_format.startswith("insert_cell"):
                        inst_name = f"inst_name=\"{inst_name}\"" if (inst_name != "") else ""
                        inst_name = f", {inst_name}" if transform != "" else inst_name
                        instances_code += \
                            f"self.insert_cell({pcell_type}, {transform}{inst_name}{_pcell_params_as_string(cell)})\n"
                    elif use_create_with_refpoints:
                        refpoint_transform = f"refpoint_transform={transform}, " if transform != "" else ""
                        instances_code += \
                            f"{var_name}, {var_name}_refpoints = {pcell_type}.create_with_refpoints(layout, " \
                            f"{refpoint_transform}rec_levels=0{_pcell_params_as_string(cell)})\n"
                        instances_code += f"view.insert_cell({var_name}, {transform_nonempty})\n"
                    else:
                        instances_code += \
                            f"{var_name} = {pcell_type}.create(layout{_pcell_params_as_string(cell)})\n"
                        instances_code += f"view.insert_cell({var_name}, {transform_nonempty})\n"
            else:
                # non-Element PCell
                if output_format.startswith("insert_cell"):
                    instances_code += \
                        f"cell = self.layout.create_cell(\"{cell.name}\", \"{cell.library().name()}\", " \
                        f"{cell.pcell_parameters_by_name()})\n"
                    instances_code += f"self.insert_cell(cell, {transform})\n"
                else:
                    instances_code += \
                        f"cell = layout.create_cell(\"{cell.name}\", \"{cell.library().name()}\", " \
                        f"{cell.pcell_parameters_by_name()})\n" \
                        f"view.insert_cell(cell, {transform})\n"

        else:
            # static cell
            if output_format.startswith("insert_cell"):
                instances_code += f"cell = self.layout.create_cell(\"{cell.name}\", \"{cell.library().name()}\")\n"
                instances_code += f"self.insert_cell(cell, {transform})\n"
            else:
                instances_code += f"cell = layout.create_cell(\"{cell.name}\", \"{cell.library().name()}\")\n"
                instances_code += f"view.insert_cell(cell, {transform})\n"

    # Generate code for the beginning of the chip or macro file if needed
    start_code = ""
    if output_format == "insert_cell+chip":
        start_code += textwrap.dedent("""\
            from kqcircuits.pya_resolver import pya
            from kqcircuits.chips.chip import Chip\n\n""")
        start_code += element_imports + "\n"
        start_code += textwrap.dedent("""\

            class NewChip(Chip):

                def build(self):\n\n""")
    elif output_format == "create+macro":
        start_code += "from kqcircuits.pya_resolver import pya\n"
        start_code += "from kqcircuits.klayout_view import KLayoutView\n\n"
        start_code += element_imports + "\n"
        start_code += "view = KLayoutView()\n"
        start_code += "layout = view.layout\n\n"
    else:
        start_code += element_imports + "\n"

    if output_format == "insert_cell+chip":
        full_code = start_code + textwrap.indent(instances_code, "        ") + "\n"
    else:
        full_code = start_code + instances_code

    return full_code


def _get_cell(inst):
    # workaround for getting the cell due to KLayout bug, see
    # https://www.klayout.de/forum/discussion/1191/cell-shapes-cannot-call-non-const-method-on-a-const-reference
    # TODO: replace by `inst.cell` once KLayout bug is fixed
    return inst.layout().cell(inst.cell_index)


def _get_unique_inst_name(inst, inst_names):
    idx = 1
    inst_name = type(inst.pcell_declaration()).__name__ + str(idx)
    while inst_name in inst_names:
        idx += 1
        inst_name = type(inst.pcell_declaration()).__name__ + str(idx)
    return inst_name


def _pcell_params_as_string(cell):
    params = cell.pcell_parameters_by_name()
    params_schema = type(cell.pcell_declaration()).get_schema()
    params_str = ""
    for param_name, param_declaration in params_schema.items():
        if (params[param_name] != param_declaration.default and param_name != "refpoints"
                and not (param_name.startswith("_") and param_name.endswith("_parameters"))):
            param_value = params[param_name]
            if isinstance(param_value, str):
                param_value = repr(param_value)
            if isinstance(param_value, pya.DPoint):
                param_value = f"pya.DPoint({param_value})"
            params_str += f", {param_name}={param_value}"
    return params_str


def _move_to_end(instances, pcell_type):
    """Returns `instances` list where instances of `pcell_type` are at the end

    Assumes that all `pcell_type` instances are consecutive elements of the list.
    """
    wg_indices = [idx for idx, inst in enumerate(instances) if isinstance(inst.pcell_declaration(), pcell_type)]
    if len(wg_indices) > 0:
        if wg_indices[-1] < len(instances) - 1:  # otherwise the waveguides are already at the end of instances list
            instances = \
                instances[:wg_indices[0]] + instances[wg_indices[-1] + 1:] + instances[wg_indices[0]:wg_indices[-1] + 1]
    return instances


def get_node_params(node: Node):
    """
    Generate a list of parameters for Node in string form

    Args:
        node: a Node to convert

    Returns: a tuple (node_params, element) where
        node_params: string of comma-separated key-value pairs that can be passed to the initializer of Node,
        starting with ``", "``
        element: class that implements the node's element, or None if the node has no element
    """
    node_params = ""
    elem = None
    for k, v in vars(node).items():
        if k == "element" and v is not None:
            node_params += f", {v.__name__}"
            elem = v
        elif (k == "inst_name" and v is not None) or \
                (k == "align" and v != tuple()) or \
                (k == "angle" and v is not None) or \
                (k == "length_before" and v is not None) or \
                (k == "length_increment" and v is not None):
            node_params += f", {k}={repr(v)}"
        elif k == "params":
            # Expand keyword arguments to Node
            for kk, vv in v.items():
                node_params += f", {kk}={repr(vv)}"
    return node_params, elem
