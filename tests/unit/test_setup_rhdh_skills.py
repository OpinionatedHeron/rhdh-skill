"""Behavior tests for the setup router's deterministic setup script."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETUP_SCRIPT = (
    PROJECT_ROOT / "skills" / "engineering" / "setup-rhdh-skills" / "scripts" / "setup.py"
)
CATALOG = PROJECT_ROOT / "skills" / "engineering" / "setup-rhdh-skills" / "assets" / "catalog.json"
SHARED_PACKAGE = PROJECT_ROOT / "packages" / "rhdh-common"


def load_setup_module():
    spec = importlib.util.spec_from_file_location("setup_rhdh_skills_script", SETUP_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_setup(*args: str) -> subprocess.CompletedProcess[str]:
    # The script depends on rhdh_common (ADR-0006); uv resolves it from the
    # PEP-723 block, and this subprocess resolves it from the source checkout.
    return subprocess.run(
        [sys.executable, str(SETUP_SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(SHARED_PACKAGE)},
    )


def install_fake_skill(root: Path, name: str) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        f"---\nname: {name}\ndescription: fake installed skill for setup tests\n---\n",
        encoding="utf-8",
    )
    return skill_file


def test_doctor_discovers_dependencies_across_supported_host_layouts(tmp_path):
    home = tmp_path / "home"
    project = tmp_path / "project"
    install_fake_skill(home / ".agents" / "skills", "grilling")
    install_fake_skill(home / ".claude" / "skills", "humanizer")
    install_fake_skill(project / ".cursor" / "skills", "ask-rhdh")

    result = run_setup(
        "doctor",
        "--catalog",
        str(CATALOG),
        "--home",
        str(home),
        "--project-root",
        str(project),
        "--no-tool-probes",
        "--json",
    )

    assert result.returncode == 1
    artifact = json.loads(result.stdout)
    assert artifact["contract"] == "SetupStatus/v1"
    assert set(artifact["data"]["installedSkills"]) == {"ask-rhdh", "grilling", "humanizer"}
    assert artifact["data"]["requiredExternalSkills"] == {
        "grilling": "installed",
        "humanizer": "installed",
    }
    assert artifact["data"]["capabilities"]["tools"]["oc"] == "not-probed"
    assert artifact["data"]["capabilities"]["tools"]["gog"] == "not-probed"
    assert "setup-rhdh-skills" in artifact["data"]["missingSkills"]
    assert all("credential" not in key.lower() for key in artifact["data"])


def test_install_plan_uses_one_pack_command_and_binds_approval_to_material_hash():
    result = run_setup(
        "install-plan",
        "--catalog",
        str(CATALOG),
        "--pack-url",
        "https://skills.sh/p/rhdh-complete-test",
        "--agent",
        "codex",
        "--scope",
        "global",
        "--json",
    )

    assert result.returncode == 0, result.stderr or result.stdout
    artifact = json.loads(result.stdout)
    assert artifact["contract"] == "MutationPlan/v1"
    expected_skills = sorted(
        [
            "ask-rhdh",
            "grilling",
            "humanizer",
            "rhdh-agent-readiness",
            "rhdh-artifacts",
            "rhdh-base-images",
            "rhdh-ci",
            "rhdh-context",
            "rhdh-forge",
            "rhdh-jira",
            "rhdh-local",
            "rhdh-overlay",
            "rhdh-platform-support",
            "rhdh-plugin-development",
            "rhdh-pr-review",
            "rhdh-pull-request",
            "rhdh-release",
            "rhdh-test-plan",
            "setup-rhdh-skills",
            "skill-authoring",
        ]
    )
    operation = artifact["data"]["operations"][0]
    assert operation == {
        "order": 1,
        "ownerSkill": "setup-rhdh-skills",
        "adapter": "skills-cli/v1",
        "operation": "skills.pack.install",
        "target": "global:codex",
        "preview": {
            "argv": [
                "npx",
                "skills",
                "add",
                "https://skills.sh/p/rhdh-complete-test",
                "--agent",
                "codex",
                "--global",
                "--yes",
            ],
            "source": "https://skills.sh/p/rhdh-complete-test",
        },
        "preconditions": [
            {"check": "tool.available", "target": "npx", "required": True},
            {"check": "catalog.schema", "expected": 1, "required": True},
        ],
        "checks": [
            {
                "check": "skills.discovered",
                "expected": expected_skills,
            }
        ],
        "recovery": [
            {
                "adapter": "skills-cli/v1",
                "operation": "skills.remove",
                "preview": {
                    "argv": [
                        "npx",
                        "skills",
                        "remove",
                        *expected_skills,
                        "--agent",
                        "codex",
                        "--global",
                        "--yes",
                    ]
                },
            }
        ],
    }
    material = {key: value for key, value in artifact["data"].items() if key != "materialHash"}
    assert set(material) == {"operations", "summary"}
    canonical = json.dumps(material, separators=(",", ":"), sort_keys=True)
    expected_hash = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
    assert artifact["data"]["materialHash"] == expected_hash


def test_install_plan_fallback_includes_the_repo_and_both_external_sources():
    result = run_setup(
        "install-plan",
        "--catalog",
        str(CATALOG),
        "--agent",
        "codex",
        "--scope",
        "project",
        "--json",
    )

    assert result.returncode == 0, result.stderr or result.stdout
    operations = json.loads(result.stdout)["data"]["operations"]
    assert [operation["preview"]["argv"][3] for operation in operations] == [
        "redhat-developer/rhdh-skill",
        "blader/humanizer",
        "mattpocock/skills",
    ]
    assert operations[0]["preview"]["argv"][4:6] == ["--skill", "*"]
    assert ["--skill", "humanizer"] == operations[1]["preview"]["argv"][4:6]
    assert ["--skill", "grilling"] == operations[2]["preview"]["argv"][4:6]


def test_apply_rejects_an_approval_for_different_plan_material(tmp_path):
    setup = load_setup_module()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    plan = setup.install_plan(catalog, "codex", "project", "https://skills.sh/p/test")
    plan["data"]["materialHash"] = "sha256:tampered"
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")

    result = run_setup(
        "apply",
        "--plan",
        str(plan_file),
        "--approved-material-hash",
        "sha256:another-plan",
        "--json",
    )

    assert result.returncode == 1
    assert json.loads(result.stdout)["errors"][0]["code"] == "PLAN_INVALID"


def test_apply_validates_every_operation_before_executing_any(monkeypatch):
    setup = load_setup_module()
    operations = [
        {
            "order": 1,
            "ownerSkill": "setup-rhdh-skills",
            "adapter": "skills-cli/v1",
            "operation": "skills.repository.install",
            "target": "project:codex",
            "preview": {"argv": ["npx", "skills", "add", "example/skills"]},
            "preconditions": [],
            "checks": [],
            "recovery": [],
        },
        {
            "order": 2,
            "ownerSkill": "setup-rhdh-skills",
            "adapter": "skills-cli/v1",
            "operation": "unexpected",
            "target": "project:codex",
            "preview": {"argv": ["powershell", "Invoke-Anything"]},
            "preconditions": [],
            "checks": [],
            "recovery": [],
        },
    ]
    material = {
        "summary": "Install skills",
        "operations": operations,
    }
    material_hash = setup.material_hash(material)
    plan = {
        "contract": "MutationPlan/v1",
        "id": "setup-install",
        "createdAt": "2026-08-10T12:00:00Z",
        "data": {**material, "materialHash": material_hash},
    }
    calls = []
    monkeypatch.setattr(
        setup.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs))
    )

    result, returncode = setup.apply_plan(plan, material_hash)

    assert returncode == 1
    assert result["errors"][0]["code"] == "OPERATION_NOT_ALLOWED"
    assert calls == []


def test_windows_npx_wrapper_resolves_to_node_without_a_shell(tmp_path, monkeypatch):
    setup = load_setup_module()
    node_dir = tmp_path / "nodejs"
    cli = node_dir / "node_modules" / "npm" / "bin" / "npx-cli.js"
    cli.parent.mkdir(parents=True)
    cli.write_text("", encoding="utf-8")
    npx = node_dir / "npx.cmd"
    npx.write_text("", encoding="utf-8")
    node = node_dir / "node.exe"
    node.write_text("", encoding="utf-8")

    monkeypatch.setattr(setup.sys, "platform", "win32")

    def fake_which(name):
        if name in {"npx", "npx.cmd"}:
            return str(npx)
        if name in {"node", "node.exe"}:
            return str(node)
        return None

    monkeypatch.setattr(setup.shutil, "which", fake_which)

    command = setup._resolve_npx_command(["npx", "skills", "add", "example/skills"])

    assert command == [
        str(node),
        str(cli),
        "skills",
        "add",
        "example/skills",
    ]


def test_apply_executes_argument_arrays_without_a_command_shell(monkeypatch):
    setup = load_setup_module()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    plan = setup.install_plan(
        catalog,
        agent="codex",
        scope="project",
        pack_url="https://skills.sh/p/rhdh-complete-test",
    )
    calls = []

    monkeypatch.setattr(
        setup,
        "_resolve_npx_command",
        lambda argv: ["node", "npx-cli.js", *argv[1:]],
    )

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="installed", stderr="")

    monkeypatch.setattr(setup.subprocess, "run", fake_run)

    receipt, returncode = setup.apply_plan(plan, plan["data"]["materialHash"])

    assert returncode == 0
    assert receipt["valid"] is True
    assert len(calls) == 1
    command, kwargs = calls[0]
    assert command == [
        "node",
        "npx-cli.js",
        "skills",
        "add",
        "https://skills.sh/p/rhdh-complete-test",
        "--agent",
        "codex",
        "--yes",
    ]
    assert kwargs["shell"] is False
    assert receipt["data"]["outcomes"] == [
        {
            "order": 1,
            "ownerSkill": "setup-rhdh-skills",
            "adapter": "skills-cli/v1",
            "operation": "skills.pack.install",
            "target": "project:codex",
            "status": "completed",
            "returnCode": 0,
            "stdout": "installed",
            "stderr": "",
        }
    ]
