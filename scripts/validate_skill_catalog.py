#!/usr/bin/env python3
"""Validate the promoted RHDH skill catalog and composition graph."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

CATALOG_PATH = Path("skills/engineering/setup-rhdh-skills/assets/catalog.json")
CONTRACTS_PATH = Path("skills/engineering/rhdh-context/scripts/artifact-contracts.json")
PROMOTED_CATEGORIES = ("engineering", "operations", "maintainers")
HOST_SKILL_PATHS = (".claude/skills", ".agents/skills", ".cursor/skills")


def _frontmatter(text: str) -> dict[str, Any]:
    """Parse the small frontmatter subset used by catalog validation."""
    normalized = text.replace("\r\n", "\n")
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", normalized, re.DOTALL)
    if not match:
        return {}

    result: dict[str, Any] = {}
    lines = match.group(1).splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        scalar = re.match(r"^([a-zA-Z][a-zA-Z0-9-]*):\s*(.*?)\s*$", line)
        if not scalar:
            index += 1
            continue
        key, value = scalar.groups()
        if value in {"|", ">", "|-", ">-"}:
            block: list[str] = []
            index += 1
            while index < len(lines) and (not lines[index].strip() or lines[index][0].isspace()):
                block.append(lines[index].strip())
                index += 1
            result[key] = "\n".join(block).strip()
            continue
        if value.lower() in {"true", "false"}:
            result[key] = value.lower() == "true"
        else:
            result[key] = value.strip("\"'")
        index += 1
    return result


def _find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, path: list[str]) -> list[str] | None:
        if node in visiting:
            return path[path.index(node) :] + [node]
        if node in visited:
            return None
        visiting.add(node)
        for dependency in graph.get(node, []):
            if dependency not in graph:
                continue
            cycle = visit(dependency, [*path, dependency])
            if cycle:
                return cycle
        visiting.remove(node)
        visited.add(node)
        return None

    for name in graph:
        cycle = visit(name, [name])
        if cycle:
            return cycle
    return None


def _validate_internal_skills(root: Path, errors: list[dict[str, str]]) -> None:
    """Require drafts to declare the nested internal metadata gate."""
    draft_root = root / "internal" / "in-progress"
    for skill_file in draft_root.glob("*/SKILL.md"):
        content = skill_file.read_text(encoding="utf-8")
        frontmatter_match = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", content, re.DOTALL)
        frontmatter = frontmatter_match.group(1) if frontmatter_match else ""
        metadata_match = re.search(
            r"(?m)^metadata:\s*$\r?\n(?P<body>(?:^[ \t]+[^\r\n]*(?:\r?\n|$))*)",
            frontmatter,
        )
        metadata = metadata_match.group("body") if metadata_match else ""
        is_internal = bool(re.search(r"(?m)^[ \t]+internal:\s*true\s*$", metadata))
        if not is_internal:
            errors.append({"code": "IN_PROGRESS_PUBLIC", "message": str(skill_file)})


def _validate_local_links(
    root: Path, document: Path, content: str, errors: list[dict[str, str]]
) -> None:
    """Validate real skill/workflow links without interpreting template examples."""
    relative = document.relative_to(root)
    if document.name != "SKILL.md" and "workflows" not in relative.parts:
        return
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", content):
        target = match.group(1).strip().split("#", 1)[0]
        if (
            not target
            or "://" in target
            or target.startswith(("/", "#", "mailto:"))
            or "<" in target
        ):
            continue
        resolved = (document.parent / target).resolve()
        if not resolved.exists():
            errors.append(
                {
                    "code": "LINK_MISSING",
                    "message": f"{relative.as_posix()} -> {target}",
                }
            )


def validate_repository(root: Path) -> dict[str, Any]:
    """Return an observable validation report for a repository checkout."""
    root = root.resolve()
    catalog_file = root / CATALOG_PATH
    errors: list[dict[str, str]] = []

    if not catalog_file.is_file():
        return {
            "valid": False,
            "errors": [{"code": "CATALOG_MISSING", "message": str(catalog_file)}],
            "promotedSkills": [],
            "humanInvokedSkills": [],
            "requiredExternalSkills": [],
        }

    try:
        catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "valid": False,
            "errors": [{"code": "CATALOG_INVALID", "message": str(exc)}],
            "promotedSkills": [],
            "humanInvokedSkills": [],
            "requiredExternalSkills": [],
        }

    if catalog.get("schemaVersion") != 1:
        errors.append({"code": "SCHEMA_VERSION", "message": "schemaVersion must be 1"})

    entries = catalog.get("skills")
    if not isinstance(entries, list):
        entries = []
        errors.append({"code": "SKILLS_TYPE", "message": "skills must be an array"})

    promoted_names: list[str] = []
    human_names: list[str] = []
    entry_by_name: dict[str, dict[str, Any]] = {}
    external_entries = catalog.get("pack", {}).get("requiredExternalSkills", [])
    external_names = [item.get("name") for item in external_entries if isinstance(item, dict)]
    external_set = {name for name in external_names if isinstance(name, str)}

    catalog_names = {
        entry.get("name")
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }
    try:
        contract_payload = json.loads((root / CONTRACTS_PATH).read_text(encoding="utf-8"))
        known_contracts = set(contract_payload.get("contracts", {}))
    except (OSError, json.JSONDecodeError) as exc:
        known_contracts = set()
        errors.append({"code": "CONTRACTS_INVALID", "message": str(exc)})

    for entry in entries:
        if not isinstance(entry, dict):
            errors.append({"code": "SKILL_ENTRY_TYPE", "message": repr(entry)})
            continue
        name = entry.get("name")
        category = entry.get("category")
        invocation = entry.get("invocation")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            errors.append({"code": "SKILL_NAME", "message": repr(name)})
            continue
        if name in entry_by_name:
            errors.append({"code": "SKILL_DUPLICATE", "message": name})
            continue
        entry_by_name[name] = entry
        promoted_names.append(name)
        if category not in PROMOTED_CATEGORIES:
            errors.append({"code": "SKILL_CATEGORY", "message": f"{name}: {category}"})
            continue
        if invocation not in {"human", "model"}:
            errors.append({"code": "SKILL_INVOCATION", "message": f"{name}: {invocation}"})
        if invocation == "human":
            human_names.append(name)

        skill_dir = root / "skills" / category / name
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            errors.append({"code": "SKILL_MISSING", "message": str(skill_file)})
            continue
        frontmatter = _frontmatter(skill_file.read_text(encoding="utf-8"))
        if frontmatter.get("name") != name:
            errors.append(
                {
                    "code": "FRONTMATTER_NAME",
                    "message": f"{skill_file}: expected {name!r}",
                }
            )
        description = frontmatter.get("description")
        if not isinstance(description, str) or not 0 < len(description) <= 1024:
            errors.append({"code": "FRONTMATTER_DESCRIPTION", "message": str(skill_file)})
        human_flag = frontmatter.get("disable-model-invocation") is True
        if human_flag != (invocation == "human"):
            errors.append(
                {
                    "code": "INVOCATION_MISMATCH",
                    "message": f"{name}: catalog={invocation}, frontmatter human={human_flag}",
                }
            )

        harness_file = skill_dir / "agents" / "openai.yaml"
        if not harness_file.is_file():
            errors.append({"code": "HARNESS_METADATA_MISSING", "message": str(harness_file)})
        else:
            harness = harness_file.read_text(encoding="utf-8")
            if not re.search(r"(?m)^\s{2}display_name:\s*\S", harness) or not re.search(
                r"(?m)^\s{2}short_description:\s*\S", harness
            ):
                errors.append({"code": "HARNESS_METADATA_INVALID", "message": str(harness_file)})
            implicit_disabled = bool(
                re.search(
                    r"(?ms)^policy:\s*$.*?^\s{2}allow_implicit_invocation:\s*false\s*$",
                    harness,
                )
            )
            if implicit_disabled != (invocation == "human"):
                errors.append(
                    {
                        "code": "HARNESS_INVOCATION_MISMATCH",
                        "message": f"{name}: catalog={invocation}, implicit disabled={implicit_disabled}",
                    }
                )

        for artifact in [*entry.get("consumes", []), *entry.get("produces", [])]:
            if not isinstance(artifact, str) or not re.fullmatch(
                r"[A-Za-z][A-Za-z0-9]*/v\d+", artifact
            ):
                errors.append({"code": "ARTIFACT_NAME", "message": f"{name}: {artifact!r}"})
            elif artifact not in known_contracts:
                errors.append({"code": "ARTIFACT_UNDECLARED", "message": f"{name}: {artifact}"})

        for path in skill_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".md", ".py", ".sh", ".mjs"}:
                continue
            content = path.read_text(encoding="utf-8", errors="replace").replace("\\", "/")
            _validate_local_links(root, path, content, errors)
            if name != "setup-rhdh-skills":
                for host_path in HOST_SKILL_PATHS:
                    if host_path in content:
                        errors.append(
                            {
                                "code": "HOST_LAYOUT_LEAK",
                                "message": f"{path.relative_to(root)} contains {host_path}",
                            }
                        )
            for other_name in catalog_names:
                if other_name == name:
                    continue
                cross_path_patterns = (
                    f"../{other_name}/",
                    f"skills/engineering/{other_name}/",
                    f"skills/operations/{other_name}/",
                    f"skills/maintainers/{other_name}/",
                )
                if any(pattern in content for pattern in cross_path_patterns):
                    errors.append(
                        {
                            "code": "CROSS_SKILL_PATH",
                            "message": f"{path.relative_to(root)} references {other_name} by path",
                        }
                    )

    internal_names = set(entry_by_name)
    graph: dict[str, list[str]] = {}
    for name, entry in entry_by_name.items():
        dependencies = entry.get("requiresSkills", [])
        optional_dependencies = entry.get("optionalSkills", [])
        external_dependencies = entry.get("requiresExternalSkills", [])
        if not isinstance(dependencies, list):
            errors.append({"code": "REQUIRES_TYPE", "message": name})
            dependencies = []
        if not isinstance(optional_dependencies, list):
            errors.append({"code": "OPTIONAL_REQUIRES_TYPE", "message": name})
            optional_dependencies = []
        if not isinstance(external_dependencies, list):
            errors.append({"code": "EXTERNAL_REQUIRES_TYPE", "message": name})
            external_dependencies = []
        required_names = [dep for dep in dependencies if isinstance(dep, str)]
        optional_names = [dep for dep in optional_dependencies if isinstance(dep, str)]
        graph[name] = [*required_names, *optional_names]
        for dependency in graph[name]:
            if dependency not in internal_names:
                errors.append({"code": "DEPENDENCY_MISSING", "message": f"{name} -> {dependency}"})
        for dependency in external_dependencies:
            if dependency not in external_set:
                errors.append(
                    {"code": "EXTERNAL_DEPENDENCY_MISSING", "message": f"{name} -> {dependency}"}
                )

    cycle = _find_cycle(graph) if graph else None
    if cycle:
        errors.append({"code": "DEPENDENCY_CYCLE", "message": " -> ".join(cycle)})

    discovered: set[str] = set()
    for category in PROMOTED_CATEGORIES:
        for skill_file in (root / "skills" / category).glob("*/SKILL.md"):
            discovered.add(skill_file.parent.name)
    undeclared = sorted(discovered - internal_names)
    missing = sorted(internal_names - discovered)
    if undeclared:
        errors.append({"code": "SKILLS_UNDECLARED", "message": ", ".join(undeclared)})
    if missing:
        errors.append({"code": "SKILLS_NOT_DISCOVERED", "message": ", ".join(missing)})

    legacy = sorted(path.parent.name for path in (root / "skills").glob("*/SKILL.md"))
    if legacy:
        errors.append({"code": "LEGACY_SKILL_LAYOUT", "message": ", ".join(legacy)})

    _validate_internal_skills(root, errors)

    return {
        "valid": not errors,
        "errors": errors,
        "promotedSkills": sorted(promoted_names),
        "humanInvokedSkills": sorted(human_names),
        "requiredExternalSkills": sorted(external_set),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the categorized RHDH skill catalog and dependency graph."
    )
    parser.add_argument("--root", default=".", help="Repository root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Emit the full JSON report")
    args = parser.parse_args(argv)

    report = validate_repository(Path(args.root))
    if args.json or not sys.stdout.isatty():
        json.dump(report, sys.stdout, indent=2 if args.json else None)
        sys.stdout.write("\n")
    elif report["valid"]:
        print(f"Skill catalog valid: {len(report['promotedSkills'])} promoted skills")
    else:
        print("Skill catalog invalid:", file=sys.stderr)
        for error in report["errors"]:
            print(f"- {error['code']}: {error['message']}", file=sys.stderr)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
