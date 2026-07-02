# This code is part of KQCircuits
# Copyright (C) 2024 IQM Finland Oy
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
# (meetiqm.com/iqm-open-source-trademark-policy). IQM welcomes contributions to the code.
# Please see our contribution agreements for individuals (meetiqm.com/iqm-individual-contributor-license-agreement)
# and organizations (meetiqm.com/iqm-organization-contributor-license-agreement).

"""
Functions to tune and replace junctions in existing design files.

See scripts/macros/export/export_tuned_junctions.lym for a use case of these functions
"""

from typing import Dict, List
import logging
from kqcircuits.defaults import default_layers, default_faces
from kqcircuits.elements.element import get_refpoints
from kqcircuits.pya_resolver import pya
from kqcircuits.util.load_save_layout import save_layout
from kqcircuits.junctions import junction_type_choices
from kqcircuits.junctions.junction import Junction
from kqcircuits.util.library_helper import load_libraries, to_library_name


class JunctionEntry:
    """All junction properties we want to store when extracting junctions"""

    def __init__(
        self,
        class_type: type,
        trans: pya.DCplxTrans,
        trans_path: List[pya.DCplxTrans],
        parameters: Dict,
        parent_name: str,
        name: str,
        refpoints: dict,
    ) -> None:
        self.type = class_type
        self.trans = trans
        self.trans_path = trans_path
        self.parameters = parameters
        self.parent_name = parent_name
        self.name = name
        self.refpoints = refpoints

    def __eq__(self, __value: object) -> bool:
        return (
            self.type == __value.type
            and self.trans == __value.trans
            and self.parameters == __value.parameters
            and self.parent_name == __value.parent_name
            and self.name == __value.name
        )


def _check_junction_names_unique(junctions):
    """Raises exception if ``junctions`` contains a non-unique (parent_name, name) key-pair"""
    unique_names = set()
    for junction in junctions:
        if (junction.parent_name, junction.name) in unique_names:
            error_text = (
                "Following cell parent name and child name is not unique in top cell: "
                f"{(junction.parent_name, junction.name)}. "
                "Something seems to be wrong with KQC generated cell"
            )
            logging.error(error_text)
            raise ValueError(error_text)
        unique_names.add((junction.parent_name, junction.name))


def _check_missing_junction_parameters(
    junction_class_name, junction_schema_errors, params, tuned_params, parent_name, name
):
    """Run for every found junction to compare junction library schema (`params`)
    and schema as given in json file (`tuned_params`).

    If some parameter keys are missing in `tuned_params`, stores missing keys in mutable `junction_schema_errors`.
    `junction_schema_errors` is a dict that has junction class as keys, and as values
    a tuple "missing_fields" with dict of missing parameters + their default values, and a list for junction names.

    Note that some parameter keys are ignored.
    """
    ignore_param_keys = {
        "_junction_parameters",
        "junction_parameters",
        "display_name",
        "_epr_show",
        "_epr_cross_section_cut_width",
        "_epr_cross_section_cut_layer",
        "_epr_cross_section_cut",
        "_epr_counter",
    }
    if junction_class_name not in junction_schema_errors:
        junction_schema_errors[junction_class_name] = {"missing_fields": ({}, []), "surplus_fields": (set(), [])}
    missing_keys = set(params.keys()).difference(set(tuned_params.keys())).difference(ignore_param_keys)
    missing_fields = {k: params[k] for k in missing_keys}
    junction_schema_errors[junction_class_name]["missing_fields"][0].update(missing_fields)
    if len(missing_fields) > 0:
        junction_schema_errors[junction_class_name]["missing_fields"][1].append((parent_name, name))


def _check_surplus_junction_parameters(
    junction_class_name, junction_schema_errors, params, tuned_params, parent_name, name
):
    """Run for every found junction to compare junction library schema (`params`)
    and schema as given in json file (`tuned_params`).

    If some parameter keys are in `tuned_params` but not in `params`,
    stores missing keys in mutable `junction_schema_errors`.
    `junction_schema_errors` is a dict that has junction class as keys, and as values
    a tuple "surplus_fields" with set of surplus parameter keys and a list for junction names.
    """
    if junction_class_name not in junction_schema_errors:
        junction_schema_errors[junction_class_name] = {"missing_fields": ({}, []), "surplus_fields": (set(), [])}
    surplus_fields = set(tuned_params.keys()).difference(set(params.keys()))
    junction_schema_errors[junction_class_name]["surplus_fields"][0].update(surplus_fields)
    if len(surplus_fields) > 0:
        junction_schema_errors[junction_class_name]["surplus_fields"][1].append((parent_name, name))


