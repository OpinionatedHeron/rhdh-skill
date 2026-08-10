#!/usr/bin/env python3
"""Validate and persist versioned RHDH skill artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CONTRACTS_FILE = Path(__file__).with_name("artifact-contracts.json")
CREDENTIAL_KEYS = {
    "auth",
    "apikey",
    "authorization",
    "clientsecret",
    "cookie",
    "credential",
    "credentials",
    "password",
    "privatekey",
    "refreshtoken",
    "secret",
    "token",
    "accesstoken",
}
CREDENTIAL_VALUE = re.compile(
    r"(?i)(?:^|\b)(?:authorization\s*:\s*)?(?:bearer|basic)\s+\S+|BEGIN (?:RSA )?PRIVATE KEY"
)
OPAQUE_CREDENTIAL_VALUE = re.compile(
    r"(?i)^(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|glpat-[A-Za-z0-9_-]+|"
    r"xox[baprs]-[A-Za-z0-9-]+|sk-[A-Za-z0-9_-]{12,}|AKIA[A-Z0-9]{16})$"
)
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
MATERIAL_HASH = re.compile(r"^sha256:[a-f0-9]{64}$")
OUTCOME_STATUSES = {"completed", "failed", "skipped"}


def _load_contracts() -> dict[str, dict[str, Any]]:
    payload = json.loads(CONTRACTS_FILE.read_text(encoding="utf-8"))
    return payload["contracts"]


def _credential_key(key: Any) -> bool:
    raw = str(key)
    normalized = re.sub(r"[^a-z0-9]", "", raw.lower())
    if normalized in CREDENTIAL_KEYS:
        return True

    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", raw)
    segments = [part.lower() for part in re.split(r"[^A-Za-z0-9]+", separated) if part]
    joined_pairs = {"".join(pair) for pair in zip(segments, segments[1:])}
    if joined_pairs & {
        "accesstoken",
        "apikey",
        "clientsecret",
        "privatekey",
        "refreshtoken",
    }:
        return True
    if set(segments) & {
        "authorization",
        "cookie",
        "credential",
        "credentials",
        "password",
        "secret",
    }:
        return True
    return any(
        segment == "token"
        and (index + 1 == len(segments) or segments[index + 1] not in {"count", "counts", "limit"})
        for index, segment in enumerate(segments)
    )


def _credential_error(value: Any, path: str = "") -> dict[str, str] | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if _credential_key(key) or _credential_key(child_path):
                return {
                    "code": "CREDENTIAL_FIELD",
                    "message": f"{child_path} is not allowed in an artifact",
                }
            error = _credential_error(child, child_path)
            if error:
                return error
    elif isinstance(value, list):
        for index, child in enumerate(value):
            error = _credential_error(child, f"{path}[{index}]")
            if error:
                return error
    elif isinstance(value, str) and (
        CREDENTIAL_VALUE.search(value) or OPAQUE_CREDENTIAL_VALUE.fullmatch(value)
    ):
        return {
            "code": "CREDENTIAL_VALUE",
            "message": f"{path or '<root>'} contains credential-shaped content",
        }
    return None


def _material_hash(data: dict[str, Any]) -> str:
    material = {key: value for key, value in data.items() if key != "materialHash"}
    canonical = json.dumps(material, separators=(",", ":"), sort_keys=True)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def _mutation_operation_errors(operations: Any) -> list[dict[str, str]]:
    if not isinstance(operations, list) or not operations:
        return [
            {
                "code": "MUTATION_OPERATIONS",
                "message": "data.operations must be a non-empty array",
            }
        ]
    errors: list[dict[str, str]] = []
    scalar_fields = ("ownerSkill", "adapter", "operation", "target")
    array_fields = ("preconditions", "checks", "recovery")
    for index, operation in enumerate(operations):
        path = f"data.operations[{index}]"
        if not isinstance(operation, dict):
            errors.append({"code": "MUTATION_OPERATION", "message": f"{path} must be an object"})
            continue
        if not isinstance(operation.get("order"), int) or operation["order"] < 1:
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
        for field in scalar_fields:
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
        for field in array_fields:
            if not isinstance(operation.get(field), list):
                errors.append(
                    {"code": "MUTATION_OPERATION", "message": f"{path}.{field} must be an array"}
                )
    return errors


def _mutation_outcome_errors(outcomes: Any) -> list[dict[str, str]]:
    if not isinstance(outcomes, list) or not outcomes:
        return [
            {
                "code": "MUTATION_OUTCOMES",
                "message": "data.outcomes must be a non-empty array",
            }
        ]
    errors: list[dict[str, str]] = []
    scalar_fields = ("ownerSkill", "adapter", "operation", "target")
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
        for field in scalar_fields:
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


def _receipt_binding_errors(
    operations: list[dict[str, Any]], outcomes: list[dict[str, Any]]
) -> list[dict[str, str]]:
    if len(outcomes) != len(operations):
        return [
            {
                "code": "RECEIPT_OUTCOME_MISMATCH",
                "message": "receipt must record exactly one outcome for every planned operation",
            }
        ]
    identity_fields = ("order", "ownerSkill", "adapter", "operation", "target")
    for index, (operation, outcome) in enumerate(zip(operations, outcomes)):
        for field in identity_fields:
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


def validate_artifact(artifact: Any) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    if not isinstance(artifact, dict):
        return {
            "valid": False,
            "errors": [{"code": "ARTIFACT_TYPE", "message": "artifact must be an object"}],
        }

    credential_error = _credential_error(artifact)
    if credential_error:
        return {"valid": False, "errors": [credential_error]}

    contracts = _load_contracts()
    contract = artifact.get("contract")
    if contract not in contracts:
        errors.append({"code": "CONTRACT_UNKNOWN", "message": repr(contract)})

    artifact_id = artifact.get("id")
    if not isinstance(artifact_id, str) or not SAFE_ID.fullmatch(artifact_id):
        errors.append(
            {
                "code": "ARTIFACT_ID",
                "message": "id must contain only letters, numbers, dots, underscores, and hyphens",
            }
        )

    created_at = artifact.get("createdAt")
    if not isinstance(created_at, str):
        errors.append({"code": "CREATED_AT", "message": "createdAt must be an ISO-8601 string"})
    else:
        try:
            datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append({"code": "CREATED_AT", "message": "createdAt must be ISO-8601"})

    data = artifact.get("data")
    if not isinstance(data, dict):
        errors.append({"code": "DATA_TYPE", "message": "data must be an object"})
    elif contract in contracts:
        for field in contracts[contract].get("requiredData", []):
            if field not in data:
                errors.append(
                    {"code": "DATA_REQUIRED", "message": f"{contract} requires data.{field}"}
                )

        if contract == "MutationPlan/v1" and "materialHash" in data:
            errors.extend(_mutation_operation_errors(data.get("operations")))
            expected_hash = _material_hash(data)
            if data["materialHash"] != expected_hash:
                errors.append(
                    {
                        "code": "MATERIAL_HASH",
                        "message": "data.materialHash does not match the canonical plan data",
                    }
                )
        elif contract == "MutationReceipt/v1" and "materialHash" in data:
            errors.extend(_mutation_outcome_errors(data.get("outcomes")))
            if not isinstance(data["materialHash"], str) or not MATERIAL_HASH.fullmatch(
                data["materialHash"]
            ):
                errors.append(
                    {
                        "code": "MATERIAL_HASH",
                        "message": "data.materialHash must be a canonical sha256 hash",
                    }
                )
            plan_id = data.get("planId")
            if not isinstance(plan_id, str) or not SAFE_ID.fullmatch(plan_id):
                errors.append(
                    {
                        "code": "PLAN_ID",
                        "message": "data.planId must be a safe artifact id",
                    }
                )

    return {"valid": not errors, "errors": errors, "contract": contract, "id": artifact_id}


def _read_artifact(path: Path) -> tuple[Any | None, dict[str, Any] | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except OSError as exc:
        return None, {"valid": False, "errors": [{"code": "READ_ERROR", "message": str(exc)}]}
    except json.JSONDecodeError as exc:
        return None, {"valid": False, "errors": [{"code": "JSON_INVALID", "message": str(exc)}]}


def _contract_directory(contract: str) -> str:
    base = contract.split("/", 1)[0]
    return re.sub(r"(?<!^)(?=[A-Z])", "-", base).lower()


def persist_artifact(artifact: dict[str, Any], project_root: Path) -> dict[str, Any]:
    report = validate_artifact(artifact)
    if not report["valid"]:
        return report

    if artifact["contract"] == "MutationReceipt/v1":
        plan_id = artifact["data"]["planId"]
        plan_path = (
            project_root.resolve() / ".rhdh" / "artifacts" / "mutation-plan" / f"{plan_id}.json"
        )
        plan, read_error = _read_artifact(plan_path)
        if read_error or not isinstance(plan, dict) or plan.get("contract") != "MutationPlan/v1":
            return {
                "valid": False,
                "errors": [
                    {
                        "code": "PLAN_NOT_FOUND",
                        "message": f"approved MutationPlan/v1 {plan_id!r} is not persisted",
                    }
                ],
            }
        plan_report = validate_artifact(plan)
        if not plan_report["valid"] or (
            artifact["data"]["materialHash"] != plan["data"].get("materialHash")
        ):
            return {
                "valid": False,
                "errors": [
                    {
                        "code": "PLAN_HASH_MISMATCH",
                        "message": "receipt materialHash does not match the approved plan",
                    }
                ],
            }
        binding_errors = _receipt_binding_errors(
            plan["data"]["operations"], artifact["data"]["outcomes"]
        )
        if binding_errors:
            return {"valid": False, "errors": binding_errors}

    relative_path = (
        Path(".rhdh")
        / "artifacts"
        / _contract_directory(artifact["contract"])
        / f"{artifact['id']}.json"
    )
    destination = project_root.resolve() / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)

    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{artifact['id']}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(artifact, stream, indent=2, sort_keys=True)
            stream.write("\n")
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()

    return {
        "valid": True,
        "errors": [],
        "contract": artifact["contract"],
        "id": artifact["id"],
        "path": relative_path.as_posix(),
    }


def cleanup_artifacts(project_root: Path, older_than_days: int) -> dict[str, Any]:
    artifact_root = project_root.resolve() / ".rhdh" / "artifacts"
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    removed: list[str] = []
    if artifact_root.is_dir():
        for path in artifact_root.rglob("*.json"):
            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if modified < cutoff:
                path.unlink()
                removed.append(path.relative_to(project_root.resolve()).as_posix())
    return {"valid": True, "removed": sorted(removed), "olderThanDays": older_than_days}


def _emit(payload: dict[str, Any], force_json: bool) -> None:
    if force_json or not sys.stdout.isatty():
        json.dump(payload, sys.stdout, indent=2 if force_json else None)
        sys.stdout.write("\n")
    elif payload.get("valid"):
        print("Artifact valid")
    else:
        for error in payload.get("errors", []):
            print(f"{error['code']}: {error['message']}", file=sys.stderr)


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Emit structured JSON output")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate, persist, and clean versioned RHDH skill artifacts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate an artifact JSON file")
    validate_parser.add_argument("artifact", type=Path, help="Artifact JSON file")
    _add_json_flag(validate_parser)

    persist_parser = subparsers.add_parser(
        "persist", help="Validate and persist an artifact under .rhdh/artifacts"
    )
    persist_parser.add_argument("artifact", type=Path, help="Artifact JSON file")
    persist_parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root (default: cwd)"
    )
    _add_json_flag(persist_parser)

    cleanup_parser = subparsers.add_parser("cleanup", help="Remove expired persisted artifacts")
    cleanup_parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root (default: cwd)"
    )
    cleanup_parser.add_argument(
        "--older-than-days", type=int, default=30, help="Remove artifacts older than this many days"
    )
    _add_json_flag(cleanup_parser)

    args = parser.parse_args(argv)
    if args.command in {"validate", "persist"}:
        artifact, read_error = _read_artifact(args.artifact)
        if read_error:
            report = read_error
        elif args.command == "validate":
            report = validate_artifact(artifact)
        else:
            report = persist_artifact(artifact, args.project_root)
    else:
        if args.older_than_days < 0:
            report = {
                "valid": False,
                "errors": [
                    {"code": "RETENTION_RANGE", "message": "older-than-days must be non-negative"}
                ],
            }
        else:
            report = cleanup_artifacts(args.project_root, args.older_than_days)

    _emit(report, args.json)
    return 0 if report.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
