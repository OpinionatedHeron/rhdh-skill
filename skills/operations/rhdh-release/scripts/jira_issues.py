"""Local Jira result enrichment adapter for the release CLI.

This module intentionally does not import or locate another skill. The public
composition seam is JiraQueryResult/v1; this adapter only preserves the release
CLI's standalone command-line behavior.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def _field(issue: dict, name: str, default=None):
    return issue.get("fields", {}).get(name, issue.get(name, default))


def _name(issue: dict, name: str) -> str:
    value = _field(issue, name)
    if isinstance(value, dict):
        return value.get("name", value.get("displayName", value.get("value", "")))
    return value if value is not None else ""


def _list_names(issue: dict, name: str) -> str:
    values = _field(issue, name, [])
    if not values:
        return ""
    return ", ".join(value.get("name", "") for value in values if isinstance(value, dict))


def _sprint(issue: dict) -> str:
    sprints = _field(issue, "customfield_10020", []) or []
    for state in ("active", "future"):
        for value in sprints:
            if isinstance(value, dict) and value.get("state") == state:
                return value.get("name", "")
    if sprints and isinstance(sprints[-1], dict):
        return sprints[-1].get("name", "")
    return ""


def _description(issue: dict) -> str:
    value = _field(issue, "description", "")
    if isinstance(value, str):
        return value
    parts: list[str] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            if node.get("type") == "text" and node.get("text"):
                parts.append(node["text"])
            for child in node.get("content", []):
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return " ".join(parts).strip()


EXTRACTORS = {
    "key": lambda i: i.get("key", ""),
    "summary": lambda i: _field(i, "summary", ""),
    "status": lambda i: _name(i, "status"),
    "assignee": lambda i: _name(i, "assignee"),
    "assignee_email": lambda i: (
        _field(i, "assignee", {}).get("emailAddress", "")
        if isinstance(_field(i, "assignee"), dict)
        else ""
    ),
    "reporter": lambda i: _name(i, "reporter"),
    "issuetype": lambda i: _name(i, "issuetype"),
    "priority": lambda i: _name(i, "priority"),
    "project": lambda i: (
        _field(i, "project", {}).get("key", "")
        if isinstance(_field(i, "project"), dict)
        else str(_field(i, "project", ""))
    ),
    "created": lambda i: _field(i, "created", ""),
    "updated": lambda i: _field(i, "updated", ""),
    "team": lambda i: _name(i, "customfield_10001"),
    "story_points": lambda i: _field(i, "customfield_10028"),
    "size": lambda i: _name(i, "customfield_10795"),
    "sprint": _sprint,
    "parent": lambda i: (
        _field(i, "parent", {}).get("key", "") if isinstance(_field(i, "parent"), dict) else ""
    ),
    "rn_type": lambda i: _name(i, "customfield_10785"),
    "fix_versions": lambda i: _list_names(i, "fixVersions"),
    "components": lambda i: _list_names(i, "components"),
    "labels": lambda i: ", ".join(_field(i, "labels", []) or []),
    "description": _description,
    "security": lambda i: _name(i, "security"),
    "feature_status": lambda i: _name(i, "customfield_10807"),
    "link_count": lambda i: len(_field(i, "issuelinks", []) or []),
}


def _acli_path() -> str | None:
    path = shutil.which("acli")
    if path:
        return path
    if sys.platform == "win32":
        candidate = Path.home() / ".path" / "acli.exe"
        if candidate.exists():
            return str(candidate)
    return None


def enrich(issues: list[dict]) -> list[dict]:
    """Fetch full fields for search results with the local acli executable."""
    acli = _acli_path()
    if not acli:
        raise RuntimeError("acli not found on PATH")

    enriched = []
    for issue in issues:
        key = issue.get("key", "")
        if not key:
            continue
        result = subprocess.run(
            [acli, "jira", "workitem", "view", key, "--fields", "*all", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if result.returncode == 0 and result.stdout:
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                data = issue
            enriched.append(data[0] if isinstance(data, list) else data)
        else:
            enriched.append(issue)
    return enriched


def select(issues: list[dict], fields: str) -> list[dict]:
    """Flatten issues to a comma-separated selection of friendly fields."""
    selected = [field.strip() for field in fields.split(",") if field.strip()]
    rows = []
    for issue in issues:
        row = {}
        for field in selected:
            extractor = EXTRACTORS.get(field)
            value = extractor(issue) if extractor else _field(issue, field, "")
            row[field] = value if value is not None else ""
        rows.append(row)
    return rows
