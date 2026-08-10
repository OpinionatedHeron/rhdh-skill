#!/usr/bin/env python3
"""Inspect RHDH skill setup and create approval-bound installation plans."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_CATALOG = Path(__file__).parent.parent / "assets" / "catalog.json"
HOST_LAYOUTS = (
    Path(".agents/skills"),
    Path(".claude/skills"),
    Path(".cursor/skills"),
    Path(".codex/skills"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_catalog(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if payload.get("schemaVersion") != 1 or not isinstance(payload.get("skills"), list):
        raise ValueError(f"Unsupported catalog schema: {path}")
    return payload


def _skill_roots(home: Path, project_root: Path) -> list[Path]:
    roots: list[Path] = []
    for base in (project_root, home):
        roots.extend(base / relative for relative in HOST_LAYOUTS)
    return roots


def _installed_skills(home: Path, project_root: Path) -> dict[str, str]:
    installed: dict[str, str] = {}
    for root in _skill_roots(home, project_root):
        if not root.is_dir():
            continue
        candidates = [*root.glob("*/SKILL.md"), *root.glob("*/*/SKILL.md")]
        for skill_file in candidates:
            installed.setdefault(skill_file.parent.name, str(skill_file.resolve()))
    return installed


def _tool_status(probe: bool) -> dict[str, str]:
    tools = ("npx", "gh", "acli", "gog", "oc", "podman", "docker")
    if not probe:
        return {name: "not-probed" for name in tools}
    return {name: "installed" if shutil.which(name) else "missing" for name in tools}


def setup_status(
    catalog: dict[str, Any], home: Path, project_root: Path, probe_tools: bool
) -> dict[str, Any]:
    installed = _installed_skills(home, project_root)
    promoted = [entry["name"] for entry in catalog["skills"]]
    external = [entry["name"] for entry in catalog["pack"]["requiredExternalSkills"]]
    required = [*promoted, *external]
    missing = sorted(name for name in required if name not in installed)
    external_status = {
        name: "installed" if name in installed else "missing" for name in sorted(external)
    }
    return {
        "contract": "SetupStatus/v1",
        "id": "setup-status",
        "createdAt": _now(),
        "data": {
            "installedSkills": sorted(installed),
            "installedSkillLocations": installed,
            "missingSkills": missing,
            "requiredExternalSkills": external_status,
            "capabilities": {
                "tools": _tool_status(probe_tools),
                "projectConfiguration": "present"
                if (project_root / ".rhdh" / "config.json").is_file()
                else "missing",
                "userConfiguration": "present"
                if (home / ".config" / "rhdh-skill" / "config.json").is_file()
                else "missing",
            },
        },
    }


def _canonical_material(material: dict[str, Any]) -> str:
    return json.dumps(material, separators=(",", ":"), sort_keys=True)


def _material_hash(material: dict[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_material(material).encode()).hexdigest()
    return f"sha256:{digest}"


def _install_flags(agent: str, scope: str) -> list[str]:
    flags = ["--agent", agent]
    if scope == "global":
        flags.append("--global")
    flags.append("--yes")
    return flags


def _recovery_argv(skill_names: list[str], agent: str, scope: str) -> list[str]:
    return [
        "npx",
        "skills",
        "remove",
        *sorted(skill_names),
        "--agent",
        agent,
        *(["--global"] if scope == "global" else []),
        "--yes",
    ]


def _install_operation(
    *,
    order: int,
    operation: str,
    argv: list[str],
    source: str,
    target: str,
    skill_names: list[str],
    agent: str,
    scope: str,
    catalog_schema: int,
) -> dict[str, Any]:
    return {
        "order": order,
        "ownerSkill": "setup-rhdh-skills",
        "adapter": "skills-cli/v1",
        "operation": operation,
        "target": target,
        "preview": {"argv": argv, "source": source},
        "preconditions": [
            {"check": "tool.available", "target": "npx", "required": True},
            {"check": "catalog.schema", "expected": catalog_schema, "required": True},
        ],
        "checks": [{"check": "skills.discovered", "expected": sorted(skill_names)}],
        "recovery": [
            {
                "adapter": "skills-cli/v1",
                "operation": "skills.remove",
                "preview": {"argv": _recovery_argv(skill_names, agent, scope)},
            }
        ],
    }


def install_plan(
    catalog: dict[str, Any], agent: str, scope: str, pack_url: str | None
) -> dict[str, Any]:
    pack = catalog["pack"]
    resolved_pack_url = pack_url or os.environ.get("RHDH_SKILLS_PACK_URL") or pack.get("url")
    flags = _install_flags(agent, scope)
    target = f"{scope}:{agent}"
    operations: list[dict[str, Any]] = []
    promoted_names = [entry["name"] for entry in catalog["skills"]]
    external_names = [entry["name"] for entry in pack["requiredExternalSkills"]]

    if resolved_pack_url:
        operations.append(
            _install_operation(
                order=1,
                operation="skills.pack.install",
                argv=["npx", "skills", "add", resolved_pack_url, *flags],
                source=resolved_pack_url,
                target=target,
                skill_names=[*promoted_names, *external_names],
                agent=agent,
                scope=scope,
                catalog_schema=catalog["schemaVersion"],
            )
        )
    else:
        operations.append(
            _install_operation(
                order=1,
                operation="skills.repository.install",
                argv=[
                    "npx",
                    "skills",
                    "add",
                    pack["source"],
                    "--skill",
                    "*",
                    *flags,
                ],
                source=pack["source"],
                target=target,
                skill_names=promoted_names,
                agent=agent,
                scope=scope,
                catalog_schema=catalog["schemaVersion"],
            )
        )
        by_source: dict[str, list[str]] = {}
        for dependency in pack["requiredExternalSkills"]:
            by_source.setdefault(dependency["source"], []).append(dependency["name"])
        for source, names in sorted(by_source.items()):
            skill_flags: list[str] = []
            for name in sorted(names):
                skill_flags.extend(["--skill", name])
            operations.append(
                _install_operation(
                    order=len(operations) + 1,
                    operation="skills.dependencies.install",
                    argv=["npx", "skills", "add", source, *skill_flags, *flags],
                    source=source,
                    target=target,
                    skill_names=names,
                    agent=agent,
                    scope=scope,
                    catalog_schema=catalog["schemaVersion"],
                )
            )

    material = {
        "summary": f"Install the complete RHDH skill set for {agent} ({scope})",
        "operations": operations,
    }
    return {
        "contract": "MutationPlan/v1",
        "id": "setup-install",
        "createdAt": _now(),
        "data": {**material, "materialHash": _material_hash(material)},
    }


def _operation_error(operation: Any, index: int) -> dict[str, str] | None:
    if not isinstance(operation, dict):
        return {
            "code": "OPERATION_NOT_ALLOWED",
            "message": f"operation {index} must be an object",
        }
    preview = operation.get("preview")
    argv = preview.get("argv") if isinstance(preview, dict) else None
    allowed_operations = {
        "skills.pack.install",
        "skills.repository.install",
        "skills.dependencies.install",
    }
    required_fields = {
        "order",
        "ownerSkill",
        "adapter",
        "operation",
        "target",
        "preview",
        "preconditions",
        "checks",
        "recovery",
    }
    if (
        set(operation) != required_fields
        or not isinstance(operation.get("order"), int)
        or isinstance(operation.get("order"), bool)
        or operation["order"] < 1
        or operation.get("ownerSkill") != "setup-rhdh-skills"
        or operation.get("adapter") != "skills-cli/v1"
        or operation.get("operation") not in allowed_operations
        or not isinstance(operation.get("target"), str)
        or not operation["target"]
        or not isinstance(preview, dict)
        or not isinstance(operation.get("preconditions"), list)
        or not isinstance(operation.get("checks"), list)
        or not isinstance(operation.get("recovery"), list)
        or not isinstance(argv, list)
        or len(argv) < 4
        or argv[:3] != ["npx", "skills", "add"]
        or not all(isinstance(item, str) and "\x00" not in item for item in argv)
        or not argv[3]
        or argv[3].startswith("-")
    ):
        return {
            "code": "OPERATION_NOT_ALLOWED",
            "message": f"operation {index} is not an allowed npx skills add operation",
        }
    return None


def _validate_plan(plan: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(plan, dict) or plan.get("contract") != "MutationPlan/v1":
        return None, {
            "valid": False,
            "errors": [{"code": "PLAN_INVALID", "message": "unsupported mutation plan"}],
        }
    data = plan.get("data")
    if not isinstance(data, dict):
        return None, {
            "valid": False,
            "errors": [{"code": "PLAN_INVALID", "message": "plan data must be an object"}],
        }

    material_hash = data.get("materialHash")
    material = {key: value for key, value in data.items() if key != "materialHash"}
    if (
        set(material) != {"summary", "operations"}
        or not isinstance(material.get("summary"), str)
        or not isinstance(material.get("operations"), list)
    ):
        return None, {
            "valid": False,
            "errors": [
                {"code": "PLAN_INVALID", "message": "plan is missing required material fields"}
            ],
        }
    if not material["operations"] or material_hash != _material_hash(material):
        return None, {
            "valid": False,
            "errors": [{"code": "PLAN_INVALID", "message": "plan content does not match its hash"}],
        }

    for index, operation in enumerate(material["operations"], start=1):
        error = _operation_error(operation, index)
        if error:
            return None, {"valid": False, "errors": [error]}
    return data, None


def _resolve_npx_command(argv: list[str]) -> list[str]:
    """Resolve npx without passing plan material through a command shell."""
    npx = (
        shutil.which("npx.cmd") or shutil.which("npx")
        if sys.platform == "win32"
        else shutil.which("npx")
    )
    if not npx:
        raise OSError("npx not found on PATH")

    npx_path = Path(npx)
    if sys.platform != "win32" or npx_path.suffix.lower() not in {".cmd", ".bat"}:
        return [npx, *argv[1:]]

    node = shutil.which("node.exe") or shutil.which("node")
    candidates = [
        npx_path.parent / "node_modules" / "npm" / "bin" / "npx-cli.js",
        npx_path.resolve().parent / "node_modules" / "npm" / "bin" / "npx-cli.js",
    ]
    npx_cli = next((candidate for candidate in candidates if candidate.is_file()), None)
    if not node or not npx_cli:
        raise OSError("cannot safely resolve the Windows npx wrapper to node and npx-cli.js")
    return [node, str(npx_cli), *argv[1:]]


def apply_plan(plan: dict[str, Any], approved_hash: str) -> tuple[dict[str, Any], int]:
    data, validation_error = _validate_plan(plan)
    if validation_error:
        return validation_error, 1
    assert data is not None
    operations = data["operations"]
    material_hash = data["materialHash"]
    if approved_hash != material_hash:
        return {
            "valid": False,
            "errors": [
                {
                    "code": "APPROVAL_MISMATCH",
                    "message": "approved hash does not match the current mutation plan",
                }
            ],
        }, 1

    outcomes: list[dict[str, Any]] = []
    for operation in operations:
        argv = operation["preview"]["argv"]
        command = _resolve_npx_command(argv)
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            shell=False,
        )
        outcomes.append(
            {
                "order": operation["order"],
                "ownerSkill": operation["ownerSkill"],
                "adapter": operation["adapter"],
                "operation": operation["operation"],
                "target": operation.get("target"),
                "status": "completed" if completed.returncode == 0 else "failed",
                "returnCode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
        if completed.returncode != 0:
            break

    for operation in operations[len(outcomes) :]:
        outcomes.append(
            {
                "order": operation["order"],
                "ownerSkill": operation["ownerSkill"],
                "adapter": operation["adapter"],
                "operation": operation["operation"],
                "target": operation["target"],
                "status": "skipped",
                "returnCode": None,
                "stdout": "",
                "stderr": "not attempted after an earlier operation failed",
            }
        )

    succeeded = all(outcome["status"] == "completed" for outcome in outcomes)
    return {
        "contract": "MutationReceipt/v1",
        "id": "setup-install-receipt",
        "createdAt": _now(),
        "data": {
            "planId": plan.get("id"),
            "materialHash": material_hash,
            "outcomes": outcomes,
        },
        "valid": succeeded,
    }, 0 if succeeded else 1


def _add_shared_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--catalog", type=Path, default=DEFAULT_CATALOG, help="Catalog JSON to inspect"
    )


def _emit(payload: dict[str, Any], force_json: bool) -> None:
    if force_json or not sys.stdout.isatty():
        json.dump(payload, sys.stdout, indent=2 if force_json else None)
        sys.stdout.write("\n")
    elif payload.get("valid", True):
        print(payload.get("data", {}).get("summary", "Setup check complete"))
    else:
        for error in payload.get("errors", []):
            print(f"{error['code']}: {error['message']}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect, plan, and apply setup for the complete RHDH skills collection."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Report installed skills and setup capabilities")
    _add_shared_paths(doctor)
    doctor.add_argument("--home", type=Path, default=Path.home(), help="User home to inspect")
    doctor.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root to inspect"
    )
    doctor.add_argument(
        "--no-tool-probes", action="store_true", help="Skip PATH-based tool detection"
    )
    doctor.add_argument("--json", action="store_true", help="Emit structured JSON output")

    plan = subparsers.add_parser("install-plan", help="Create an approval-bound install plan")
    _add_shared_paths(plan)
    plan.add_argument("--pack-url", help="Override the catalog pack URL")
    plan.add_argument("--agent", required=True, help="skills CLI agent identifier")
    plan.add_argument(
        "--scope", choices=("project", "global"), default="global", help="Installation scope"
    )
    plan.add_argument("--json", action="store_true", help="Emit structured JSON output")

    apply_parser = subparsers.add_parser("apply", help="Apply an explicitly approved install plan")
    apply_parser.add_argument("--plan", type=Path, required=True, help="MutationPlan JSON file")
    apply_parser.add_argument(
        "--approved-material-hash", required=True, help="Hash approved by the user"
    )
    apply_parser.add_argument("--json", action="store_true", help="Emit structured JSON output")

    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            catalog = _load_catalog(args.catalog)
            payload = setup_status(
                catalog, args.home, args.project_root, probe_tools=not args.no_tool_probes
            )
            code = 0 if not payload["data"]["missingSkills"] else 1
        elif args.command == "install-plan":
            catalog = _load_catalog(args.catalog)
            payload = install_plan(catalog, args.agent, args.scope, args.pack_url)
            code = 0
        else:
            plan_payload = json.loads(args.plan.read_text(encoding="utf-8"))
            payload, code = apply_plan(plan_payload, args.approved_material_hash)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        payload = {"valid": False, "errors": [{"code": "SETUP_INPUT", "message": str(exc)}]}
        code = 1

    _emit(payload, args.json)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
