#!/usr/bin/env python3
"""Detect whether Matt Pocock's grilling skill is installed (verify only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MINIMAL_INSTALL = "npx skills@latest add mattpocock/skills --skill grilling -g -y"
RECOMMENDED_INSTALL = "npx skills@latest add mattpocock/skills --all -g"

SKILL_RELATIVE = Path("grilling") / "SKILL.md"


def grilling_search_paths(
    home: Path | None = None,
    cwd: Path | None = None,
) -> list[Path]:
    """Return candidate paths for grilling/SKILL.md (user + project-local)."""
    home = home if home is not None else Path.home()
    cwd = cwd if cwd is not None else Path.cwd()
    return [
        home / ".claude" / "skills" / SKILL_RELATIVE,
        home / ".agents" / "skills" / SKILL_RELATIVE,
        home / ".cursor" / "skills" / SKILL_RELATIVE,
        cwd / ".claude" / "skills" / SKILL_RELATIVE,
        cwd / ".agents" / "skills" / SKILL_RELATIVE,
        cwd / ".cursor" / "skills" / SKILL_RELATIVE,
    ]


def find_grilling(
    home: Path | None = None,
    cwd: Path | None = None,
) -> Path | None:
    """Return the first existing grilling/SKILL.md path, or None."""
    for path in grilling_search_paths(home=home, cwd=cwd):
        if path.is_file():
            return path.resolve()
    return None


def check_grilling(
    home: Path | None = None,
    cwd: Path | None = None,
) -> dict:
    """Build a results dict for grilling skill detection."""
    found = find_grilling(home=home, cwd=cwd)
    return {
        "grilling_found": found is not None,
        "grilling_path": str(found) if found else None,
        "minimal_install": MINIMAL_INSTALL,
        "recommended_install": RECOMMENDED_INSTALL,
        "overall": "pass" if found else "fail",
    }


def _output(results: dict, as_json: bool) -> None:
    """Print results in JSON or human-readable format."""
    if as_json:
        json.dump(results, sys.stdout, indent=2)
        print()
        return

    print("=" * 50)
    print("skill-maker Setup Check")
    print("=" * 50)
    print()
    print("Hard prerequisite: Matt Pocock's `grilling` skill.")
    print("Create/interview paths require it for interview cadence.")
    print()

    if results["grilling_found"]:
        print(f"  [PASS] grilling found: {results['grilling_path']}")
    else:
        print("  [FAIL] grilling skill not found")
        print("         Looked for grilling/SKILL.md under:")
        print("           ~/.claude/skills/")
        print("           ~/.agents/skills/")
        print("           ~/.cursor/skills/")
        print("           <cwd>/.claude/skills/")
        print("           <cwd>/.agents/skills/")
        print("           <cwd>/.cursor/skills/")
        print()
        print("  Install (after user confirms):")
        print(f"    Minimal (gate installs this): {MINIMAL_INSTALL}")
        print(f"    Recommended (full Matt pack): {RECOMMENDED_INSTALL}")
        print()
        print("  This script detects only — it does not install.")

    print()
    print(f"Overall: {results['overall'].upper()}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Detect whether Matt Pocock's grilling skill is installed. "
            "Verify only — does not install."
        )
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args(argv)

    results = check_grilling()
    _output(results, args.json)
    return 0 if results["overall"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
