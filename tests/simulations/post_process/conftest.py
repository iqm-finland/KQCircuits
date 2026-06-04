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
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
POST_PROCESS_DIR = REPO_ROOT / "klayout_package" / "python" / "scripts" / "simulations" / "post_process"


class PostProcessSandbox:
    """Temporary simulation-folder harness for post-process scripts."""

    def __init__(self, path):
        self.path = Path(path)

    def write_json(self, file_name, data):
        file_path = self.path / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return file_path

    def write_text(self, file_name, data):
        file_path = self.path / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(data, encoding="utf-8")
        return file_path

    def run_script(self, script_name, *args):
        env = os.environ.copy()
        python_path = [str(POST_PROCESS_DIR)]
        if env.get("PYTHONPATH"):
            python_path.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(python_path)

        result = subprocess.run(
            [sys.executable, str(POST_PROCESS_DIR / script_name), *[str(arg) for arg in args]],
            cwd=self.path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        return result

    def csv_rows(self, suffix):
        matches = list(self.path.glob(f"*{suffix}"))
        assert len(matches) == 1
        with matches[0].open(encoding="utf-8", newline="") as csv_file:
            return list(csv.DictReader(csv_file))


@pytest.fixture
def post_process_sandbox(tmp_path):
    return PostProcessSandbox(tmp_path)