def _print_surplus_junction_parameters(junction_schema_errors):
    """Logs as warning the content of "surplus_fields" in `junction_schema_errors`,
    which are junction parameters that were attempted to be tuned,
    yet were not defined for the given junction types.
    """
    for k, v in junction_schema_errors.items():
        surplus_fields, junctions = v["surplus_fields"]
        if len(surplus_fields) > 0:
            logging.warning(
                (
                    f"{k} class junction attempted to be tuned with parameters "
                    f"that are not part of the class: {surplus_fields}"
                )
            )
            logging.warning(f"for {junctions[:5]}\n")


def _handle_missing_junction_parameters(junction_schema_errors, is_pcell, halt):
    """Format a message to show all missing parameter keys detected for each junction type
    and names the affected junctions, for entries where `junction_schema_errors` is not empty.

    If `halt` is True, raises an exception if missing parameters are found.
    Otherwise logs a warning.
    """
    error_text = ""
    for k, v in junction_schema_errors.items():
        missing_fields, junctions = v["missing_fields"]
        if len(missing_fields) > 0:
            missing_fields_report = set(missing_fields.keys()) if halt else missing_fields
            error_text = (
                f"{error_text}"
                f"{k} class junction parameters missing {missing_fields_report}\n"
                f"missing for {junctions[:5]}\n\n"
            )
    if len(error_text) > 0:
        if halt:
            error_text = (
                (
                    "Since junction type was changed for some junctions, "
                    "the tuned junction json should give value at least for parameters "
                    "that are in new junction type but not in old junction type.\n"
                    f"Following junction parameters missing:\n\n{error_text}"
                )
                if is_pcell
                else (
                    "Since the cell doesn't contain pre-existing PCell parameter data, "
                    "the tuned junction json should be exhaustive.\n"
                    f"Following junction parameters missing:\n\n{error_text}"
                )
            )
            logging.error(error_text)
            raise ValueError("Some junction parameters were missing in the tuning json, see log for details")
        # halt=False, only log errors but don't raise
        logging.warning(
            "Following junction parameters were missing in tuned junction json, "
            f"which were replaced with following default values:\n\n{error_text}"
        )


def _transformation_for_junction_face(
    top_cell: pya.Cell, junction_face_ids: list[str], old_translation: bool = False
) -> pya.DCplxTrans:
    """Returns chip level transformation to apply to junctions and any other layout
    exported with the junctions. Relies on orientation of corner markers to determine
    whether chip geometry should be mirrored or not.

    Translates the chip so that bottom-left corner is at origin.
    If `old_translation` set to True, will leave the translation alone,
    only taking care of mirroring if needed.

    Args:
        top_cell: Main chip cell containing the junctions
        junction_face_ids: ``face_ids`` value of some junction,
            assumed that all junctions exist on same face

    Returns:
        pya.DCplxTrans to apply to every shape in the chip
    """
    layout = top_cell.layout()
    face = junction_face_ids[0]
    biggest_bbox, this_bbox = None, pya.DBox(0, 0, 0, 0)
    # Pick largest chip frame
    for l in layout.layer_infos():
        if l.name.endswith("_base_metal_gap_wo_grid") or l.name.endswith("*base*metal*gap*wo*grid"):
            bb = top_cell.dbbox_per_layer(layout.layer(l))
            if l.name.startswith(face) and not old_translation:
                this_bbox = bb
            if not biggest_bbox or biggest_bbox.width() < bb.width():
                biggest_bbox = bb
    refpoints = get_refpoints(layout.layer(default_layers["refpoints"]), top_cell)
    chip_is_mirrored = refpoints[f"{face}_marker_se"].x < refpoints[f"{face}_marker_sw"].x
    if chip_is_mirrored:
        # Mirror by Y-axis = mirror by X-axis * rotate 180 degrees
        # Then need to shift the chip back so left and right edges of mirrored chip
        # is same as edges of original chip. Why bbox.p1.x + bbox.p2.x?
        # Mirror by Y-axis (without translation) means bbox_1.p1.x = -bbox_0.p1.x
        # For final translated bbox_2 we want
        # bbox_2.p1.x = bbox_0.p2.x and bbox_2.p2.x = bbox_0.p1.x
        # Solve for y in bbox_2.p1.x = bbox_1.p1.x + y = -bbox_0.p1.x + y = bbox_0.p2.x
        # and bbox_2.p2.x = ... = -bbox_0.p2.x + y = bbox_0.p1.x
        # to get y = bbox_0.p1.x + bbox_0.p2.x
        return pya.DCplxTrans(
            pya.DTrans(2, True, biggest_bbox.p1.x + biggest_bbox.p2.x - this_bbox.p1.x, -this_bbox.p1.y)
        )
    # Chip not mirrored, return identity transformation
    return pya.DCplxTrans()


