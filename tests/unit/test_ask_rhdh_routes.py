"""The /ask-rhdh routing table is a projection of the catalog, not a second inventory.

The table froze silently once: the category restructure moved `catalog.json`, the
renderer's path went stale, `--check` began exiting 2 instead of reporting drift,
and nothing ran it. The table then sat eleven skills out of date while catalog
validation stayed green — it does not look at that file.

These tests fail on drift AND on a renderer that cannot run, because the second
failure is what hid the first.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASK_RHDH = PROJECT_ROOT / "skills" / "meta" / "ask-rhdh"
RENDERER = ASK_RHDH / "scripts" / "render_routes.py"


def run_renderer(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RENDERER), *args],
        cwd=ASK_RHDH,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_route_table_matches_the_catalog():
    """`--check` exits 0 only when every catalog skill has a current row."""
    result = run_renderer("--check")

    assert result.returncode == 0, (
        "The /ask-rhdh route table has drifted from the catalog. "
        "Run: python scripts/render_routes.py --write\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_the_renderer_can_find_the_catalog():
    """A renderer that cannot locate the catalog must not look like a passing check.

    Exit code 2 means the tool broke; 1 means it ran and found drift. Conflating
    them is how the stale table survived, so assert the tool reached a verdict.
    """
    result = run_renderer("--check")

    assert result.returncode in (0, 1), (
        f"render_routes.py failed to run (exit {result.returncode}), rather than "
        f"reporting a verdict on the table.\nstderr: {result.stderr}"
    )
    assert "CATALOG_MISSING" not in (result.stdout + result.stderr)
