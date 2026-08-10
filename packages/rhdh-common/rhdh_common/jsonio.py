"""Progress on stderr, machine-readable failure on stdout.

Data-gathering scripts write one JSON document to stdout and nothing else, so
progress goes to stderr and a failure exits with a JSON error object. The two
prior copies of this pair disagreed on the error shape (``detail`` string
versus arbitrary extra keys); this one accepts both.
"""

from __future__ import annotations

import json
import os
import sys
from typing import NoReturn, Optional


def log(msg: str) -> None:
    """Write progress to stderr, keeping stdout clean for JSON output.

    Silent when stderr is redirected or when NO_COLOR is set, matching the
    behaviour the fetch scripts already relied on.
    """
    if sys.stderr.isatty() and os.environ.get("NO_COLOR") is None:
        print(msg, file=sys.stderr)


def error_exit(
    error_key: str,
    detail: Optional[str] = None,
    extra: Optional[dict] = None,
) -> NoReturn:
    """Print a JSON error object to stdout and exit 1.

    ``error_key`` is the stable machine-readable reason. ``detail`` is a human
    string; ``extra`` merges additional diagnostic keys.
    """
    result: dict = {"error": error_key}
    if detail:
        result["detail"] = detail
    if extra:
        result.update(extra)
    json.dump(result, sys.stdout, indent=2)
    print()
    sys.exit(1)
