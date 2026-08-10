#!/usr/bin/env python3
"""Produce the stable RhdhContext/v1 artifact for skill composition."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from rhdh import config  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _tool_status(probe: bool) -> dict[str, str]:
    tools = ("git", "gh", "node", "yarn", "uv", "podman", "docker", "oc")
    if not probe:
        return {tool: "not-probed" for tool in tools}
    return {tool: "installed" if shutil.which(tool) else "missing" for tool in tools}


def build_context(project_root: Path, probe_tools: bool) -> dict[str, Any]:
    previous_cwd = Path.cwd()
    try:
        os.chdir(project_root)
        info = config.get_config_info()
        repositories = {
            name: str(Path(value).resolve()) if value else None
            for name, value in info["resolved"].items()
        }
        configuration = {
            "dataDirectory": str(config.get_data_dir().resolve()),
            "projectConfig": str(config.get_project_config_path().resolve()),
            "userConfig": str(config.get_user_config_path().resolve()),
        }
    finally:
        os.chdir(previous_cwd)

    return {
        "contract": "RhdhContext/v1",
        "id": "rhdh-context",
        "createdAt": _now(),
        "data": {
            "repositories": repositories,
            "tools": _tool_status(probe_tools),
            "configuration": configuration,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve repositories, tools, and configuration into RhdhContext/v1."
    )
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root to inspect"
    )
    parser.add_argument(
        "--no-tool-probes", action="store_true", help="Skip PATH-based tool discovery"
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON output")
    args = parser.parse_args(argv)

    try:
        artifact = build_context(args.project_root.resolve(), not args.no_tool_probes)
    except (OSError, ValueError) as exc:
        error = {"valid": False, "errors": [{"code": "CONTEXT_ERROR", "message": str(exc)}]}
        json.dump(error, sys.stdout, indent=2 if args.json else None)
        sys.stdout.write("\n")
        return 1

    if args.json or not sys.stdout.isatty():
        json.dump(artifact, sys.stdout, indent=2 if args.json else None)
        sys.stdout.write("\n")
    else:
        configured = sum(value is not None for value in artifact["data"]["repositories"].values())
        print(f"RHDH context: {configured} repositories configured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