def _static_junction_is_on_face(junction_cell: pya.Cell, face: str):
    """Returns true if `junction_cell` is placed at `face`.

    Intended to use on static cells. Assumes no multiface junctions.
    """
    return any(
        not junction_cell.dbbox(junction_cell.layout().layer(l)).empty()
        for layer_name, l in default_faces[face].items()
        if layer_name.startswith("SIS_")
    )


def extract_junctions(
    top_cell: pya.Cell,
    tuned_junction_parameters: Dict,
    halt_on_missing_params: bool = True,
    check_paramset: bool = True,
    old_translation: bool = False,
) -> List[JunctionEntry]:
    """Extracts all junction elements placed in the `top_cell`.
    Junction parameters are tuned according to `tuned_junction_parameters` dict.

    `tuned_junction_parameters` is a dict with junction's parent cell name as key,
    where parent cell is an element that contains the junction, e.g. "QB1", "testarray_nw" etc.
    The value is also a dict, with junction cell's name as key, e.g "squid", "squid_0", "squid_3" etc.
    For example testarray cells may have multiple junction cells.
    Then `tuned_junction_parameters[parent_name][name]` is a dict of junction parameters.

    If `top_cell` has pcell data, the parameter values that are missing in `tuned_junction_parameters`
    can be inferred from the Junction PCell's values. So `tuned_junction_parameters` may only contain
    parameter values that are different from how junctions were defined in `top_cell`.
    If "junction_type" in `tuned_junction_parameters` is changed from `top_cell`,
    then `tuned_junction_parameters` should also include parameters exclusive
    to new "junction_type".

    If `top_cell` has no pcell data, `tuned_junction_parameters` must include all parameter keys
    of the junction parameter schema for each junction contained in the `top_cell`,
    even if the parameter values are the same as were used to construct `top_cell`.
    If that is not the case, then depending on `halt_on_missing_params` argument,
    `extract_junctions` will either raise an exception, or simply print a warning.

    To prevent parameter schema checking, set `check_paramset` to False. This could be
    useful if you're only interested in junction locations.

    Junctions will be transformed such that the chip face where the junctions preside is facing the viewer.
    For some chips this means that the layout gets mirrored. By default, mirrored chip is also
    translated so that bottom left corner is at origin. If `old_translation` is set to True,
    it will leave chip translation in place, only performing mirroring.

    Returns a list of `JunctionEntry` objects that can be used to place the extracted junctions
    into another cell that has tuned parameters but is otherwise identical in shape, placement and orientation.

    Junction type may also be changed, if `junction_type` is tuned to have some other junction class name.
    For every junction that has its `junction_type` changed, even if the cell contains PCell data,
    `tuned_junction_parameters` should have at least all parameters present that are in the new junction type
    but not in the old junction type.
    """
    junction_schema_errors = {}
    found_junctions = []
    library_layout = (load_libraries(path=Junction.LIBRARY_PATH)[Junction.LIBRARY_NAME]).layout()
    layout = top_cell.layout()
    is_pcell = False
    for i in top_cell.each_inst():
        if i.pcell_declaration() is not None:
            is_pcell = True
            break

    def recursive_junction_search(inst, parent_name, prev_trans, trans_path):
        cell = layout.cell(inst.cell_index)
        name = inst.property("id")
        trans = prev_trans * inst.dcplx_trans
        tuned_params = tuned_junction_parameters.get(parent_name, {}).get(name, {})
        if is_pcell:
            pcell = inst.pcell_declaration()
            is_junction = pcell and isinstance(pcell, Junction)
        else:
            cell_class_from_name = cell.name.split("$")[0].replace("*", " ")
            pcell = library_layout.pcell_declaration(cell_class_from_name)
            is_junction = cell_class_from_name in junction_type_choices
        if is_junction:
            pcell_param_values = {}
            if is_pcell:
                # Parameter values present in PCell data can be reused
                pcell_param_values = inst.pcell_parameters_by_name()
            if "junction_type" not in tuned_params:
                tuned_params["junction_type"] = (
                    pcell_param_values["junction_type"] if is_pcell else cell_class_from_name
                )
            junction_type = tuned_params["junction_type"]
            if junction_type not in junction_type_choices:
                error_text = (
                    f"'junction_type' value {junction_type} for junction "
                    f"({parent_name}, {name}) is not part of junction_type_choices"
                )
                logging.error(error_text)
                raise ValueError(error_text)
            junction_type = library_layout.pcell_declaration(junction_type)
            if "face_ids" not in tuned_params:
                if is_pcell:
                    tuned_params["face_ids"] = pcell_param_values["face_ids"]
                else:
                    for face in default_faces:
                        if _static_junction_is_on_face(cell, face):
                            tuned_params["face_ids"] = [face]
                            break
            params = {
                # If PCell is available, get PCell parameter values that are available
                k: v.default if not is_pcell else pcell_param_values.get(k, v.default)
                for k, v in type(junction_type).get_schema().items()
            }
            params.update(tuned_params)
            # Not PCell, need to be strict that tuned junction params json includes all params
            if not is_pcell:
                _check_missing_junction_parameters(
                    type(junction_type).__name__, junction_schema_errors, params, tuned_params, parent_name, name
                )
            # Is PCell, and junction type is being changed. Need to make sure params exclusive to new type are tuned
            elif junction_type is not None and junction_type != pcell:
                exclusive_params = {k: v for k, v in params.items() if k not in pcell_param_values}
                _check_missing_junction_parameters(
                    type(junction_type).__name__,
                    junction_schema_errors,
                    exclusive_params,
                    tuned_params,
                    parent_name,
                    name,
                )
            _check_surplus_junction_parameters(
                type(junction_type).__name__,
                junction_schema_errors,
                type(junction_type).get_schema(),
                tuned_params,
                parent_name,
                name,
            )
            refp = get_refpoints(layout.layer(default_layers["refpoints"]), cell).dict()
            found_junctions.append(
                JunctionEntry(
                    type(junction_type), trans, trans_path + [inst.dcplx_trans], params, parent_name, name, refp
                )
            )
        for i in cell.each_inst():
            # For pcell oas, accumulate transformation starting from root
            # For static oas, only use parent.dcplx_trans * this.dcplx_trans
            recursive_junction_search(i, name, trans if is_pcell else prev_trans, trans_path + [inst.dcplx_trans])

    for i in top_cell.each_inst():
        recursive_junction_search(i, None, i.dcplx_trans, [])
    # Need to know face of junctions before performing chip specific transformation,
    # because we need to know for which face we need to perform the marker position test
    if found_junctions:
        chip_trans = _transformation_for_junction_face(
            top_cell, found_junctions[0].parameters["face_ids"], old_translation=old_translation
        )
        for jj in found_junctions:
            jj.trans = chip_trans * jj.trans
    _check_junction_names_unique(found_junctions)
    if check_paramset:
        _print_surplus_junction_parameters(junction_schema_errors)
        _handle_missing_junction_parameters(junction_schema_errors, is_pcell, halt_on_missing_params)
    return found_junctions


