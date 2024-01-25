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
# (meetiqm.com/developers/osstmpolicy). IQM welcomes contributions to the code. Please see our contribution agreements
# for individuals (meetiqm.com/developers/clas/individual) and organizations (meetiqm.com/developers/clas/organization).

"""
Functions to tune and replace junctions in existing design files.

See scripts/macros/export/export_tuned_junctions.lym for a use case of these functions
"""

from os import path
from typing import Dict, List
import logging
from kqcircuits.pya_resolver import pya
from kqcircuits.junctions import junction_type_choices
from kqcircuits.junctions.junction import Junction
from kqcircuits.chips.chip import Chip
from kqcircuits.util.library_helper import load_libraries, to_library_name


class JunctionEntry:
    """All junction properties we want to store when extracting junctions"""
    def __init__(self, class_type: type, trans: pya.DCplxTrans, parameters: Dict, parent_name: str, name: str) -> None:
        self.type = class_type
        self.trans = trans
        self.parameters = parameters
        self.parent_name = parent_name
        self.name = name
    def __eq__(self, __value: object) -> bool:
        return self.type == __value.type and \
            self.trans == __value.trans and \
            self.parameters == __value.parameters and \
            self.parent_name == __value.parent_name and \
            self.name == __value.name

def _check_junction_names_unique(junctions):
    """Raises exception if ``junctions`` contains a non-unique (parent_name, name) key-pair"""
    unique_names = set()
    for junction in junctions:
        if (junction.parent_name, junction.name) in unique_names:
            error_text = ("Following cell parent name and child name is not unique in top cell: "
                        f"{(junction.parent_name, junction.name)}. "
                        "Something seems to be wrong with KQC generated cell")
            error = ValueError(error_text)
            logging.exception(error_text, exc_info=error)
            raise error
        unique_names.add((junction.parent_name, junction.name))

def _check_missing_junction_parameters(junction_class_name, junction_schema_errors,
                                       params, tuned_params, parent_name, name):
    """Run for every found junction to compare junction library schema (`params`)
    and schema as given in json file (`tuned_params`).

    If some parameter keys are missing in `tuned_params`, stores missing keys in mutable `junction_schema_errors`.
    `junction_schema_errors` is a dict that has junction class as keys, and as values
    a tuple "missing_fields" with set of missing parameter keys and a list for junction names.

    Note that some parameter keys are ignored.
    """
    ignore_param_keys = {"_junction_parameters", "junction_parameters", "display_name"}
    if junction_class_name not in junction_schema_errors:
        junction_schema_errors[junction_class_name] = {
            "missing_fields": (set(), []), "surplus_fields": (set(), [])
        }
    missing_fields = set(params.keys()).difference(set(tuned_params.keys())).difference(ignore_param_keys)
    junction_schema_errors[junction_class_name]["missing_fields"][0].update(missing_fields)
    if len(missing_fields) > 0:
        junction_schema_errors[junction_class_name]["missing_fields"][1].append((parent_name, name))

def _check_surplus_junction_parameters(junction_class_name, junction_schema_errors,
                                       params, tuned_params, parent_name, name):
    """Run for every found junction to compare junction library schema (`params`)
    and schema as given in json file (`tuned_params`).

    If some parameter keys are in `tuned_params` but not in `params`,
    stores missing keys in mutable `junction_schema_errors`.
    `junction_schema_errors` is a dict that has junction class as keys, and as values
    a tuple "surplus_fields" with set of surplus parameter keys and a list for junction names.
    """
    if junction_class_name not in junction_schema_errors:
        junction_schema_errors[junction_class_name] = {
            "missing_fields": (set(), []), "surplus_fields": (set(), [])
        }
    surplus_fields = set(tuned_params.keys()).difference(set(params.keys()))
    junction_schema_errors[junction_class_name]["surplus_fields"][0].update(surplus_fields)
    if len(surplus_fields) > 0:
        junction_schema_errors[junction_class_name]["surplus_fields"][1].append((parent_name, name))

def _print_surplus_junction_parameters(junction_schema_errors):
    """Logs as warning the content of "surplus_fields" in `junction_schema_errors`
    junction parameters that were attempted to be tuned,
    yet were not defined for the given junction types.
    """
    for k,v in junction_schema_errors.items():
        surplus_fields, junctions = v["surplus_fields"]
        if len(surplus_fields) > 0:
            logging.warning((f"{k} class junction attempted to be tuned with parameters "
                             f"that are not part of the class: {surplus_fields}"))
            logging.warning(f"for {junctions[:5]}\n")

