"""Fetch and parse YAML files from the openshift/release repository.

Supports both local checkout and remote GitHub API access. Provides
helper functions for listing files, reading YAML, and extracting
configured K8s versions from CI config files.

Usage:
    from rhdh_common.openshift_release.yaml import fetch_yaml, list_yaml_files

Requires the ``yaml`` extra: ``rhdh-common[yaml]``.
"""

from __future__ import annotations

import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from ruamel.yaml import YAML

from rhdh_common.openshift_release.repo import GITHUB_REPO

_yaml = YAML()
_yaml.preserve_quotes = True


def list_yaml_files(config_dir: str, pattern: str, root: Path | None, is_remote: bool) -> list[str]:
    """List YAML files in a directory matching a glob pattern.

    In local mode, returns absolute path strings.
    In remote mode, returns repo-relative path strings.
    """
    if is_remote:
        api_path = f"repos/{GITHUB_REPO}/contents/{config_dir}"
        try:
            result = subprocess.run(
                ["gh", "api", api_path, "--jq", ".[] | .path"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"ERROR: Failed to list {config_dir} via GitHub API: {exc}", file=sys.stderr)
            return []
        # Filter by pattern (convert glob to regex)
        regex = re.compile(pattern.replace("*", ".*").replace("?", "."))
        return [
            line for line in result.stdout.strip().splitlines() if regex.search(Path(line).name)
        ]
    else:
        local_dir = root / config_dir if root else Path(config_dir)
        if not local_dir.is_dir():
            print(f"ERROR: Directory not found: {local_dir}", file=sys.stderr)
            return []
        return sorted(str(f) for f in local_dir.glob(pattern) if f.is_file())


def fetch_yaml(filepath: str, root: Path | None, is_remote: bool) -> dict | None:
    """Read and parse a single YAML file.

    Returns the parsed YAML as a dict, or None on failure.
    """
    if is_remote:
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/HEAD/{filepath}"
        try:
            req = urllib.request.Request(raw_url, headers={"User-Agent": "rhdh-skill"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return _yaml.load(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError) as exc:
            print(f"ERROR: Failed to fetch {filepath}: {exc}", file=sys.stderr)
            return None
    else:
        path = Path(filepath)
        if not path.is_file():
            print(f"ERROR: File not found: {filepath}", file=sys.stderr)
            return None
        with open(path) as fh:
            return _yaml.load(fh)


def fetch_yaml_text(filepath: str, root: Path | None, is_remote: bool) -> str | None:
    """Read a file as raw text (no YAML parsing).

    Useful for files that need grep-style processing rather than structured
    parsing (e.g., extracting a tag value from a ref YAML).
    """
    if is_remote:
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/HEAD/{filepath}"
        try:
            req = urllib.request.Request(raw_url, headers={"User-Agent": "rhdh-skill"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, OSError) as exc:
            print(f"ERROR: Failed to fetch {filepath}: {exc}", file=sys.stderr)
            return None
    else:
        path = Path(filepath)
        if not path.is_file():
            print(f"ERROR: File not found: {filepath}", file=sys.stderr)
            return None
        return path.read_text()


def extract_branch(prefix: str, filepath: str) -> str:
    """Extract the branch/filename stem from a config file path.

    Example:
        extract_branch("redhat-developer-rhdh-", ".../redhat-developer-rhdh-main.yaml")
        => "main"
    """
    name = Path(filepath).stem  # removes .yaml
    if name.startswith(prefix):
        return name[len(prefix) :]
    return name
