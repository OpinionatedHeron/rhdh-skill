#!/usr/bin/env python3
"""Verify acli installation, Jira authentication, and grilling skill for RHDH."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

RHDH_PROJECTS = ["RHIDP", "RHDHPLAN", "RHDHBUGS", "RHDHSUPP"]
JIRA_CONFIG_RELATIVE = Path(".config", "acli", "jira_config.yaml")

MINIMAL_GRILLING_INSTALL = "npx skills@latest add mattpocock/skills --skill grilling -g -y"
RECOMMENDED_GRILLING_INSTALL = "npx skills@latest add mattpocock/skills --all -g"
GRILLING_SKILL_RELATIVE = Path("grilling") / "SKILL.md"


def find_acli():
    """Find acli binary on PATH."""
    acli = shutil.which("acli")
    if acli:
        return acli

    # Check common locations on Windows
    if sys.platform == "win32":
        home = Path.home()
        candidates = [
            home / ".path" / "acli.exe",
            home / "AppData" / "Local" / "acli" / "acli.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

    return None


def grilling_search_paths(home=None, cwd=None):
    """Return candidate paths for grilling/SKILL.md (user + project-local)."""
    home = Path.home() if home is None else Path(home)
    cwd = Path.cwd() if cwd is None else Path(cwd)
    return [
        home / ".claude" / "skills" / GRILLING_SKILL_RELATIVE,
        home / ".agents" / "skills" / GRILLING_SKILL_RELATIVE,
        home / ".cursor" / "skills" / GRILLING_SKILL_RELATIVE,
        cwd / ".claude" / "skills" / GRILLING_SKILL_RELATIVE,
        cwd / ".agents" / "skills" / GRILLING_SKILL_RELATIVE,
        cwd / ".cursor" / "skills" / GRILLING_SKILL_RELATIVE,
    ]


def find_grilling(home=None, cwd=None):
    """Return the first existing grilling/SKILL.md path, or None."""
    for path in grilling_search_paths(home=home, cwd=cwd):
        if path.is_file():
            return path.resolve()
    return None


def check_grilling(home=None, cwd=None):
    """Build a results dict for grilling skill detection."""
    found = find_grilling(home=home, cwd=cwd)
    return {
        "grilling_found": found is not None,
        "grilling_path": str(found) if found else None,
        "minimal_install": MINIMAL_GRILLING_INSTALL,
        "recommended_install": RECOMMENDED_GRILLING_INSTALL,
        "overall": "pass" if found else "fail",
    }


def check_config():
    """Check if Jira API token config exists."""
    config_path = Path.home() / JIRA_CONFIG_RELATIVE
    if not config_path.exists():
        return None, "not found"

    try:
        content = config_path.read_text(encoding="utf-8")
        if "api_token" in content:
            return str(config_path), "api_token"
        elif "oauth" in content.lower():
            return str(config_path), "oauth"
        else:
            return str(config_path), "unknown"
    except OSError as e:
        return None, f"read error: {e}"


def smoke_test(acli_path):
    """Run a smoke test to verify Jira connectivity."""
    try:
        result = subprocess.run(
            [acli_path, "jira", "project", "list", "--recent", "1"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        if result.returncode == 0 and stdout.strip():
            return True, stdout.strip()
        return False, stderr.strip() or "empty response"
    except subprocess.TimeoutExpired:
        return False, "timeout after 30s"
    except OSError as e:
        return False, str(e)


def check_projects(acli_path):
    """Check which RHDH projects are accessible."""
    accessible = []
    inaccessible = []

    for project in RHDH_PROJECTS:
        try:
            result = subprocess.run(
                [acli_path, "jira", "project", "view", "--key", project],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            if result.returncode == 0:
                accessible.append(project)
            else:
                stderr = result.stderr or ""
                inaccessible.append((project, stderr.strip()))
        except (subprocess.TimeoutExpired, OSError) as e:
            inaccessible.append((project, str(e)))

    return accessible, inaccessible


def check_token_file(acli_path):
    """Check if .jira-token file exists next to the acli executable."""
    acli_dir = Path(acli_path).resolve().parent
    token_path = acli_dir / ".jira-token"
    if not token_path.exists():
        return None, "not found", []
    warnings = []
    try:
        content = token_path.read_text(encoding="utf-8").strip()
        if "\n" in content:
            warnings.append("file contains multiple lines — should be a single line")
        if ":" not in content:
            return str(token_path), "missing email prefix (expected email:token format)", warnings
        # Check file permissions on Unix
        if sys.platform != "win32":
            import stat

            mode = token_path.stat().st_mode
            if mode & (stat.S_IRGRP | stat.S_IROTH):
                warnings.append(
                    "file is readable by group/others — run: chmod 600 " + str(token_path)
                )
        return str(token_path), "valid", warnings
    except OSError as e:
        return None, f"read error: {e}", warnings


def _merge_grilling(results, home=None, cwd=None):
    """Attach grilling detection fields to a full setup results dict."""
    grilling = check_grilling(home=home, cwd=cwd)
    results["grilling_found"] = grilling["grilling_found"]
    results["grilling_path"] = grilling["grilling_path"]
    results["grilling_minimal_install"] = grilling["minimal_install"]
    results["grilling_recommended_install"] = grilling["recommended_install"]


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Verify acli installation and Jira authentication for RHDH. "
            "Also detects Matt Pocock's grilling skill (required for create/grill paths)."
        )
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--quick", action="store_true", help="Skip project accessibility check")
    parser.add_argument(
        "--grilling-only",
        action="store_true",
        help=(
            "Only check for the grilling skill (skip acli/auth). "
            "Exit non-zero if grilling is missing. Use this from create/grill paths "
            "so acli failures do not hide the grilling-specific prereq message."
        ),
    )
    args = parser.parse_args(argv)

    if args.grilling_only:
        results = check_grilling()
        _output_grilling(results, args.json)
        sys.exit(0 if results["overall"] == "pass" else 1)

    results = {
        "acli_found": False,
        "acli_path": None,
        "config_found": False,
        "config_path": None,
        "auth_type": None,
        "token_file_found": False,
        "token_file_path": None,
        "token_file_status": None,
        "connectivity": False,
        "connectivity_detail": None,
        "projects_accessible": [],
        "projects_inaccessible": [],
        "grilling_found": False,
        "grilling_path": None,
        "grilling_minimal_install": MINIMAL_GRILLING_INSTALL,
        "grilling_recommended_install": RECOMMENDED_GRILLING_INSTALL,
        "overall": "fail",
    }

    # Step 1: Find acli
    acli_path = find_acli()
    if acli_path:
        results["acli_found"] = True
        results["acli_path"] = acli_path
    else:
        results["connectivity_detail"] = "acli not found on PATH"
        _merge_grilling(results)
        _output(results, args.json)
        sys.exit(1)

    # Step 2: Check config
    config_path, auth_type = check_config()
    if config_path:
        results["config_found"] = True
        results["config_path"] = config_path
        results["auth_type"] = auth_type

    # Step 3: Check .jira-token file
    token_path, token_status, token_warnings = check_token_file(acli_path)
    if token_path:
        results["token_file_found"] = True
        results["token_file_path"] = token_path
    results["token_file_status"] = token_status
    results["token_file_warnings"] = token_warnings

    # Step 4: Smoke test (do NOT use 'acli auth status' — it lies with API tokens)
    ok, detail = smoke_test(acli_path)
    results["connectivity"] = ok
    results["connectivity_detail"] = detail

    if not ok:
        _merge_grilling(results)
        _output(results, args.json)
        sys.exit(1)

    # Step 5: Check project access
    if not args.quick:
        accessible, inaccessible = check_projects(acli_path)
        results["projects_accessible"] = accessible
        results["projects_inaccessible"] = [{"project": p, "error": e} for p, e in inaccessible]

    # Step 6: grilling skill (informational in full mode — does not fail overall)
    _merge_grilling(results)

    results["overall"] = "pass"
    _output(results, args.json)
    sys.exit(0)


def _output_grilling(results, as_json):
    """Print grilling-only results in JSON or human-readable format."""
    if as_json:
        json.dump(results, sys.stdout, indent=2)
        print()
        return

    print("=" * 50)
    print("RHDH Jira Grilling Check")
    print("=" * 50)
    print()
    print("Hard prerequisite for create/grill paths: Matt Pocock's `grilling` skill.")
    print("Used for interview cadence (one question at a time).")
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
        print("  Install (after user confirms — this script does not install):")
        print(f"    Minimal (gate installs this): {results['minimal_install']}")
        print(f"    Recommended (full Matt pack): {results['recommended_install']}")

    print()
    print(f"Overall: {results['overall'].upper()}")


def _output(results, as_json):
    """Print results in JSON or human-readable format."""
    if as_json:
        json.dump(results, sys.stdout, indent=2)
        print()
        return

    print("=" * 50)
    print("RHDH Jira Setup Check")
    print("=" * 50)

    # acli
    if results["acli_found"]:
        print(f"  [PASS] acli found: {results['acli_path']}")
    else:
        print("  [FAIL] acli not found on PATH")
        print("         Install from: https://developer.atlassian.com/cloud/acli/")
        _print_grilling_section(results)
        return

    # Config
    if results["config_found"]:
        print(f"  [PASS] Config found: {results['config_path']}")
        print(f"         Auth type: {results['auth_type']}")
    else:
        print("  [WARN] No Jira config found at ~/.config/acli/jira_config.yaml")
        print("         Run: acli auth login")

    # Token file
    if results["token_file_found"]:
        if results["token_file_status"] == "valid":
            print(f"  [PASS] Token file found: {results['token_file_path']}")
        else:
            print(f"  [WARN] Token file found but {results['token_file_status']}")
            print(f"         File: {results['token_file_path']}")
            print("         Expected format: email@example.com:your-api-token")
        for w in results.get("token_file_warnings", []):
            print(f"  [WARN] {w}")
    else:
        acli_dir = Path(results["acli_path"]).resolve().parent
        print("  [WARN] No .jira-token file found next to acli")
        print(f"         Expected at: {acli_dir / '.jira-token'}")
        print("         Create with: echo 'email:api-token' > .jira-token")
        print("         Then: chmod 600 .jira-token")
        print("         REST API/GraphQL fallback will not work without it.")
        print("         See: https://developer.atlassian.com/cloud/acli/guides/how-to-get-started/")

    # Connectivity
    if results["connectivity"]:
        print("  [PASS] Jira connectivity verified")
    else:
        print(f"  [FAIL] Jira connectivity failed: {results['connectivity_detail']}")
        _print_grilling_section(results)
        return

    # Projects
    if results["projects_accessible"]:
        print(f"  [PASS] Projects accessible: {', '.join(results['projects_accessible'])}")
    if results["projects_inaccessible"]:
        for item in results["projects_inaccessible"]:
            print(f"  [WARN] {item['project']}: {item['error']}")

    _print_grilling_section(results)

    print()
    print(f"Overall: {results['overall'].upper()}")


def _print_grilling_section(results):
    """Print grilling status in full setup output (warn if missing; does not fail overall)."""
    if results.get("grilling_found"):
        print(f"  [PASS] grilling found: {results['grilling_path']}")
    else:
        print("  [WARN] grilling skill not found (required for to-feature / to-epic / to-issue)")
        print("         Create/grill paths: python scripts/setup.py --grilling-only")
        print(
            f"         Minimal: {results.get('grilling_minimal_install', MINIMAL_GRILLING_INSTALL)}"
        )
        print(
            f"         Recommended: {results.get('grilling_recommended_install', RECOMMENDED_GRILLING_INSTALL)}"
        )


if __name__ == "__main__":
    main()
