#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["rhdh-common"]
#
# [tool.uv.sources]
# rhdh-common = { git = "https://github.com/redhat-developer/rhdh-skill", subdirectory = "packages/rhdh-common" }
# ///
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

from rhdh_common.mutation import (
    MATERIAL_HASH,
    material_hash,
    operation_errors,
    outcome_errors,
    receipt_binding_errors,
)

CONTRACTS_FILE = Path(__file__).with_name("artifact-contracts.json")
STORE_DIRECTORY = "rhdh-skill-artifacts"
CREDENTIAL_KEYS = {
    "auth",
    "accesskey",
    "apikey",
    "apisecret",
    "apitoken",
    "authorization",
    "clientsecret",
    "cookie",
    "credential",
    "credentials",
    "encryptionkey",
    "passphrase",
    "password",
    "privatekey",
    "refreshtoken",
    "secret",
    "secretaccesskey",
    "secretkey",
    "signingkey",
    "sshkey",
    "token",
    "accesstoken",
    "webhooksecret",
}
# An authorization header is a credential wherever it appears. A bare "basic" or
# "bearer" is ordinary prose ("basic auth", "basic example") unless its operand is
# credential-shaped: long enough and carrying a digit or base64 padding.
CREDENTIAL_VALUE = re.compile(
    r"""(?ix)
    authorization \s* : \s* (?: bearer | basic | token ) \s+ \S+
  | \b (?: bearer | basic ) \s+
      (?= [A-Za-z0-9+/=._~-]* [0-9+/=] ) [A-Za-z0-9+/=._~-]{6,}
  | (?: ----- )? BEGIN \s (?: [A-Z0-9]+ \s )* PRIVATE \s KEY (?: \s BLOCK )?
    """
)
OPAQUE_CREDENTIAL_VALUE = re.compile(
    r"(?i)^(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|glpat-[A-Za-z0-9_-]+|"
    r"xox[baprs]-[A-Za-z0-9-]+|sk-[A-Za-z0-9_-]{12,}|AKIA[A-Z0-9]{16})$"
)
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


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


def _redact(matched: str) -> str:
    """Name the offending text without repeating the secret itself."""
    if "private key" in matched.lower():
        return matched.strip()
    words = matched.split()
    if len(words) > 1:
        return " ".join(words[:-1] + ["<redacted>"])
    prefix = re.match(r"^[A-Za-z]+[-_]?", matched)
    return f"{prefix.group(0)}<redacted>" if prefix else "<redacted>"


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
    elif isinstance(value, str):
        match = CREDENTIAL_VALUE.search(value)
        opaque = OPAQUE_CREDENTIAL_VALUE.fullmatch(value)
        if match or opaque:
            offending = _redact(match.group(0) if match else value)
            return {
                "code": "CREDENTIAL_VALUE",
                "message": (f"{path or '<root>'} contains credential-shaped content: {offending}"),
            }
    return None


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
            errors.extend(operation_errors(data.get("operations")))
            if data["materialHash"] != material_hash(data):
                errors.append(
                    {
                        "code": "MATERIAL_HASH",
                        "message": "data.materialHash does not match the canonical plan data",
                    }
                )
        elif contract == "MutationReceipt/v1" and "materialHash" in data:
            errors.extend(outcome_errors(data.get("outcomes")))
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


def artifact_root(project_root: Path) -> Path:
    """Locate this project's artifacts in the operating system temporary directory.

    The project root namespaces the store so two checkouts never collide; it is
    not where artifacts live. The operating system may purge these files between
    sessions, which the store reports as an expired artifact.
    """
    resolved = project_root.resolve()
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:12]
    label = re.sub(r"[^A-Za-z0-9._-]", "-", resolved.name) or "project"
    return Path(tempfile.gettempdir()) / STORE_DIRECTORY / f"{label}-{digest}"


