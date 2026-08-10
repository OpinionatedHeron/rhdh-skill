#!/usr/bin/env python3
"""Validate the promoted RHDH skill catalog and composition graph."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

CATALOG_PATH = Path("skills/engineering/setup-rhdh-skills/assets/catalog.json")
CONTRACTS_PATH = Path("skills/engineering/rhdh-context/scripts/artifact-contracts.json")
PROMOTED_CATEGORIES = ("engineering", "operations", "maintainers")
HOST_SKILL_PATHS = (".claude/skills", ".agents/skills", ".cursor/skills", ".codex/skills")
SHIPPED_SUFFIXES = {".md", ".py", ".sh", ".mjs"}
DUPLICATE_BLOCK_LINES = 25
ARTIFACT_FIELD_BULLET = re.compile(r"^[ \t]*[-*]\s+`([A-Za-z][A-Za-z0-9]*/v\d+)`\s*:\s*(.*)$")


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
        unquoted = value.strip("\"'")
        if unquoted.lower() in {"true", "false"}:
            result[key] = unquoted.lower() == "true"
        else:
            result[key] = unquoted
        index += 1
    return result


def _body(text: str) -> str:
    """Return the document with its frontmatter removed."""
    normalized = text.replace("\r\n", "\n")
    return re.sub(r"^---\n.*?\n---(?:\n|$)", "", normalized, count=1, flags=re.DOTALL)


def _mentions(body: str, term: str) -> bool:
    """Report whether the body names a skill or artifact rather than a longer token.

    ``/rhdh-jira`` and `` `rhdh-jira` `` both count; ``rhdh-jira-legacy`` does not.
    """
    return re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", body) is not None


def _artifact_list(
    entry: dict[str, Any], field: str, name: str, errors: list[dict[str, str]]
) -> list[Any]:
    """Read an artifact edge list, reporting malformed values instead of raising."""
    if field not in entry:
        return []
    value = entry[field]
    if not isinstance(value, list):
        errors.append(
            {
                "code": "ARTIFACT_LIST_TYPE",
                "message": (
                    f"{name}: {field} must be an array of artifact names, "
                    f"got {type(value).__name__}; use [] when the skill has none"
                ),
            }
        )
        return []
    return value


def _documented_artifact_fields(body: str) -> dict[str, set[str]]:
    """Collect the data fields a SKILL.md documents per artifact contract.

    Recognizes the house pattern ``- `Contract/v1`: `field`, `field`.`` including
    wrapped continuation lines. Bullets that name no field document none.
    """
    documented: dict[str, set[str]] = {}
    lines = body.split("\n")
    index = 0
    while index < len(lines):
        match = ARTIFACT_FIELD_BULLET.match(lines[index])
        if not match:
            index += 1
            continue
        artifact, remainder = match.groups()
        chunk = [remainder]
        index += 1
        while (
            index < len(lines)
            and lines[index].strip()
            and lines[index][:1].isspace()
            and not ARTIFACT_FIELD_BULLET.match(lines[index])
        ):
            chunk.append(lines[index])
            index += 1
        fields = set(re.findall(r"`([^`]+)`", " ".join(chunk)))
        if fields:
            documented.setdefault(artifact, set()).update(fields)
    return documented


def _shipped_files(skill_dir: Path) -> Iterator[Path]:
    """Yield the text files a skill ships, skipping build residue."""
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SHIPPED_SUFFIXES:
            continue
        if "__pycache__" in path.parts:
            continue
        yield path


def _duplicate_files(root: Path, skill_dirs: dict[str, Path]) -> list[tuple[str, str]]:
    """Return file pairs from different skills that ship the same content.

    Compares whole files and every window of ``DUPLICATE_BLOCK_LINES`` significant
    lines, so a copy that only differs in its header block is still reported.
    """
    groups: dict[str, set[tuple[str, str]]] = {}
    for name, skill_dir in skill_dirs.items():
        for path in _shipped_files(skill_dir):
            text = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            if not lines:
                continue
            owner = (name, path.relative_to(root).as_posix())
            keys = ["\n".join(lines)]
            keys.extend(
                "\n".join(lines[start : start + DUPLICATE_BLOCK_LINES])
                for start in range(len(lines) - DUPLICATE_BLOCK_LINES + 1)
            )
            for key in keys:
                digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
                groups.setdefault(digest, set()).add(owner)

    pairs: set[tuple[str, str]] = set()
    for group in groups.values():
        if len({name for name, _ in group}) < 2:
            continue
        for left, right in itertools.combinations(sorted(group), 2):
            if left[0] != right[0]:
                pairs.add((left[1], right[1]))
    return sorted(pairs)


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
        contracts = contract_payload.get("contracts", {})
    except (OSError, json.JSONDecodeError) as exc:
        contracts = {}
        errors.append({"code": "CONTRACTS_INVALID", "message": str(exc)})
    known_contracts = set(contracts)
    terminal_contracts = {
        artifact
        for artifact, spec in contracts.items()
        if isinstance(spec, dict) and spec.get("terminal") is True
    }
    produced_by: dict[str, list[str]] = {}
    consumed_by: dict[str, list[str]] = {}

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
        skill_text = skill_file.read_text(encoding="utf-8")
        body = _body(skill_text)
        frontmatter = _frontmatter(skill_text)
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
            remedy = (
                "set disable-model-invocation: true in the frontmatter"
                if invocation == "human"
                else "drop disable-model-invocation from the frontmatter"
            )
            errors.append(
                {
                    "code": "INVOCATION_MISMATCH",
                    "message": (
                        f"{name}: catalog={invocation}, frontmatter human={human_flag}; "
                        f"{remedy} or change the catalog invocation"
                    ),
                }
            )

        if not re.search(r"(?m)^##\s+Completion\s*$", body):
            errors.append(
                {
                    "code": "MISSING_COMPLETION",
                    "message": (
                        f"{skill_file.relative_to(root).as_posix()}: add a '## Completion' "
                        "section stating what the skill leaves behind when it finishes"
                    ),
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

        consumes = _artifact_list(entry, "consumes", name, errors)
        produces = _artifact_list(entry, "produces", name, errors)
        for artifact in [*consumes, *produces]:
            if not isinstance(artifact, str) or not re.fullmatch(
                r"[A-Za-z][A-Za-z0-9]*/v\d+", artifact
            ):
                errors.append({"code": "ARTIFACT_NAME", "message": f"{name}: {artifact!r}"})
            elif artifact not in known_contracts:
                errors.append({"code": "ARTIFACT_UNDECLARED", "message": f"{name}: {artifact}"})
        for artifact in consumes:
            if isinstance(artifact, str):
                consumed_by.setdefault(artifact, []).append(name)
        for artifact in produces:
            if isinstance(artifact, str):
                produced_by.setdefault(artifact, []).append(name)

        for dependency in entry.get("requiresSkills") or []:
            if isinstance(dependency, str) and not _mentions(body, dependency):
                errors.append(
                    {
                        "code": "DEPENDENCY_NOT_DOCUMENTED",
                        "message": (
                            f"{name}: requiresSkills declares {dependency} but SKILL.md never "
                            f"names it; document when to invoke {dependency} and what it returns, "
                            "or drop the dependency"
                        ),
                    }
                )

        for artifact in produces:
            if isinstance(artifact, str) and not _mentions(body, artifact):
                errors.append(
                    {
                        "code": "ARTIFACT_NOT_DOCUMENTED",
                        "message": (
                            f"{name}: produces {artifact} but SKILL.md never names it; document "
                            "which route emits it, or drop it from produces"
                        ),
                    }
                )

        for artifact, fields in _documented_artifact_fields(body).items():
            required = contracts.get(artifact, {})
            required = required.get("requiredData", []) if isinstance(required, dict) else []
            missing = [field for field in required if field not in fields]
            if missing:
                errors.append(
                    {
                        "code": "ARTIFACT_FIELDS_MISMATCH",
                        "message": (
                            f"{name}: documented fields for {artifact} omit required "
                            f"{', '.join(missing)}; document the contract fields or amend "
                            f"{CONTRACTS_PATH.as_posix()}"
                        ),
                    }
                )

        for path in _shipped_files(skill_dir):
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

    for artifact, consumers in sorted(consumed_by.items()):
        if artifact not in produced_by:
            errors.append(
                {
                    "code": "DANGLING_ARTIFACT_EDGE",
                    "message": (
                        f"{artifact} is consumed by {', '.join(sorted(consumers))} but produced "
                        "by no skill; add the producing skill or drop the consumes entry"
                    ),
                }
            )
    for artifact, producers in sorted(produced_by.items()):
        if artifact not in consumed_by and artifact not in terminal_contracts:
            errors.append(
                {
                    "code": "DANGLING_ARTIFACT_EDGE",
                    "message": (
                        f"{artifact} is produced by {', '.join(sorted(producers))} but consumed "
                        "by no skill; add the consuming skill, drop the produces entry, or mark "
                        f'the contract "terminal": true in {CONTRACTS_PATH.as_posix()}'
                    ),
                }
            )

    skill_dirs: dict[str, Path] = {}
    for category in PROMOTED_CATEGORIES:
        for skill_file in (root / "skills" / category).glob("*/SKILL.md"):
            skill_dirs[skill_file.parent.name] = skill_file.parent
    for left, right in _duplicate_files(root, skill_dirs):
        errors.append(
            {
                "code": "DUPLICATE_FILE",
                "message": (
                    f"{left} and {right} ship the same content; extract it into a foundation "
                    "skill both invoke by name, or delete the copy and cross the owner's seam"
                ),
            }
        )

    discovered = set(skill_dirs)
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
