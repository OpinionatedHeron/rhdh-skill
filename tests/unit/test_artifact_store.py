"""Behavior tests for versioned artifact validation and persistence."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_STORE = (
    PROJECT_ROOT / "skills" / "engineering" / "rhdh-context" / "scripts" / "artifact_store.py"
)
SHARED_PACKAGE = PROJECT_ROOT / "packages" / "rhdh-common"


def run_store(*args: str) -> subprocess.CompletedProcess[str]:
    # The store depends on rhdh_common (ADR-0006); uv resolves it from the
    # PEP-723 block, and this subprocess resolves it from the source checkout.
    return subprocess.run(
        [sys.executable, str(ARTIFACT_STORE), *args],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(SHARED_PACKAGE)},
    )


def mutation_plan() -> dict:
    data = {
        "summary": "Create the approved pull request",
        "operations": [
            {
                "order": 1,
                "ownerSkill": "rhdh-pull-request",
                "adapter": "github",
                "operation": "github.pull-request.create",
                "target": "redhat-developer/example",
                "preview": {"commandOrRequest": {"base": "main", "head": "fix"}},
                "preconditions": [],
                "checks": [],
                "recovery": [],
            }
        ],
    }
    canonical = json.dumps(data, separators=(",", ":"), sort_keys=True)
    data["materialHash"] = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
    return {
        "contract": "MutationPlan/v1",
        "id": "plan-123",
        "createdAt": "2026-08-10T12:00:00Z",
        "data": data,
    }


def canonical_rehash(artifact: dict) -> dict:
    material = {key: value for key, value in artifact["data"].items() if key != "materialHash"}
    canonical = json.dumps(material, separators=(",", ":"), sort_keys=True)
    artifact["data"]["materialHash"] = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
    return artifact


def mutation_outcomes(plan: dict) -> list[dict]:
    return [
        {
            "order": operation["order"],
            "ownerSkill": operation["ownerSkill"],
            "adapter": operation["adapter"],
            "operation": operation["operation"],
            "target": operation["target"],
            "status": "completed",
        }
        for operation in plan["data"]["operations"]
    ]


def test_validated_artifact_can_be_persisted_outside_source_control(tmp_path):
    artifact_file = tmp_path / "plan.json"
    artifact_file.write_text(json.dumps(mutation_plan()), encoding="utf-8")

    validation = run_store("validate", str(artifact_file), "--json")
    assert validation.returncode == 0, validation.stderr or validation.stdout
    assert json.loads(validation.stdout)["valid"] is True

    persistence = run_store(
        "persist",
        str(artifact_file),
        "--project-root",
        str(tmp_path),
        "--json",
    )
    assert persistence.returncode == 0, persistence.stderr or persistence.stdout
    receipt = json.loads(persistence.stdout)
    persisted = Path(receipt["path"])
    assert Path(tempfile.gettempdir()).resolve() in persisted.resolve().parents
    assert tmp_path.resolve() not in persisted.resolve().parents
    assert persisted.parent.name == "mutation-plan"
    assert persisted.name == "plan-123.json"
    assert json.loads(persisted.read_text(encoding="utf-8")) == mutation_plan()


def test_persisted_artifacts_are_namespaced_by_project_root(tmp_path):
    artifact_file = tmp_path / "plan.json"
    artifact_file.write_text(json.dumps(mutation_plan()), encoding="utf-8")
    other_root = tmp_path / "other-checkout"
    other_root.mkdir()

    first = json.loads(
        run_store("persist", str(artifact_file), "--project-root", str(tmp_path), "--json").stdout
    )
    second = json.loads(
        run_store("persist", str(artifact_file), "--project-root", str(other_root), "--json").stdout
    )

    assert first["path"] != second["path"]


def test_reading_a_purged_artifact_reports_expiry_and_names_the_producer(tmp_path):
    result = run_store(
        "read",
        "MutationPlan/v1",
        "plan-123",
        "--project-root",
        str(tmp_path),
        "--producer",
        "rhdh-pull-request",
        "--json",
    )

    assert result.returncode == 1
    error = json.loads(result.stdout)["errors"][0]
    assert error["code"] == "ARTIFACT_EXPIRED"
    assert "rhdh-pull-request" in error["message"]
    assert "Traceback" not in result.stderr


def test_receipt_persistence_reports_an_expired_plan_rather_than_a_missing_file(tmp_path):
    plan = mutation_plan()
    receipt = {
        "contract": "MutationReceipt/v1",
        "id": "receipt-expired",
        "createdAt": "2026-08-10T12:01:00Z",
        "data": {
            "planId": plan["id"],
            "materialHash": plan["data"]["materialHash"],
            "outcomes": mutation_outcomes(plan),
        },
    }
    receipt_file = tmp_path / "receipt.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    result = run_store("persist", str(receipt_file), "--project-root", str(tmp_path), "--json")

    assert result.returncode == 1
    error = json.loads(result.stdout)["errors"][0]
    assert error["code"] == "ARTIFACT_EXPIRED"
    assert "/rhdh-pull-request" in error["message"]


@pytest.mark.parametrize(
    "prose",
    [
        "basic auth is required",
        "a basic example of the bearer flow",
        "basic block layout",
        "basic auth-token setup notes",
    ],
)
def test_artifact_store_accepts_prose_that_mentions_basic_or_bearer(tmp_path, prose):
    artifact = mutation_plan()
    artifact["data"]["operations"][0]["preview"]["commandOrRequest"]["body"] = prose
    canonical_rehash(artifact)
    artifact_file = tmp_path / "prose-plan.json"
    artifact_file.write_text(json.dumps(artifact), encoding="utf-8")

    result = run_store("validate", str(artifact_file), "--json")

    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["valid"] is True


@pytest.mark.parametrize(
    "secret",
    [
        # PEM headers only, no key material: these assert the scanner rejects them.
        "-----BEGIN OPENSSH PRIVATE KEY-----",  # gitleaks:allow
        "-----BEGIN EC PRIVATE KEY-----",  # gitleaks:allow
        "-----BEGIN PGP PRIVATE KEY BLOCK-----",  # gitleaks:allow
        "Authorization: Bearer abc123",
        "Bearer eyJhbGciOi.J9x_1",
    ],
)
def test_artifact_store_rejects_private_keys_and_authorization_headers(tmp_path, secret):
    artifact = mutation_plan()
    artifact["data"]["operations"][0]["preview"]["commandOrRequest"]["body"] = secret
    canonical_rehash(artifact)
    artifact_file = tmp_path / "secret-body-plan.json"
    artifact_file.write_text(json.dumps(artifact), encoding="utf-8")

    result = run_store("validate", str(artifact_file), "--json")

    assert result.returncode == 1
    error = json.loads(result.stdout)["errors"][0]
    assert error["code"] == "CREDENTIAL_VALUE"
    assert "contains credential-shaped content:" in error["message"]


def test_artifact_store_rejects_credentials_at_any_depth(tmp_path):
    artifact = mutation_plan()
    artifact["data"]["operations"][0]["token"] = "should-never-be-persisted"
    artifact_file = tmp_path / "secret-plan.json"
    artifact_file.write_text(json.dumps(artifact), encoding="utf-8")

    result = run_store("persist", str(artifact_file), "--project-root", str(tmp_path), "--json")

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["valid"] is False
    assert report["errors"] == [
        {
            "code": "CREDENTIAL_FIELD",
            "message": "data.operations[0].token is not allowed in an artifact",
        }
    ]
    assert not (tmp_path / ".rhdh" / "artifacts").exists()


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("privateKey", "private material", "CREDENTIAL_FIELD"),
        ("auth", "email:token", "CREDENTIAL_FIELD"),
        ("credential", "email:token", "CREDENTIAL_FIELD"),
        ("headers", ["Authorization: Bearer abc123"], "CREDENTIAL_VALUE"),
        ("X-Api-Key", "gh" + "p_this_is_a_secret_value", "CREDENTIAL_FIELD"),
        ("githubTokenValue", "opaque-secret-value", "CREDENTIAL_FIELD"),
    ],
)
def test_artifact_store_rejects_common_credential_shapes(tmp_path, field, value, code):
    artifact = mutation_plan()
    artifact["data"][field] = value
    artifact_file = tmp_path / "credential-plan.json"
    artifact_file.write_text(json.dumps(artifact), encoding="utf-8")

    result = run_store("validate", str(artifact_file), "--json")

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["valid"] is False
    assert report["errors"][0]["code"] == code


def test_artifact_store_rejects_compound_api_key_headers(tmp_path):
    artifact = mutation_plan()
    artifact["data"]["operations"][0]["preview"]["headers"] = {
        "X-Api-Key": "gh" + "p_this_is_a_secret_value"
    }
    artifact_file = tmp_path / "header-secret-plan.json"
    artifact_file.write_text(json.dumps(artifact), encoding="utf-8")

    result = run_store("validate", str(artifact_file), "--json")

    assert result.returncode == 1
    assert json.loads(result.stdout)["errors"][0] == {
        "code": "CREDENTIAL_FIELD",
        "message": "data.operations[0].preview.headers.X-Api-Key is not allowed in an artifact",
    }


def test_artifact_store_rejects_a_plan_changed_after_hashing(tmp_path):
    artifact = mutation_plan()
    artifact["data"]["operations"][0]["target"] = "redhat-developer/other"
    artifact_file = tmp_path / "tampered-plan.json"
    artifact_file.write_text(json.dumps(artifact), encoding="utf-8")

    result = run_store("validate", str(artifact_file), "--json")

    assert result.returncode == 1
    assert json.loads(result.stdout)["errors"][0]["code"] == "MATERIAL_HASH"


def test_artifact_store_rejects_incomplete_mutation_operations(tmp_path):
    artifact = mutation_plan()
    del artifact["data"]["operations"][0]["recovery"]
    material = {key: value for key, value in artifact["data"].items() if key != "materialHash"}
    canonical = json.dumps(material, separators=(",", ":"), sort_keys=True)
    artifact["data"]["materialHash"] = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
    artifact_file = tmp_path / "incomplete-plan.json"
    artifact_file.write_text(json.dumps(artifact), encoding="utf-8")

    result = run_store("validate", str(artifact_file), "--json")

    assert result.returncode == 1
    assert json.loads(result.stdout)["errors"][0] == {
        "code": "MUTATION_OPERATION",
        "message": "data.operations[0].recovery must be an array",
    }


def test_receipt_persistence_requires_the_matching_approved_plan(tmp_path):
    plan = mutation_plan()
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    assert run_store("persist", str(plan_file), "--project-root", str(tmp_path)).returncode == 0

    receipt = {
        "contract": "MutationReceipt/v1",
        "id": "receipt-123",
        "createdAt": "2026-08-10T12:01:00Z",
        "data": {
            "planId": plan["id"],
            "materialHash": "sha256:" + ("0" * 64),
            "outcomes": mutation_outcomes(plan),
        },
    }
    receipt_file = tmp_path / "receipt.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    mismatch = run_store("persist", str(receipt_file), "--project-root", str(tmp_path), "--json")
    assert mismatch.returncode == 1
    assert json.loads(mismatch.stdout)["errors"][0]["code"] == "PLAN_HASH_MISMATCH"

    receipt["data"]["materialHash"] = plan["data"]["materialHash"]
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")
    matched = run_store("persist", str(receipt_file), "--project-root", str(tmp_path), "--json")
    assert matched.returncode == 0, matched.stderr or matched.stdout


@pytest.mark.parametrize(
    "secret_data",
    [
        {"api": {"key": "opaque-value"}},
        {"value": "gh" + "p_this_is_a_secret_value"},
    ],
)
def test_artifact_store_rejects_credentials_split_across_paths_or_opaque_values(
    tmp_path, secret_data
):
    artifact = mutation_plan()
    artifact["data"]["operations"][0]["preview"]["request"] = secret_data
    artifact_file = tmp_path / "path-secret-plan.json"
    artifact_file.write_text(json.dumps(artifact), encoding="utf-8")

    result = run_store("validate", str(artifact_file), "--json")

    assert result.returncode == 1
    assert json.loads(result.stdout)["errors"][0]["code"] in {
        "CREDENTIAL_FIELD",
        "CREDENTIAL_VALUE",
    }


def test_receipt_requires_one_identity_bound_outcome_per_planned_operation(tmp_path):
    plan = mutation_plan()
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    assert run_store("persist", str(plan_file), "--project-root", str(tmp_path)).returncode == 0

    receipt = {
        "contract": "MutationReceipt/v1",
        "id": "receipt-operations",
        "createdAt": "2026-08-10T12:01:00Z",
        "data": {
            "planId": plan["id"],
            "materialHash": plan["data"]["materialHash"],
            "outcomes": mutation_outcomes(plan),
        },
    }
    receipt_file = tmp_path / "receipt.json"

    receipt["data"]["outcomes"] = []
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")
    missing = run_store("persist", str(receipt_file), "--project-root", str(tmp_path), "--json")
    assert missing.returncode == 1
    assert json.loads(missing.stdout)["errors"][0]["code"] == "MUTATION_OUTCOMES"

    receipt["data"]["outcomes"] = mutation_outcomes(plan)
    receipt["data"]["outcomes"][0]["target"] = "redhat-developer/different"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")
    mismatched = run_store("persist", str(receipt_file), "--project-root", str(tmp_path), "--json")
    assert mismatched.returncode == 1
    assert json.loads(mismatched.stdout)["errors"][0]["code"] == "RECEIPT_OUTCOME_MISMATCH"
