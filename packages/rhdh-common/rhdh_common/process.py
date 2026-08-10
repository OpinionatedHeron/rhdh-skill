"""Subprocess execution and tool discovery.

Both were previously reimplemented per skill. The copies drifted: one
``run_command`` set an explicit encoding and one did not, and one ``find_acli``
knew about a Windows install location the others missed, so a setup doctor
reported acli installed while the scripts using it reported not-found. The
versions here are the safe supersets.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional


def run_command(cmd: list[str], cwd: Optional[Path] = None) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr).

    Decoding is pinned to UTF-8 with replacement so that non-ASCII subprocess
    output does not raise on a Windows console codepage.
    """
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def find_tool(name: str, extra_candidates: Iterable[Path] = ()) -> Optional[str]:
    """Return the path to a tool, or None.

    PATH wins. ``extra_candidates`` covers installers that do not amend PATH.
    """
    on_path = shutil.which(name)
    if on_path:
        return on_path
    for candidate in extra_candidates:
        if Path(candidate).is_file():
            return str(candidate)
    return None


def find_acli() -> Optional[str]:
    """Return the path to the Atlassian CLI, or None."""
    home = Path.home()
    return find_tool(
        "acli",
        (
            home / ".path" / "acli.exe",
            home / "AppData" / "Local" / "acli" / "acli.exe",
        ),
    )
