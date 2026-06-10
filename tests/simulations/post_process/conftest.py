# This code is part of KQCircuits
# Copyright (C) 2026 IQM Finland Oy
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

"""Shared infrastructure for testing the post-process scripts.

Each post-process script is a top-level script (not an importable module) that is meant to be run with the
current working directory set to a simulation output folder. The fixtures here set up such a folder with mocked
simulation files, run a script in it the same way `simulation.sh`/`simulation.bat` would, and read back the files
the script produces. Adding a test for a new script should only require these fixtures.
"""

import csv
import json
import runpy
import sys
from pathlib import Path

import pytest

POST_PROCESS_DIR = Path(__file__).parents[3] / "klayout_package" / "python" / "scripts" / "simulations" / "post_process"


@pytest.fixture
def sim_folder(tmp_path, monkeypatch):
    """Temporary folder that mimics a simulation output folder.

    The current working directory is changed to it and the post-process scripts are put on the path so that their
    `from post_process_helpers import ...` style imports resolve like they do during an actual simulation run.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(POST_PROCESS_DIR))
    return tmp_path


@pytest.fixture
def write_simulation(sim_folder):
    """Write the `<name>.json` definition and `<name>_project_results.json` results files for one sweep."""

    def write(name, definition, results):
        definition = {"parameters": {}, **definition}
        (sim_folder / f"{name}.json").write_text(json.dumps(definition), encoding="utf-8")
        (sim_folder / f"{name}_project_results.json").write_text(json.dumps(results), encoding="utf-8")

    return write


@pytest.fixture
def run_post_process(sim_folder, monkeypatch):
    """Run a post-process script inside the simulation folder, optionally passing command line arguments."""

    def run(script_name, args=None):
        monkeypatch.setattr(sys, "argv", [script_name, *(str(a) for a in args or [])])
        runpy.run_path(str(POST_PROCESS_DIR / script_name), run_name="__main__")
        return sim_folder

    return run


@pytest.fixture
def read_csv():
    """Read a CSV produced by a post-process script into a list of row dictionaries."""

    def read(path):
        with open(path, "r", encoding="utf-8", newline="") as csv_file:
            return list(csv.DictReader(csv_file))

    return read
