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
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
POST_PROCESS_DIR = REPO_ROOT / "klayout_package" / "python" / "scripts" / "simulations" / "post_process"


def _write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _copy_post_process_script(tmp_path, script_name):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    shutil.copy2(POST_PROCESS_DIR / script_name, scripts_dir / script_name)
    shutil.copy2(POST_PROCESS_DIR / "post_process_helpers.py", scripts_dir / "post_process_helpers.py")
    return scripts_dir / script_name


def _run_post_process_script(tmp_path, script_name, *args):
    script = _copy_post_process_script(tmp_path, script_name)
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{script.parent}{os.pathsep}{env.get('PYTHONPATH', '')}"
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _read_csv(path):
    with path.open(encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def test_produce_cmatrix_table_writes_swept_capacitance_rows(tmp_path):
    _write_json(tmp_path / "waveguide_w10.json", {"parameters": {"width": 10, "gap": 6}, "tool": "cross-section"})
    _write_json(tmp_path / "waveguide_w20.json", {"parameters": {"width": 20, "gap": 6}, "tool": "cross-section"})
    _write_json(tmp_path / "waveguide_w10_project_results.json", {"CMatrix": [[1.0, 0.2], [0.2, 2.0]]})
    _write_json(tmp_path / "waveguide_w20_project_results.json", {"Cs": [[3.0, 0.4], [0.4, 4.0]]})

    _run_post_process_script(tmp_path, "produce_cmatrix_table.py")

    rows = {row["key"]: row for row in _read_csv(tmp_path / f"{tmp_path.name}_results.csv")}
    assert rows["waveguide_w10"] == {
        "key": "waveguide_w10",
        "width": "10",
        "C11": "1.0",
        "C12": "0.2",
        "C21": "0.2",
        "C22": "2.0",
    }
    assert rows["waveguide_w20"] == {
        "key": "waveguide_w20",
        "width": "20",
        "C11": "3.0",
        "C12": "0.4",
        "C21": "0.4",
        "C22": "4.0",
    }


def test_produce_z0_table_writes_impedance_and_effective_speed(tmp_path):
    _write_json(tmp_path / "cross_section.json", {"parameters": {"width": 10}})
    _write_json(tmp_path / "cross_section_project_results.json", {"Cs": [[4.0]], "Ls": [[9.0]]})

    _run_post_process_script(tmp_path, "produce_z0_table.py")

    rows = _read_csv(tmp_path / f"{tmp_path.name}_Z0.csv")
    assert len(rows) == 1
    assert rows[0]["key"] == "cross_section"
    assert float(rows[0]["Cs"]) == 4.0
    assert float(rows[0]["Ls"]) == 9.0
    assert float(rows[0]["Z0"]) == pytest.approx(1.5)
    assert float(rows[0]["c_eff"]) == pytest.approx(1.0 / 6.0)


def test_produce_q_factor_table_combines_epr_with_loss_tangents(tmp_path):
    _write_json(tmp_path / "waveguide.json", {"parameters": {"width": 10}})
    _write_json(tmp_path / "waveguide_project_results.json", {})
    _write_json(tmp_path / "loss_tangents.json", {"ma": 1e-3, "ms": 2e-3})
    (tmp_path / "waveguide_epr.csv").write_text("E_total,p_ma,p_ms\n1.0,0.25,0.5\n", encoding="utf-8")

    _run_post_process_script(tmp_path, "produce_q_factor_table.py", "loss_tangents.json")

    rows = _read_csv(tmp_path / "waveguide_q_factors.csv")
    assert len(rows) == 1
    assert float(rows[0]["Q_ma"]) == pytest.approx(4000.0)
    assert float(rows[0]["Q_ms"]) == pytest.approx(1000.0)
    assert float(rows[0]["Q_total"]) == pytest.approx(800.0)


def test_elmer_cleanup_only_cleans_simulation_directories(tmp_path):
    script = _copy_post_process_script(tmp_path, "elmer_cleanup.py")
    (script.parent / "elmer_helpers.py").write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "",
                "def delete_meshes(path, simname):",
                "    marker = Path(path) / simname / 'mesh_to_delete.unv'",
                "    if marker.exists():",
                "        marker.unlink()",
                "    with (Path(path) / 'deleted_meshes.txt').open('a', encoding='utf-8') as log_file:",
                "        log_file.write(simname + '\\n')",
            ]
        ),
        encoding="utf-8",
    )

    sim_dir = tmp_path / "waveguide"
    sim_dir.mkdir()
    (sim_dir / "mesh_to_delete.unv").write_text("mesh data", encoding="utf-8")
    for non_sim_dir in ("scripts", "log_files", "elmer_data", "s_matrix_plots"):
        path = tmp_path / non_sim_dir
        path.mkdir(exist_ok=True)
        (path / "mesh_to_delete.unv").write_text("keep", encoding="utf-8")

    _run_post_process_script(tmp_path, "elmer_cleanup.py")

    assert not (sim_dir / "mesh_to_delete.unv").exists()
    for non_sim_dir in ("scripts", "log_files", "elmer_data", "s_matrix_plots"):
        assert (tmp_path / non_sim_dir / "mesh_to_delete.unv").exists()
    assert (tmp_path / "deleted_meshes.txt").read_text(encoding="utf-8") == "waveguide\n"
