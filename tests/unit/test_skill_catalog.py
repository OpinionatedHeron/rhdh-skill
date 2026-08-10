"""Behavior tests for the machine-readable skill catalog validator."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = PROJECT_ROOT / "scripts" / "validate_skill_catalog.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_skill_catalog", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_repository_catalog_exposes_the_approved_composable_skill_set():
    """The validator reports the approved promoted catalog through its JSON CLI."""
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--root", str(PROJECT_ROOT), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    report = json.loads(result.stdout)
    assert report["valid"] is True
    assert set(report["promotedSkills"]) == {
        "ask-rhdh",
        "setup-rhdh-skills",
        "rhdh-context",
        "rhdh-plugin-development",
        "rhdh-overlay",
        "rhdh-local",
        "rhdh-pull-request",
        "rhdh-pr-review",
        "rhdh-jira",
        "rhdh-platform-support",
        "rhdh-test-plan",
        "rhdh-release",
        "rhdh-ci",
        "rhdh-base-images",
        "rhdh-agent-readiness",
        "skill-authoring",
    }
    assert set(report["humanInvokedSkills"]) == {"ask-rhdh", "setup-rhdh-skills"}
    assert set(report["requiredExternalSkills"]) == {"grilling", "humanizer"}


def test_in_progress_skills_use_the_internal_root_and_metadata_gate(tmp_path):
    validator = load_validator()
    skill = tmp_path / "internal" / "in-progress" / "draft" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: draft\ndescription: Work in progress\nmetadata:\n  internal: true\n---\n",
        encoding="utf-8",
    )

    errors = []
    validator._validate_internal_skills(tmp_path, errors)
    assert errors == []

    skill.write_text("---\nname: draft\ndescription: Accidentally public\n---\n", encoding="utf-8")
    validator._validate_internal_skills(tmp_path, errors)
    assert errors == [{"code": "IN_PROGRESS_PUBLIC", "message": str(skill)}]

    errors.clear()
    skill.write_text(
        "---\nname: draft\nmetadata:\n  owner: team\npolicy:\n  internal: true\n---\n",
        encoding="utf-8",
    )
    validator._validate_internal_skills(tmp_path, errors)
    assert errors == [{"code": "IN_PROGRESS_PUBLIC", "message": str(skill)}]


def test_cycle_detection_ignores_missing_nodes_already_reported_by_the_catalog_validator():
    validator = load_validator()

    assert validator._find_cycle({"skill": ["missing"]}) is None


def test_workflow_links_are_resolved_from_the_document_directory(tmp_path):
    validator = load_validator()
    workflow = tmp_path / "skills" / "operations" / "sample" / "workflows" / "run.md"
    script = workflow.parent.parent / "scripts" / "run.py"
    workflow.parent.mkdir(parents=True)
    script.parent.mkdir(parents=True)
    script.write_text("print('ok')\n", encoding="utf-8")

    errors = []
    validator._validate_local_links(tmp_path, workflow, "[run](../scripts/run.py)", errors)
    assert errors == []

    validator._validate_local_links(tmp_path, workflow, "[run](scripts/run.py)", errors)
    assert errors == [
        {
            "code": "LINK_MISSING",
            "message": "skills/operations/sample/workflows/run.md -> scripts/run.py",
        }
    ]