def _halt_if_missing_junction_parameters(junction_schema_errors, is_pcell):
    """Raises exception if "missing_fields" for some entry in `junction_schema_errors` is not empty,
    formats an error message to show all missing parameter keys detected for each junction type
    and names the affected junctions.
    """
    error_text = ""
    for k,v in junction_schema_errors.items():
        missing_fields, junctions = v["missing_fields"]
        if len(missing_fields) > 0:
            error_text = (f"{error_text}"
                          f"{k} class junction parameters missing {missing_fields}\n"
                          f"missing for {junctions[:5]}\n\n")
    if len(error_text) > 0:
        if is_pcell:
            error_text = ("Since junction type was changed for some junctions, "
                        "the tuned junction json should give value at least for parameters "
                        "that are in new junction type but not in old junction type.\n"
                        f"Following junction parameters missing:\n\n{error_text}")
        else:
            error_text = ("Since the cell doesn't contain pre-existing PCell parameter data, "
                        "the tuned junction json should be exhaustive.\n"
                        f"Following junction parameters missing:\n\n{error_text}")
        error = ValueError("Some junction parameters were missing in the tuning json, see log for details")
        logging.exception(error_text, exc_info=error)
        raise error

def extract_junctions(top_cell: pya.Cell, tuned_junction_parameters: Dict) -> List[JunctionEntry]:
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

    If `top_cell` has no pcell data, `tuned_junction_parameters` must include all parameter keys
    of the junction parameter schema for each junction contained in the `top_cell`,
    even if the parameter values are the same as were used to construct `top_cell`.
    If that is not the case, `extract_junctions` will raise an exception.

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
    if not is_pcell:
        logging.warning("Top cell doesn't contain PCell parameter data")

    def recursive_junction_search(inst, parent_name, prev_trans):
        cell = layout.cell(inst.cell_index)
        name = inst.property('id')
        trans = prev_trans * inst.dcplx_trans
        tuned_params = tuned_junction_parameters.get(parent_name, {}).get(name, {})
        if is_pcell:
            pcell = inst.pcell_declaration()
            is_junction = (pcell and isinstance(pcell, Junction))
        else:
            cell_class_from_name = cell.name.split('$')[0].replace('*', ' ')
            pcell = library_layout.pcell_declaration(cell_class_from_name)
            is_junction = cell_class_from_name in junction_type_choices
        if is_junction:
            if is_pcell:
                # Parameter values present in PCell data can be reused
                pcell_param_values = inst.pcell_parameters_by_name()
            junction_type = tuned_params.get("junction_type")
            if junction_type not in junction_type_choices and not (is_pcell and "junction_type" not in tuned_params):
                error_text = (f"'junction_type' value {junction_type} for junction "
                              f"({parent_name}, {name}) is not part of junction_type_choices")
                error = ValueError(error_text)
                logging.exception(error_text, exc_info=error)
                raise error
            if not junction_type and is_pcell:
                junction_type = pcell_param_values.get("junction_type")
            junction_type = library_layout.pcell_declaration(junction_type)
            params = {
                # If PCell is available, get PCell parameter values that are available
                k: v.default if not is_pcell else pcell_param_values.get(k, v.default)
                for k, v in type(junction_type).get_schema().items()
            }
            params.update(tuned_params)
            # Not PCell, need to be strict that tuned junction params json includes all params
            if not is_pcell:
                _check_missing_junction_parameters(type(junction_type).__name__,
                                                   junction_schema_errors,
                                                   params, tuned_params, parent_name, name)
            # Is PCell, and junction type is being changed. Need to make sure params exclusive to new type are tuned
            elif junction_type is not None and junction_type != pcell:
                exclusive_params = {k:v for k,v in params.items() if k not in pcell_param_values}
                _check_missing_junction_parameters(type(junction_type).__name__,
                                                   junction_schema_errors,
                                                   exclusive_params, tuned_params, parent_name, name)
            _check_surplus_junction_parameters(type(junction_type).__name__, junction_schema_errors,
                                               type(junction_type).get_schema(), tuned_params, parent_name, name)
            found_junctions.append(JunctionEntry(type(junction_type), trans, params, parent_name, name))
        for i in cell.each_inst():
            # For pcell oas, accumulate transformation starting from root
            # For static oas, only use parent.dcplx_trans * this.dcplx_trans
            recursive_junction_search(i, name, trans if is_pcell else prev_trans)

    for i in top_cell.each_inst():
        recursive_junction_search(i, None, i.dcplx_trans)
    _check_junction_names_unique(found_junctions)
    _print_surplus_junction_parameters(junction_schema_errors)
    _halt_if_missing_junction_parameters(junction_schema_errors, is_pcell)
    return found_junctions