def check_static_cell_has_junctions(top_cell: pya.Cell) -> bool:
    """Perform quick check on a static chip cell if it contains a junction.

    Args: top_cell - top cell of the chip

    Returns: True if chip contains at least one junction.
    """
    layout = top_cell.layout()

    def recursive_junction_search(inst):
        cell = layout.cell(inst.cell_index)
        cell_class_from_name = cell.name.split("$")[0].replace("*", " ")
        is_junction = cell_class_from_name in junction_type_choices
        if is_junction:
            return True
        for i in cell.each_inst():
            if recursive_junction_search(i):
                return True
        return False

    for i in top_cell.each_inst():
        if recursive_junction_search(i):
            return True
    return False


def place_junctions(top_cell: pya.Cell, junctions: List[JunctionEntry]) -> None:
    """Places `junctions` to `top_cell` in the same location and orientation as in
    the cell they were extracted from, but with possibly tuned parameters.
    """
    layout = top_cell.layout()
    for junction in junctions:
        if "junction_type" not in junction.parameters:
            junction.parameters["junction_type"] = to_library_name(junction.type.__name__)
        if to_library_name(junction.type.__name__) != junction.parameters["junction_type"]:
            error_text = (
                f"Exported junction of class '{to_library_name(junction.type.__name__)}', "
                f"but 'junction_type' parameter was set to {junction.parameters['junction_type']}"
            )
            logging.error(error_text)
            raise ValueError(error_text)
        junction_cell = Junction.create(layout, **junction.parameters)
        top_cell.insert(pya.DCellInstArray(junction_cell.cell_index(), junction.trans))


