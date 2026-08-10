"""Standalone runtime support for the rhdh-local CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


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


def run_command(cmd: list[str], cwd: Optional[Path] = None) -> tuple[int, str, str]:
    """Run a command and return its exit code, stdout, and stderr."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


class OutputFormatter:
    """Render structured JSON for agents or concise text for humans."""

    def __init__(self, mode: str = "auto") -> None:
        self.mode = "human" if mode == "auto" and sys.stdout.isatty() else mode
        if self.mode == "auto":
            self.mode = "json"
        self._has_human_output = False
        self._color = self.mode == "human" and os.environ.get("NO_COLOR") is None

    @property
    def is_human(self) -> bool:
        return self.mode == "human"

    def _paint(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self._color else text

    def header(self, text: str) -> None:
        if self.is_human:
            print(f"\n{self._paint('1', text)}")
            self._has_human_output = True

    def _log(self, symbol: str, color: str, message: str) -> None:
        if self.is_human:
            print(f"  {self._paint(color, symbol)} {message}")
            self._has_human_output = True

    def log_ok(self, message: str) -> None:
        self._log("✓", "32", message)

    def log_warn(self, message: str) -> None:
        self._log("!", "33", message)

    def log_fail(self, message: str) -> None:
        self._log("x", "31", message)

    def log_info(self, message: str) -> None:
        self._log("→", "34", message)

    def success(self, data: dict[str, Any], next_steps: Optional[list[str]] = None) -> None:
        if not self.is_human:
            payload: dict[str, Any] = {"success": True, "data": data}
            if next_steps:
                payload["next_steps"] = next_steps
            print(json.dumps(payload, indent=2, default=str))
            return
        if not self._has_human_output:
            for key, value in data.items():
                print(f"{key}: {value}")
        if next_steps:
            print("\nNext steps:")
            for step in next_steps:
                print(f"  {step}")

    def error(
        self,
        code: str,
        message: str,
        next_steps: Optional[list[str]] = None,
    ) -> None:
        if not self.is_human:
            payload: dict[str, Any] = {
                "success": False,
                "error": {"code": code, "message": message},
            }
            if next_steps:
                payload["next_steps"] = next_steps
            print(json.dumps(payload, indent=2))
            return
        print(f"Error [{code}]: {message}", file=sys.stderr)
        if next_steps:
            print("To fix:", file=sys.stderr)
            for step in next_steps:
                print(f"  {step}", file=sys.stderr)
