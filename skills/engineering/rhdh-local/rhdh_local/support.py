"""Workspace discovery for the rhdh-local CLI.

Output formatting and subprocess execution used to be reimplemented here; both
now come from ``rhdh_common`` (ADR-0006). This module keeps only what is
specific to rhdh-local: finding the rhdh-local-setup workspace.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _is_setup_dir(path: Path) -> bool:
    return (path / "rhdh-customizations").is_dir() and (path / "rhdh-local").is_dir()


def get_local_setup_dir(start: Optional[Path] = None) -> Optional[Path]:
    """Discover an rhdh-local-setup workspace without external configuration."""
    configured = os.environ.get("RHDH_LOCAL_SETUP_DIR")
    if configured:
        path = Path(configured).expanduser()
        if _is_setup_dir(path):
            return path.resolve()

    current = (start or Path.cwd()).resolve()
    for parent in (current, *current.parents):
        if _is_setup_dir(parent):
            return parent
        candidate = parent / "rhdh-local-setup"
        if _is_setup_dir(candidate):
            return candidate.resolve()
    return None
