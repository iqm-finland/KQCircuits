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

import csv
import json
import runpy
from pathlib import Path


POST_PROCESS_DIR = Path("klayout_package/python/scripts/simulations/post_process")


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def run_post_process(script_name, tmp_path, monkeypatch, test_file):
    script_dir = Path(test_file).parents[3] / POST_PROCESS_DIR
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(script_dir))
    runpy.run_path(str(script_dir / script_name), run_name="__main__")


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))
