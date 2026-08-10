"""Output formatting for the rhdh CLI.

The implementation lives in ``rhdh_common.output`` (ADR-0006): it was
previously copied byte-for-byte into rhdh-release and reimplemented a third
time in rhdh-local. This module re-exports it so the CLI keeps a stable import
path.
"""

from rhdh_common.output import (
    BLUE,
    BOLD,
    GREEN,
    NC,
    RED,
    YELLOW,
    OutputFormatter,
    detect_output_mode,
)

__all__ = [
    "BLUE",
    "BOLD",
    "GREEN",
    "NC",
    "RED",
    "YELLOW",
    "OutputFormatter",
    "detect_output_mode",
]
