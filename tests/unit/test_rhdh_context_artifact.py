"""Behavior tests for the RHDH context artifact producer."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTEXT_SCRIPT = PROJECT_ROOT / "skills" / "engineering" / "rhdh-context" / "scripts" / "context.py"


def test_context_script_resolves_configured_repositories_without_exposing_config_values(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    overlay = tmp_path / "rhdh-plugin-export-overlays"
    overlay.mkdir()
    config_dir = project / ".rhdh"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        json.dumps({"repos": {"overlay": str(overlay)}, "token": "must-not-leak"}),
        encoding="utf-8",
    )

    env = {**os.environ, "HOME": str(tmp_path / "home"), "USERPROFILE": str(tmp_path / "home")}
    result = subprocess.run(
        [
            sys.executable,
            str(CONTEXT_SCRIPT),
            "--project-root",
            str(project),
            "--no-tool-probes",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    artifact = json.loads(result.stdout)
    assert artifact["contract"] == "RhdhContext/v1"
    assert artifact["data"]["repositories"]["overlay"] == str(overlay.resolve())
    assert artifact["data"]["configuration"] == {
        "dataDirectory": str((tmp_path / "home" / ".config" / "rhdh-skill").resolve()),
        "projectConfig": str((config_dir / "config.json").resolve()),
        "userConfig": str((tmp_path / "home" / ".config" / "rhdh-skill" / "config.json").resolve()),
    }
    assert "must-not-leak" not in result.stdout
