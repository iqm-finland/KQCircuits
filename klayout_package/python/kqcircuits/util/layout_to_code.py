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
from kqcircuits.klayout_view import KLayoutView
from kqcircuits.pya_resolver import pya


def convert_cells_to_code(chip_cell, print_waveguides_as_composite=False, add_instance_names=True, refpoint_snap=50.0,
                          grid_snap=1.0, include_chip_code=True):

    """Prints out the Python code required to create the cells in chip_cell.

    For each instance that is selected in GUI, prints out an `insert_cell()` command that can be copy pasted to a chip's
    `build()`. If no instances are selected, then it will do the same for all instances that are one level below
    the chip cell in the cell hierarchy. PCell parameters are taken into account. Waveguide points can automatically be
    snapped to closest refpoints in the generated code.

    Args:
        chip_cell: cell whose child cells will be printed as code
        print_waveguides_as_composite: If true, then WaveguideCoplanar elements are printed as WaveguideComposite.
        add_instance_names: If true, then unique instance names will be added for each printed element. This is required
            if you want to have waveguides connect to refpoints of elements that were placed in GUI.
        refpoint_snap: If a waveguide point is closer than `refpoint_snap` to a refpoint, the waveguide point will be
            at that refpoint.
        grid_snap: If a waveguide point was not close enough to a refpoint, it will be snapped to a square grid with
            square side length equal to `grid_snap`
        include_chip_code: If true, also the code for the chip class is generated (including `build()` function
            and import statements) so that the printed code works as is. Otherwise only the code for inserted cells are
            printed, which must be copied to a chip's `build()` function.
    """

    layout = chip_cell.layout()

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
    layout_view = KLayoutView.get_active_cell_view().view()
    if len(layout_view.object_selection) > 0:
        for obj in layout_view.object_selection:
            if obj.is_cell_inst():
                add_instance(obj.inst())
    # Otherwise get all instances at one level below chip_cell.
    else:
        for inst in chip_cell.each_inst():
            add_instance(inst)

    # Order the instances according to cell type, x-coordinate, and y-coordinate
    instances = sorted(instances, key=lambda inst: (inst.cell.name, -inst.dtrans.disp.y, inst.dtrans.disp.x))
    pcell_classes = sorted(pcell_classes, key=lambda pcell_class: pcell_class.__module__)

    # Move all WaveguideCoplanar elements to the end of the list. This is required so that the refpoints from other
    # instances can be used as waveguide path points.
    # we can assume here that all WaveguideCoplanar are consecutive elements in the list due to the previous sorting
    wg_indices = [idx for idx, inst in enumerate(instances) if isinstance(inst.pcell_declaration(), WaveguideCoplanar)]
    if len(wg_indices) > 0:
        if wg_indices[-1] < len(instances) - 1:  # otherwise the waveguides are already at the end of instances list
            instances = \
                instances[:wg_indices[0]] + instances[wg_indices[-1]+1:] + instances[wg_indices[0]:wg_indices[-1]+1]

    # Add names to placed instances and create chip-level refpoints with those names
    if add_instance_names:
        for inst in instances:
            if inst.property("id") is None:
                inst_name = _get_unique_inst_name(inst, inst_names)
                inst_names.append(inst_name)
                inst.set_property("id", inst_name)
                inst_refpoints = get_refpoints(layout.layer(default_layers["refpoints"]), inst.cell, inst.dcplx_trans,
                                               0)
                for name, refpoint in inst_refpoints.items():
                    text = pya.DText(f"{inst_name}_{name}", refpoint.x, refpoint.y)
                    chip_cell.shapes(layout.layer(default_layers["refpoints"])).insert(text)

    # Get refpoints used for snapping waveguide points
    refpoints = get_refpoints(layout.layer(default_layers["refpoints"]), chip_cell)
    # only use refpoints of named instances
    refpoints = {name: point for name, point in refpoints.items() if name.startswith(tuple(inst_names))}

    def get_waveguide_code(inst, prefix, postfix, pcell_type, point_prefix, point_postfix="", refpoint_prefix="",
                           refpoint_postfix=""):
        path_str = prefix
        for path_point in inst.pcell_parameter("path").each_point():
            path_point += inst.dtrans.disp
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
                path_str += f"{refpoint_prefix}self.refpoints[\"{closest_refpoint_name}\"]{refpoint_postfix}, "
            else:
                x = grid_snap*round(path_point.x/grid_snap)
                y = grid_snap*round(path_point.y/grid_snap)
                path_str += f"{point_prefix}({x}, {y}){point_postfix}, "
        path_str = path_str[:-2]  # Remove extra comma and space
        path_str += postfix
        return f"self.insert_cell({pcell_type}, {path_str})\n"

    def transform_as_string(inst):
        trans = inst.dcplx_trans
        x, y = trans.disp.x, trans.disp.y
        if trans.mag == 1 and trans.angle%90 == 0:
            if trans.rot() == 0 and not trans.is_mirror():
                if x == 0 and trans.disp.y == 0:
                    return ""
                else:
                    return f", pya.DTrans({x}, {y})"
            else:
                return f", pya.DTrans({trans.rot()}, {trans.is_mirror()}, {x}, {y})"
        else:
            return f", pya.DCplxTrans({trans.mag}, {trans.angle}, {trans.is_mirror()}, {x}, {y})"

    generated_code = ""
    if include_chip_code:
        element_imports = ""
        for pcell_class in pcell_classes:
            element_imports += f"from {pcell_class.__module__} import {pcell_class.__name__}\n"
        generated_code += textwrap.dedent("""\
            from kqcircuits.chips.chip import Chip
            from kqcircuits.pya_resolver import pya\n\n""")
        generated_code += element_imports
        generated_code += textwrap.dedent("""\
            
    
            class NewChip(Chip):
            
                def build(self):\n\n""")

    # Print the Python code for creating each instance
    instances_code = ""
    for inst in instances:
        # Print python code for creating the instance at the given position
        cell = _get_cell(inst)
        pcell_declaration = inst.pcell_declaration()
        if pcell_declaration is not None:
            if isinstance(pcell_declaration, Element):
                # special handling for waveguides
                if isinstance(pcell_declaration, WaveguideCoplanar):
                    if print_waveguides_as_composite:
                        instances_code += \
                            get_waveguide_code(inst, prefix="nodes=[", postfix="]", pcell_type="WaveguideComposite",
                                               point_prefix="Node(", point_postfix=")", refpoint_prefix="Node(",
                                               refpoint_postfix=")")
                    else:
                        instances_code += \
                            get_waveguide_code(inst, prefix="path=pya.DPath([", postfix="], 0)",
                                               pcell_type=type(pcell_declaration).__name__, point_prefix="pya.DPoint")
                # other elements
                else:
                    inst_name = f", inst_name=\"{inst.property('id')}\"" if (inst.property('id') is not None) else ""
                    instances_code += \
                        f"self.insert_cell({type(pcell_declaration).__name__}{transform_as_string(inst)}{inst_name}" \
                        f"{_pcell_params_as_string(cell)})\n"
            else:
                # non-Element PCell
                instances_code += \
                    f"cell = self.layout.create_cell(\"{cell.name}\", \"{cell.library().name()}\", " \
                    f"{cell.pcell_parameters_by_name()})\n"
                instances_code += f"self.insert_cell(cell{transform_as_string(inst)})\n"

        else:
            # static cell
            generated_code += f"cell = self.layout.create_cell(\"{cell.name}\", \"{cell.library().name()}\")\n"
            generated_code += f"self.insert_cell(cell{transform_as_string(inst)})\n"

    if include_chip_code:
        generated_code += textwrap.indent(instances_code, "        ")
    else:
        generated_code = instances_code

    print(generated_code)


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
        if params[param_name] != param_declaration.default and param_name != "refpoints":
            param_value = params[param_name]
            if isinstance(param_value, str):
                param_value = f"\"{param_value}\""
            if isinstance(param_value, pya.DPoint):
                param_value = f"pya.DPoint({param_value})"
            params_str += f", {param_name}={param_value}"
    return params_str