def place_junctions(top_cell: pya.Cell, junctions: List[JunctionEntry]) -> None:
    """Places `junctions` to `top_cell` in the same location and orientation as in
    the cell they were extracted from, but with possibly tuned parameters.
    """
    layout = top_cell.layout()
    for junction in junctions:
        if 'junction_type' not in junction.parameters:
            junction.parameters['junction_type'] = to_library_name(junction.type.__name__)
        if to_library_name(junction.type.__name__) != junction.parameters['junction_type']:
            error_text = (f"Exported junction of class '{to_library_name(junction.type.__name__)}', "
                          f"but 'junction_type' parameter was set to {junction.parameters['junction_type']}")
            error = ValueError(error_text)
            logging.exception(error_text, exc_info=error)
            raise error
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
        result[junction.parent_name][junction.name] = junction.parameters
    return result

def copy_one_layer_of_cell(write_path: str, top_cell: pya.Cell, junctions: List[JunctionEntry], layer_string: str
                           ) -> None:
    """Extracts all geometry in `top_cell` at layer `layer_string`
    and saves the geometry into a new file at `write_path`.
    The face of the layer is determined from `junctions` parameters.

    This can be used to extract geometry of alignment markers as well as other geometry
    to visualize junctions within a context of surrounding elements.
    The file at `write_path` may be loaded later and junctions may be placed using
    `place_junctions` into the top cell of the file, then saved again.
    """
    # TODO: Assuming face of the junction determined by first element of 'face_ids'.
    # Reconsider once multiface junctions are introduced.
    faces_set = {j.parameters["face_ids"][0] for j in junctions}
    if len(faces_set) > 1:
        error_text = f"Detected inconsistent junction face assignments {faces_set}"
        error = ValueError(error_text)
        logging.exception(error_text, exc_info=error)
        raise error
    face = list(faces_set)[0]
    layout = top_cell.layout()
    layers = [l for l in layout.layer_infos() if l.name == (f"{face}_{layer_string}")]
    if not layers:
        error_text = f"Layer not found '{face}_{layer_string}'"
        error = ValueError(error_text)
        logging.exception(error_text, exc_info=error)
        raise error
    layer = layers[0]

    svopt = pya.SaveLayoutOptions()
    svopt.set_format_from_filename(write_path)
    svopt.deselect_all_layers()
    svopt.clear_cells()
    svopt.add_cell(top_cell.cell_index())
    svopt.add_layer(layout.layer(layer), layer)
    svopt.write_context_info = False
    layout.write(write_path, svopt)

def replace_squids(cell, junction_type, parameter_name, parameter_start, parameter_step, parameter_end=None):
    """DEPRECATED! Replaces squids by code generated squids with the given parameter sweep.

    All squids below top_cell in the cell hierarchy are removed. The number of code
    generated squids may be limited by the value of parameter_end.

    Args:
        cell (Cell): The cell where the squids to be replaced are
        junction_type: class name of the code generated squid that replaces the other squids
        parameter_name (str): Name of the parameter to be swept
        parameter_start: Start value of the parameter
        parameter_step: Parameter value increment step
        parameter_end: End value of the parameter. If None, there is no limit for the parameter value, so that all
            squids are replaced

    """
    layout = cell.layout()
    parameter_value = parameter_start
    junction_types = [choice if isinstance(choice, str) else choice[1] for choice in junction_type_choices]

    old_squids = []  # list of tuples (squid instance, squid dtrans with respect to cell, old name)

    def recursive_replace_squids(top_cell_inst, combined_dtrans):
        """Appends to old_squids all squids in top_cell_inst or any instance below it in hierarchy."""
        # cannot use just top_cell_inst.cell due to klayout bug, see
        # https://www.klayout.de/forum/discussion/1191/cell-shapes-cannot-call-non-const-method-on-a-const-reference
        top_cell = layout.cell(top_cell_inst.cell_index)
        for subcell_inst in top_cell.each_inst():
            subcell_name = subcell_inst.cell.name.split("$")[0]
            if subcell_name in junction_types:
                old_squids.append((subcell_inst, combined_dtrans*subcell_inst.dcplx_trans, subcell_name))
            else:
                recursive_replace_squids(subcell_inst, combined_dtrans*subcell_inst.dcplx_trans)

    for inst in cell.each_inst():
        if inst.cell.name in junction_types:
            old_squids.append((inst, inst.dcplx_trans, inst.cell.name))
        recursive_replace_squids(inst, inst.dcplx_trans)

    # sort left-to-right and bottom-to-top
    old_squids.sort(key=lambda squid: (squid[1].disp.x, squid[1].disp.y))

    for (inst, dtrans, name) in old_squids:
        if (parameter_end is None) or (parameter_value <= parameter_end):
            # create new squid at old squid's position
            parameters = {parameter_name: parameter_value}
            squid_cell = Junction.create(layout, junction_type=junction_type, face_ids=inst.pcell_parameter("face_ids"),
                                      **parameters)
            cell.insert(pya.DCellInstArray(squid_cell.cell_index(), dtrans))
            logging.info("Replaced squid \"%s\" with dtrans=%s by a squid \"%s\" with %s=%s.",
                         name, dtrans, junction_type, parameter_name, parameter_value)
            parameter_value += parameter_step
        # delete old squid
        inst.delete()

