#!/usr/bin/env python3
"""Detect the humanizer skill for rhdh-pr-review draft gates."""

import argparse
import json
import sys
from pathlib import Path

MINIMAL_HUMANIZER_INSTALL = "npx skills@latest add blader/humanizer -g -y"
RECOMMENDED_HUMANIZER_INSTALL = "npx skills@latest add blader/humanizer --global"
HUMANIZER_SKILL_RELATIVE = Path("humanizer") / "SKILL.md"


def humanizer_search_paths(home=None, cwd=None):
    """Return candidate paths for humanizer/SKILL.md (user + project-local)."""
    home = Path.home() if home is None else Path(home)
    cwd = Path.cwd() if cwd is None else Path(cwd)
    return [
        home / ".claude" / "skills" / HUMANIZER_SKILL_RELATIVE,
        home / ".agents" / "skills" / HUMANIZER_SKILL_RELATIVE,
        home / ".cursor" / "skills" / HUMANIZER_SKILL_RELATIVE,
        cwd / ".claude" / "skills" / HUMANIZER_SKILL_RELATIVE,
        cwd / ".agents" / "skills" / HUMANIZER_SKILL_RELATIVE,
        cwd / ".cursor" / "skills" / HUMANIZER_SKILL_RELATIVE,
    ]


def find_humanizer(home=None, cwd=None):
    """Return the first existing humanizer/SKILL.md path, or None."""
    for path in humanizer_search_paths(home=home, cwd=cwd):
        if path.is_file():
            return path.resolve()
    return None


def check_humanizer(home=None, cwd=None):
    """Build a results dict for humanizer skill detection."""
    found = find_humanizer(home=home, cwd=cwd)
    return {
        "humanizer_found": found is not None,
        "humanizer_path": str(found) if found else None,
        "minimal_install": MINIMAL_HUMANIZER_INSTALL,
        "recommended_install": RECOMMENDED_HUMANIZER_INSTALL,
        "overall": "pass" if found else "fail",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Detect the humanizer skill (required before presenting review drafts). "
            "Pass --humanizer-only from review-code paths."
        )
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--humanizer-only",
        action="store_true",
        required=True,
        help=(
            "Check for the humanizer skill (required). "
            "Exit non-zero if humanizer is missing. Use this from review-code paths."
        ),
    )
    args = parser.parse_args(argv)

    results = check_humanizer()
    _output_humanizer(results, args.json)
    sys.exit(0 if results["overall"] == "pass" else 1)


def _output_humanizer(results, as_json):
    """Print humanizer-only results in JSON or human-readable format."""
    if as_json:
        json.dump(results, sys.stdout, indent=2)
        print()
        return

    print("=" * 50)
    print("RHDH PR Review Humanizer Check")
    print("=" * 50)
    print()
    print("Hard prerequisite for review-code drafts: the `humanizer` skill.")
    print("Used to strip AI tells from top-level and inline review prose.")
    print()

    if results["humanizer_found"]:
        print(f"  [PASS] humanizer found: {results['humanizer_path']}")
    else:
        print("  [FAIL] humanizer skill not found")
        print("         Looked for humanizer/SKILL.md under:")
        print("           ~/.claude/skills/")
        print("           ~/.agents/skills/")
        print("           ~/.cursor/skills/")
        print("           <cwd>/.claude/skills/")
        print("           <cwd>/.agents/skills/")
        print("           <cwd>/.cursor/skills/")
        print()
        print("  Install (after user confirms — this script does not install):")
        print(f"    Minimal (gate installs this): {results['minimal_install']}")
        print(f"    Recommended: {results['recommended_install']}")

    print()
    print(f"Overall: {results['overall'].upper()}")


if __name__ == "__main__":
    main()
