# This code is part of KQCircuits
# Copyright (C) 2023 IQM Finland Oy
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
import json
from pathlib import Path
import numpy as np
from kqcircuits.simulations.export.export_and_run import export_and_run
from kqcircuits.defaults import SIM_SCRIPT_PATH


def assert_dicts(d1, d2, rtol, atol, ignore_keys=None, only_keys=None):
    """
    Checks if fem data in dictionaries d1 and d2 is equivalent.
    Equivalent if

      * keys are the same
      * values are np.allclose()

    Args:

      d1(dict()): first dictionary containing the first fem data
      d2(dict()): second dictionary containing the second fem data
      ignore_keys(list): keys that are not taken into account in the comparison
      only_keys(list): keys that are only taken into account in the comparison
    """
    if d1 is None and d2 is None:
        return True
    if ignore_keys is None:
        ignore_keys = []
    if only_keys is not None:
        ignore_keys = set(d1.keys()) + set(d2.keys())
        ignore_keys -= set(only_keys)
        ignore_keys = list(ignore_keys)
    keys1 = set(d1.keys())
    keys2 = set(d2.keys())
    assert keys1 == keys2
    for key in keys1:
        if key not in ignore_keys:
            val1 = d1[key]
            val2 = d2[key]
            if val1 is None:
                assert val2 is None
            elif isinstance(val1, dict):
                assert isinstance(val2, dict)
                assert assert_dicts(val1, val2, rtol, atol, ignore_keys=ignore_keys, only_keys=only_keys)
            elif isinstance(val1, str):
                assert isinstance(val2, str)
                assert val1 == val2
            else:
                assert np.allclose(val1, val2, rtol=rtol, atol=atol), f"{val1} and {val2} for {key} do not match"
    return True


def assert_project_results_equal(
    project_results_path: Path, ref_project_results_path: Path, rtol, atol, ignore_keys=None, generate_ref_results=False
):
    """
    Checks whether the project results correspond to the reference
    project results.

    project_results_path(Path): path to the KQC simulations "_project_results.json" file
    ref_project_results_path(dict): path to reference project results in dict format
    rtol(float): see `numpy.allclose`
    atol(float): see `numpy.allclose`
    ignore_keys(list): keys that are not taken into account in the comparison
    generate_ref_results(bool): if true, generates the reference results json based on the simulation to be tested
    """

    with open(project_results_path) as f:
        results = json.load(f)

    if generate_ref_results:
        with open(ref_project_results_path, "w") as f:
            json.dump(results, f)

    with open(ref_project_results_path) as f:
        ref_results = json.load(f)

    return assert_dicts(ref_results, results, rtol, atol, ignore_keys=ignore_keys)


def export_and_run_test(tmp_path: Path, export_script_name: str, args: list):
    """
    Exports, runs and asserts a KQC simulation.

    Args:
        tmp_path: temporary directory for the output files
        export_script_name(str): Name of the export script (has to be located in SIM_SCRIPT_PATH)
        args(list): list of arguments passed to the export script

    Returns:
        a tuple containing

            * export_script(Path): path to the simulation export script
            * tmp_path(Path): path where simulation files are exported

    """

    export_script = SIM_SCRIPT_PATH / f"{export_script_name}.py"

    return export_and_run(export_script, tmp_path, quiet=True, args=args)


def assert_sim_script(
    export_script_name: str,
    export_script_dir: Path,
    export_path: Path,
    project_ref_info: dict,
    generate_ref_results=False,
):
    """
    Exports, runs and asserts a KQC simulation.

    Args:
        export_script_name(str): Name of the export script (has to be located in SIM_SCRIPT_PATH)
        export_script_dir(Path): Path to the export script
        export_path(Path): Path to the export folder
        project_ref_info_list(list): list of dicts containing

            * project_results_file(Path): KQC simulations "_project_results.json" file
            * ref_project_results_file(dict): reference project results file
            * rtol(float): see `numpy.allclose`
            * atol(float): see `numpy.allclose`
            * ignore_keys(list): keys that are not taken into account in the comparison

        generate_ref_results(bool): if True, generates the reference
            results json based on the simulation to be tested (test
            passes only if this is False)

    """
    asset_dir = export_script_dir / export_script_name

    project_ref = {
        "project_results_path": export_path / project_ref_info["project_results_file"],
        "ref_project_results_path": asset_dir / project_ref_info["ref_project_results_file"],
        "rtol": project_ref_info["rtol"],
        "atol": project_ref_info["atol"],
        "ignore_keys": project_ref_info["ignore_keys"],
    }

    assert_project_results_equal(**project_ref, generate_ref_results=generate_ref_results)

    assert not generate_ref_results, "Test set to fail when reference data is generated"
