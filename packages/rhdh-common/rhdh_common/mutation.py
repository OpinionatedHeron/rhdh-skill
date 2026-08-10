"""Canonical mutation-plan hashing and receipt validation.

A plan the user approved and the receipt that closes it must agree byte for
byte, in every skill that writes to an external system. Two implementations of
that hash cannot be kept in agreement by review, so ADR-0006 puts shared runtime
code in this versioned package: this module is the only implementation.

    from rhdh_common.mutation import material_hash, operation_errors
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

MATERIAL_HASH = re.compile(r"^sha256:[a-f0-9]{64}$")
OUTCOME_STATUSES = frozenset({"completed", "failed", "skipped"})
_SCALAR_FIELDS = ("ownerSkill", "adapter", "operation", "target")
_ARRAY_FIELDS = ("preconditions", "checks", "recovery")
_IDENTITY_FIELDS = ("order", "ownerSkill", "adapter", "operation", "target")


def canonical_material(data: dict[str, Any]) -> str:
    """Return the UTF-8 JSON text the material hash is computed over.

    The input is a plan's complete ``data`` object. ``materialHash`` is removed
    here so no caller has to remember to strip it.
    """
    material = {key: value for key, value in data.items() if key != "materialHash"}
    return json.dumps(material, separators=(",", ":"), sort_keys=True)


def material_hash(data: dict[str, Any]) -> str:
    """Return ``sha256:<digest>`` binding a plan's summary and operations."""
    return f"sha256:{hashlib.sha256(canonical_material(data).encode()).hexdigest()}"


def _positive_order(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def operation_errors(operations: Any) -> list[dict[str, str]]:
    """Validate a plan's ``data.operations`` array."""
    if not isinstance(operations, list) or not operations:
        return [
            {
                "code": "MUTATION_OPERATIONS",
                "message": "data.operations must be a non-empty array",
            }
        ]
    errors: list[dict[str, str]] = []
    for index, operation in enumerate(operations):
        path = f"data.operations[{index}]"
        if not isinstance(operation, dict):
            errors.append({"code": "MUTATION_OPERATION", "message": f"{path} must be an object"})
            continue
        if not _positive_order(operation.get("order")):
            errors.append(
                {
                    "code": "MUTATION_OPERATION",
                    "message": f"{path}.order must be a positive integer",
                }
            )
        elif operation["order"] != index + 1:
            errors.append(
                {
                    "code": "MUTATION_OPERATION",
                    "message": f"{path}.order must be {index + 1} to match array order",
                }
            )
        for field in _SCALAR_FIELDS:
            if not isinstance(operation.get(field), str) or not operation[field].strip():
                errors.append(
                    {
                        "code": "MUTATION_OPERATION",
                        "message": f"{path}.{field} must be a non-empty string",
                    }
                )
        if not isinstance(operation.get("preview"), dict):
            errors.append(
                {"code": "MUTATION_OPERATION", "message": f"{path}.preview must be an object"}
            )
        for field in _ARRAY_FIELDS:
            if not isinstance(operation.get(field), list):
                errors.append(
                    {"code": "MUTATION_OPERATION", "message": f"{path}.{field} must be an array"}
                )
    return errors


def outcome_errors(outcomes: Any) -> list[dict[str, str]]:
    """Validate a receipt's ``data.outcomes`` array."""
    if not isinstance(outcomes, list) or not outcomes:
        return [
            {
                "code": "MUTATION_OUTCOMES",
                "message": "data.outcomes must be a non-empty array",
            }
        ]
    errors: list[dict[str, str]] = []
    for index, outcome in enumerate(outcomes):
        path = f"data.outcomes[{index}]"
        if not isinstance(outcome, dict):
            errors.append({"code": "MUTATION_OUTCOME", "message": f"{path} must be an object"})
            continue
        if outcome.get("order") != index + 1:
            errors.append(
                {
                    "code": "MUTATION_OUTCOME",
                    "message": f"{path}.order must be {index + 1} to match array order",
                }
            )
        for field in _SCALAR_FIELDS:
            if not isinstance(outcome.get(field), str) or not outcome[field].strip():
                errors.append(
                    {
                        "code": "MUTATION_OUTCOME",
                        "message": f"{path}.{field} must be a non-empty string",
                    }
                )
        if outcome.get("status") not in OUTCOME_STATUSES:
            errors.append(
                {
                    "code": "MUTATION_OUTCOME",
                    "message": (
                        f"{path}.status must be one of " + ", ".join(sorted(OUTCOME_STATUSES))
                    ),
                }
            )
    return errors


def receipt_binding_errors(
    operations: list[dict[str, Any]], outcomes: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """Require exactly one identity-bound outcome per planned operation."""
    if len(outcomes) != len(operations):
        return [
            {
                "code": "RECEIPT_OUTCOME_MISMATCH",
                "message": "receipt must record exactly one outcome for every planned operation",
            }
        ]
    for index, (operation, outcome) in enumerate(zip(operations, outcomes)):
        for field in _IDENTITY_FIELDS:
            if outcome.get(field) != operation.get(field):
                return [
                    {
                        "code": "RECEIPT_OUTCOME_MISMATCH",
                        "message": (
                            f"data.outcomes[{index}].{field} does not match "
                            f"data.operations[{index}].{field}"
                        ),
                    }
                ]
    return []
