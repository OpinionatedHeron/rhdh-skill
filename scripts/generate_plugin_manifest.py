#!/usr/bin/env python3
"""Generate `.claude-plugin/marketplace.json` from the skill catalog.

The marketplace file is a projection for `npx skills add` grouping, not a Claude
Code marketplace product and not a second inventory. Membership and category
order come from `catalog.json`; hand-editing the generated file will drift.

    python scripts/generate_plugin_manifest.py            # print the JSON
    python scripts/generate_plugin_manifest.py --write    # rewrite marketplace.json
    python scripts/generate_plugin_manifest.py --check    # exit 1 if stale

Exit codes: 0 in sync or written, 1 stale under --check, 2 inputs unreadable.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "skills" / "meta" / "setup-rhdh-skills" / "assets" / "catalog.json"
MANIFEST_PATH = REPO_ROOT / ".claude-plugin" / "marketplace.json"

# skills CLI title-cases each kebab segment; spell acronyms so the tree reads
# "CI" rather than "Ci".
PLUGIN_NAME_BY_CATEGORY = {
    "ci": "CI",
}


def _fail(message: str) -> None:
    json.dump({"ok": False, "error": message}, sys.stdout, indent=2)
    print()
    sys.exit(2)


def plugin_name(category: str) -> str:
    return PLUGIN_NAME_BY_CATEGORY.get(category, category)


def plugin_description(category: str) -> str:
    name = plugin_name(category)
    label = name if category in PLUGIN_NAME_BY_CATEGORY else name[:1].upper() + name[1:]
    return f"{label} skills from the RHDH pack"


def build_manifest(catalog: dict[str, Any]) -> dict[str, Any]:
    """One marketplace plugin per catalog category, skills in catalog order."""
    categories = catalog.get("categories")
    skills = catalog.get("skills")
    pack = catalog.get("pack") or {}
    if not isinstance(categories, list) or not categories:
        raise ValueError("catalog.json has no categories list")
    if not isinstance(skills, list):
        raise ValueError("catalog.json has no skills list")

    by_category: dict[str, list[str]] = {category: [] for category in categories}
    for entry in skills:
        name = entry.get("name")
        category = entry.get("category")
        if not isinstance(name, str) or not isinstance(category, str):
            raise ValueError(f"catalog skill entry missing name/category: {entry!r}")
        if category not in by_category:
            raise ValueError(f"{name}: category {category!r} is not in catalog categories")
        by_category[category].append(f"./skills/{category}/{name}")

    plugins = []
    for category in categories:
        paths = by_category[category]
        if not paths:
            raise ValueError(f"category {category!r} has no skills in the catalog")
        plugins.append(
            {
                "name": plugin_name(category),
                "source": "./",
                "description": plugin_description(category),
                "skills": paths,
            }
        )

    source = pack.get("source") or "redhat-developer/rhdh-skills"
    return {
        "name": "rhdh-skills",
        "owner": {
            "name": "Red Hat Developer Hub",
            "url": f"https://github.com/{source}",
        },
        "description": (
            "Projection of the promoted RHDH skill catalog for npx skills "
            "installer grouping. Not a Claude Code marketplace product."
        ),
        "plugins": plugins,
    }


def render_manifest() -> str:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return json.dumps(build_manifest(catalog), indent=2) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="generate_plugin_manifest",
        description="Generate .claude-plugin/marketplace.json from the skill catalog.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="rewrite marketplace.json")
    mode.add_argument("--check", action="store_true", help="exit 1 if marketplace.json is stale")
    parser.add_argument("--json", action="store_true", help="structured output")
    args = parser.parse_args(argv)

    try:
        rendered = render_manifest()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        _fail(str(error))
        return

    if not (args.write or args.check):
        if args.json:
            json.dump({"ok": True, "manifest": json.loads(rendered)}, sys.stdout, indent=2)
            print()
        else:
            sys.stdout.write(rendered)
        return

    current = MANIFEST_PATH.read_text(encoding="utf-8") if MANIFEST_PATH.is_file() else ""
    in_sync = current == rendered

    if args.check:
        if args.json or not in_sync:
            json.dump(
                {
                    "ok": in_sync,
                    "path": str(MANIFEST_PATH),
                    "expected": rendered,
                    "found": current,
                },
                sys.stdout,
                indent=2,
            )
            print()
        sys.exit(0 if in_sync else 1)

    if not in_sync:
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(rendered, encoding="utf-8")
    if args.json:
        json.dump(
            {"ok": True, "path": str(MANIFEST_PATH), "rewritten": not in_sync},
            sys.stdout,
            indent=2,
        )
        print()


if __name__ == "__main__":
    main()