def replace_squid(top_cell, inst_name, junction_type, mirror=False, squid_index=0, **params):
    """DEPRECATED! Replaces a SQUID by the requested alternative in the named instance.

    Replaces the SQUID(s) in the sub-element(s) named ``inst_name`` with other SQUID(s) of
    ``junction_type``. The necessary SQUID parameters are specified in ``params``. If ``inst_name`` is
    a Test Structure then ``squid_index`` specifies which SQUID to change.

    Args:
        top_cell: The top cell with SQUIDs to be replaced
        inst_name: Instance name of PCell containing the SQUID to be replaced
        junction_type: Name of SQUID Class or .gds/.oas file
        mirror: Mirror the SQUID along its vertical axis
        squid_index: Index of the SQUID to be replaced within a Test Structure
        **params: Extra parameters for the new SQUID
    """

    def find_cells_with_squids(chip, inst_name):
        """Returns the container cells in `chip` called `inst_name`"""
        cells = []
        layout = chip.layout()
        for inst in chip.each_inst():
            if inst.property("id") == inst_name:
                cells.append((chip, inst))
            elif isinstance(inst.pcell_declaration(), Chip):  # recursively look for more chips
                cells += find_cells_with_squids(layout.cell(inst.cell_index), inst_name)
        return cells

    cells = find_cells_with_squids(top_cell, inst_name)
    if not cells:
        logging.warning(f"Could not find anything named '{inst_name}'!")

    layout = top_cell.layout()
    file_cell = None
    if junction_type.endswith(".oas") or junction_type.endswith(".gds"):  # try to load from file
        if not path.exists(junction_type):
            logging.warning(f"No file found at '{path.realpath(junction_type)}!")
            return
        load_opts = pya.LoadLayoutOptions()
        load_opts.cell_conflict_resolution = pya.LoadLayoutOptions.CellConflictResolution.RenameCell
        layout.read(junction_type, load_opts)
        file_cell = layout.top_cells()[-1]
        file_cell.name = f"Junction Library.{file_cell.name}"

    for (chip, inst) in cells:
        orig_trans = inst.dcplx_trans
        ccell = inst.layout().cell(inst.cell_index)

        if ccell.is_pcell_variant():  # make copy if used elsewhere
            dup = ccell.dup()
            dup.set_property("id", inst.property("id"))
            inst.delete()
            chip.insert(pya.DCellInstArray(dup.cell_index(), orig_trans), dup.prop_id)
            ccell = dup

        squids = [sq for sq in ccell.each_inst() if sq.cell.qname().find("Junction Library") != -1]
        squids.sort(key=lambda q: q.property("squid_index"))
        if not squids or squid_index >= len(squids) or squid_index < 0:
            logging.warning(f"No SQUID found in '{inst_name}' or squid_index={squid_index} is out of range!")
            continue
        old_squid = squids[squid_index]
        if old_squid.is_pcell():
            params = {"face_ids": old_squid.pcell_parameter("face_ids"), **params}
        trans = old_squid.dcplx_trans * pya.DCplxTrans.M90 if mirror else old_squid.dcplx_trans
        squid_pos = (orig_trans * trans).disp
        logging.info(f"Replaced SQUID of '{inst_name}' with {junction_type} at {squid_pos}.")
        old_squid.delete()
        if file_cell:
            new_squid = ccell.insert(pya.DCellInstArray(file_cell.cell_index(), trans))
        else:
            new_squid = Junction.create(layout, junction_type=junction_type, **params)
            new_squid = ccell.insert(pya.DCellInstArray(new_squid.cell_index(), trans))
        new_squid.set_property("squid_index", squid_index)

def convert_cells_to_static(layout):
    """DEPRECATED! Converts all cells in the layout to static. """

    converted_cells = {}

    # convert the cells to static
    for cell in layout.each_cell():
        if cell.is_library_cell():
            cell_idx = cell.cell_index()
            new_cell_idx = layout.convert_cell_to_static(cell_idx)
            if new_cell_idx != cell_idx:
                converted_cells[cell_idx] = new_cell_idx

    # translate the instances
    for cell in layout.each_cell():
        for inst in cell.each_inst():
            if inst.cell_index in converted_cells:
                inst.cell_index = converted_cells[inst.cell_index]

    # delete the PCells
    for cell_idx in converted_cells:
        layout.delete_cell(cell_idx)
