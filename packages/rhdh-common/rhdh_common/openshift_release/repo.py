"""Resolve the openshift/release repository root for local or remote access.

Resolution order:
  1. Explicit path passed via resolve_repo_root(explicit_dir=...)
  2. OPENSHIFT_RELEASE_DIR environment variable
  3. Walk up from cwd looking for the ci-operator sentinel directory
  4. Fall back to REMOTE mode (GitHub API via gh CLI)

Usage:
    from rhdh_common.openshift_release.repo import resolve_repo_root
    root, is_remote = resolve_repo_root()
"""

import os
import sys
from pathlib import Path

# Sentinel path that identifies an openshift/release checkout.
_SENTINEL = Path("ci-operator/config/redhat-developer/rhdh")

# GitHub repository for remote access.
GITHUB_REPO = os.environ.get("OPENSHIFT_RELEASE_REPO", "openshift/release")


def resolve_repo_root(explicit_dir=None):
    """Return (root_path, is_remote).

    root_path is a Path when local, None when remote.
    is_remote is True when no local checkout was found.
    """
    # 1. Explicit override
    if explicit_dir is not None:
        p = Path(explicit_dir)
        if (p / _SENTINEL).is_dir():
            return p.resolve(), False
        print(
            f"WARNING: explicit dir {explicit_dir} does not contain {_SENTINEL}",
            file=sys.stderr,
        )

    # 2. Environment variable
    env_dir = os.environ.get("OPENSHIFT_RELEASE_DIR")
    if env_dir:
        p = Path(env_dir)
        if (p / _SENTINEL).is_dir():
            return p.resolve(), False
        print(
            f"WARNING: OPENSHIFT_RELEASE_DIR is set but {_SENTINEL} not found there",
            file=sys.stderr,
        )

    # 3. Walk up from cwd
    cur = Path.cwd()
    while True:
        if (cur / _SENTINEL).is_dir():
            return cur.resolve(), False
        parent = cur.parent
        if parent == cur:
            break
        cur = parent

    # 4. Remote mode
    return None, True