def _expired_error(contract: str, artifact_id: str, producer: str | None) -> dict[str, Any]:
    rerun = f"/{producer}" if producer else "the skill that produced it"
    return {
        "valid": False,
        "errors": [
            {
                "code": "ARTIFACT_EXPIRED",
                "message": (
                    f"{contract} {artifact_id!r} is no longer in the artifact store; "
                    f"temporary storage expires between sessions. Re-run {rerun}."
                ),
            }
        ],
    }


def read_artifact(
    contract: str, artifact_id: str, project_root: Path, producer: str | None = None
) -> dict[str, Any]:
    if not SAFE_ID.fullmatch(artifact_id):
        return {
            "valid": False,
            "errors": [
                {
                    "code": "ARTIFACT_ID",
                    "message": "id must contain only letters, numbers, dots, underscores, and hyphens",
                }
            ],
        }

    path = artifact_root(project_root) / _contract_directory(contract) / f"{artifact_id}.json"
    if not path.is_file():
        return _expired_error(contract, artifact_id, producer)

    artifact, read_error = _read_artifact(path)
    if read_error:
        return read_error
    if not isinstance(artifact, dict) or artifact.get("contract") != contract:
        return {
            "valid": False,
            "errors": [
                {
                    "code": "CONTRACT_MISMATCH",
                    "message": f"{path.name} does not hold a {contract} artifact",
                }
            ],
        }
    return {
        "valid": True,
        "errors": [],
        "contract": contract,
        "id": artifact_id,
        "artifact": artifact,
    }


def persist_artifact(artifact: dict[str, Any], project_root: Path) -> dict[str, Any]:
    report = validate_artifact(artifact)
    if not report["valid"]:
        return report

    if artifact["contract"] == "MutationReceipt/v1":
        plan_id = artifact["data"]["planId"]
        outcomes = artifact["data"].get("outcomes")
        producer = None
        if isinstance(outcomes, list) and outcomes and isinstance(outcomes[0], dict):
            owner = outcomes[0].get("ownerSkill")
            producer = owner if isinstance(owner, str) else None
        plan_report = read_artifact("MutationPlan/v1", plan_id, project_root, producer)
        if not plan_report["valid"]:
            return plan_report
        plan = plan_report["artifact"]
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
        binding_errors = receipt_binding_errors(
            plan["data"]["operations"], artifact["data"]["outcomes"]
        )
        if binding_errors:
            return {"valid": False, "errors": binding_errors}

    destination = (
        artifact_root(project_root)
        / _contract_directory(artifact["contract"])
        / f"{artifact['id']}.json"
    )
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
        "path": destination.as_posix(),
    }


def cleanup_artifacts(project_root: Path, older_than_days: int) -> dict[str, Any]:
    root = artifact_root(project_root)
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    removed: list[str] = []
    if root.is_dir():
        for path in root.rglob("*.json"):
            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if modified < cutoff:
                path.unlink()
                removed.append(path.relative_to(root).as_posix())
    return {
        "valid": True,
        "removed": sorted(removed),
        "olderThanDays": older_than_days,
        "store": root.as_posix(),
    }


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
        "persist", help="Validate and persist an artifact in the temporary artifact store"
    )
    persist_parser.add_argument("artifact", type=Path, help="Artifact JSON file")
    persist_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root that namespaces the store (default: cwd)",
    )
    _add_json_flag(persist_parser)

    read_parser = subparsers.add_parser(
        "read", help="Read a persisted artifact, reporting expiry instead of failing"
    )
    read_parser.add_argument("contract", help="Artifact contract, for example MutationPlan/v1")
    read_parser.add_argument("id", help="Artifact id")
    read_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root that namespaces the store (default: cwd)",
    )
    read_parser.add_argument(
        "--producer", help="Skill to name in the expiry message, for example rhdh-pull-request"
    )
    _add_json_flag(read_parser)

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
    elif args.command == "read":
        report = read_artifact(args.contract, args.id, args.project_root, args.producer)
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