def get_tuned_junction_json(junctions: List[JunctionEntry]) -> Dict:
    """Returns a jsonable dict of all junction parameters for each junction entry in `junctions`.

    If junctions were extracted from a cell with pcell data, the json can be extracted to
    have an exhaustive list of all junction parameters so that junctions can then be tuned
    using a cell with no pcell data, which is faster to read.
    """
    result = {}
    for junction in junctions:
        if junction.parent_name not in result:
            result[junction.parent_name] = {}
        # Copy parameter set, don't pass by reference
        result[junction.parent_name][junction.name] = dict(junction.parameters.items())
    return result


def copy_one_layer_of_cell(
    write_path: str,
    top_cell: pya.Cell,
    junctions: List[JunctionEntry],
    layer_string: str,
    old_translation: bool = False,
) -> None:
    """Extracts all geometry in `top_cell` at layer `layer_string`
    and saves the geometry into a new file at `write_path`.
    The face of the layer is determined from `junctions` parameters.

    This can be used to extract geometry of alignment markers as well as other geometry
    to visualize junctions within a context of surrounding elements.
    The file at `write_path` may be loaded later and junctions may be placed using
    `place_junctions` into the top cell of the file, then saved again.

    Layout will be transformed such that the chip is facing the viewer.
    For some chips this means that the layout gets mirrored. By default, mirrored chip is also
    translated so that bottom left corner is at origin. If `old_translation` is set to True,
    it will leave chip translation in place, only performing mirroring.
    """
    # TODO: Assuming face of the junction determined by first element of 'face_ids'.
    # Reconsider once multiface junctions are introduced.
    faces_set = {j.parameters["face_ids"][0] for j in junctions}
    if len(faces_set) > 1:
        error_text = f"Detected inconsistent junction face assignments {faces_set}"
        logging.error(error_text)
        raise ValueError(error_text)
    face = list(faces_set)[0]
    layout = top_cell.layout()
    layers = [l for l in layout.layer_infos() if l.name == (f"{face}_{layer_string}")]
    if not layers:
        error_text = f"Layer not found '{face}_{layer_string}'"
        logging.error(error_text)
        raise ValueError(error_text)
    layer = layers[0]
    trans = _transformation_for_junction_face(top_cell, [face], old_translation=old_translation)
    # Copy layout so when we transform, orignal layout is unaffected
    layout_out = layout.dup()
    # Remove unneeded layers to save time on transformation
    for l in layout_out.layer_infos():
        if l.name != layer.name:
            layout_out.clear_layer(layout_out.layer(l))
    layout_out.transform(trans)
    save_layout(write_path, layout_out, [top_cell], [layer])
