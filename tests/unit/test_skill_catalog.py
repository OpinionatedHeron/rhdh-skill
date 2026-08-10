"""Behavior tests for the machine-readable skill catalog validator."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = PROJECT_ROOT / "scripts" / "validate_skill_catalog.py"

COMPLETION_SECTION = "\n## Completion\n\nReport what was produced.\n"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_skill_catalog", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_skill(
    root: Path,
    name: str,
    *,
    category: str = "engineering",
    invocation: str = "model",
    body: str = "",
    frontmatter_extra: str = "",
) -> Path:
    """Write a minimal skill that satisfies every rule the fixture is not exercising."""
    skill_dir = root / "skills" / category / name
    (skill_dir / "agents").mkdir(parents=True, exist_ok=True)
    human = "disable-model-invocation: true\n" if invocation == "human" else ""
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Sample {name} skill.\n{human}{frontmatter_extra}---\n\n"
        f"# {name}\n{body}{COMPLETION_SECTION}",
        encoding="utf-8",
    )
    policy = "policy:\n  allow_implicit_invocation: false\n" if invocation == "human" else ""
    (skill_dir / "agents" / "openai.yaml").write_text(
        f"metadata:\n  display_name: {name}\n  short_description: Sample {name} skill.\n{policy}",
        encoding="utf-8",
    )
    return skill_dir


def write_repository(
    root: Path,
    entries: list[dict],
    *,
    contracts: dict | None = None,
    skill_bodies: dict[str, str] | None = None,
) -> Path:
    """Build a throwaway checkout whose catalog and skills the validator can read."""
    bodies = skill_bodies or {}
    for entry in entries:
        write_skill(
            root,
            entry["name"],
            category=entry["category"],
            invocation=entry["invocation"],
            body=bodies.get(entry["name"], ""),
        )
    catalog = root / "skills" / "engineering" / "setup-rhdh-skills" / "assets" / "catalog.json"
    catalog.parent.mkdir(parents=True, exist_ok=True)
    catalog.write_text(
        json.dumps({"schemaVersion": 1, "skills": entries, "pack": {"requiredExternalSkills": []}}),
        encoding="utf-8",
    )
    contracts_file = root / "skills" / "engineering" / "rhdh-context" / "scripts"
    contracts_file.mkdir(parents=True, exist_ok=True)
    (contracts_file / "artifact-contracts.json").write_text(
        json.dumps({"schemaVersion": 1, "contracts": contracts or {}}),
        encoding="utf-8",
    )
    return root


def entry(name: str, **overrides) -> dict:
    base = {"name": name, "category": "engineering", "invocation": "model"}
    base.update(overrides)
    return base


def codes(report: dict) -> list[str]:
    return [error["code"] for error in report["errors"]]


def messages(report: dict, code: str) -> list[str]:
    return [error["message"] for error in report["errors"] if error["code"] == code]


def test_repository_catalog_exposes_the_approved_composable_skill_set():
    """The validator reports the approved promoted catalog through its JSON CLI."""
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--root", str(PROJECT_ROOT), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    report = json.loads(result.stdout)
    assert set(report["promotedSkills"]) == {
        "ask-rhdh",
        "setup-rhdh-skills",
        "rhdh-context",
        "rhdh-artifacts",
        "rhdh-forge",
        "rhdh-plugin-development",
        "rhdh-overlay",
        "rhdh-local",
        "rhdh-pull-request",
        "rhdh-pr-review",
        "rhdh-jira",
        "rhdh-platform-support",
        "rhdh-test-plan",
        "rhdh-release",
        "rhdh-ci",
        "rhdh-base-images",
        "rhdh-agent-readiness",
        "skill-authoring",
    }
    assert set(report["humanInvokedSkills"]) == {"ask-rhdh", "setup-rhdh-skills"}
    assert set(report["requiredExternalSkills"]) == {"grilling", "humanizer"}


def test_repository_satisfies_every_catalog_rule():
    """The checked-in repository passes the full rule set."""
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--root", str(PROJECT_ROOT), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    report = json.loads(result.stdout)
    assert report["valid"] is True, sorted({error["code"] for error in report["errors"]})
    assert result.returncode == 0


def test_in_progress_skills_use_the_internal_root_and_metadata_gate(tmp_path):
    validator = load_validator()
    skill = tmp_path / "internal" / "in-progress" / "draft" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\nname: draft\ndescription: Work in progress\nmetadata:\n  internal: true\n---\n",
        encoding="utf-8",
    )

    errors = []
    validator._validate_internal_skills(tmp_path, errors)
    assert errors == []

    skill.write_text("---\nname: draft\ndescription: Accidentally public\n---\n", encoding="utf-8")
    validator._validate_internal_skills(tmp_path, errors)
    assert errors == [{"code": "IN_PROGRESS_PUBLIC", "message": str(skill)}]

    errors.clear()
    skill.write_text(
        "---\nname: draft\nmetadata:\n  owner: team\npolicy:\n  internal: true\n---\n",
        encoding="utf-8",
    )
    validator._validate_internal_skills(tmp_path, errors)
    assert errors == [{"code": "IN_PROGRESS_PUBLIC", "message": str(skill)}]


def test_cycle_detection_ignores_missing_nodes_already_reported_by_the_catalog_validator():
    validator = load_validator()

    assert validator._find_cycle({"skill": ["missing"]}) is None


def test_workflow_links_are_resolved_from_the_document_directory(tmp_path):
    validator = load_validator()
    workflow = tmp_path / "skills" / "operations" / "sample" / "workflows" / "run.md"
    script = workflow.parent.parent / "scripts" / "run.py"
    workflow.parent.mkdir(parents=True)
    script.parent.mkdir(parents=True)
    script.write_text("print('ok')\n", encoding="utf-8")

    errors = []
    validator._validate_local_links(tmp_path, workflow, "[run](../scripts/run.py)", errors)
    assert errors == []

    validator._validate_local_links(tmp_path, workflow, "[run](scripts/run.py)", errors)
    assert errors == [
        {
            "code": "LINK_MISSING",
            "message": "skills/operations/sample/workflows/run.md -> scripts/run.py",
        }
    ]


def build_fixture(tmp_path, **overrides):
    """A two-skill checkout that passes every rule, ready to be broken one rule at a time."""
    entries = overrides.pop(
        "entries",
        [
            entry("alpha", produces=["Widget/v1"]),
            entry("beta", consumes=["Widget/v1"], requiresSkills=["alpha"]),
        ],
    )
    contracts = overrides.pop("contracts", {"Widget/v1": {"requiredData": ["shape", "size"]}})
    bodies = overrides.pop(
        "skill_bodies",
        {
            "alpha": "\nEmits `Widget/v1`.\n",
            "beta": "\nInvoke `alpha` by name and consume `Widget/v1`.\n",
        },
    )
    assert not overrides, overrides
    return write_repository(tmp_path, entries, contracts=contracts, skill_bodies=bodies)


def test_the_fixture_checkout_passes_every_rule(tmp_path):
    validator = load_validator()

    report = validator.validate_repository(build_fixture(tmp_path))

    assert report["valid"] is True, report["errors"]


def test_a_required_skill_absent_from_the_owning_body_is_reported(tmp_path):
    validator = load_validator()
    root = build_fixture(
        tmp_path,
        skill_bodies={"alpha": "\nEmits `Widget/v1`.\n", "beta": "\nConsumes `Widget/v1`.\n"},
    )

    report = validator.validate_repository(root)

    assert codes(report) == ["DEPENDENCY_NOT_DOCUMENTED"]
    assert "beta: requiresSkills declares alpha" in messages(report, "DEPENDENCY_NOT_DOCUMENTED")[0]


def test_a_dependency_named_only_inside_a_longer_token_does_not_count(tmp_path):
    validator = load_validator()
    root = build_fixture(
        tmp_path,
        skill_bodies={
            "alpha": "\nEmits `Widget/v1`.\n",
            "beta": "\nInvoke `alpha-legacy` and consume `Widget/v1`.\n",
        },
    )

    assert codes(validator.validate_repository(root)) == ["DEPENDENCY_NOT_DOCUMENTED"]


def test_a_slash_prefixed_skill_name_counts_as_documentation(tmp_path):
    validator = load_validator()
    root = build_fixture(
        tmp_path,
        skill_bodies={
            "alpha": "\nEmits `Widget/v1`.\n",
            "beta": "\nInvoke `/alpha` by name and consume `Widget/v1`.\n",
        },
    )

    assert validator.validate_repository(root)["valid"] is True


def test_a_produced_artifact_absent_from_the_owning_body_is_reported(tmp_path):
    validator = load_validator()
    root = build_fixture(
        tmp_path,
        skill_bodies={
            "alpha": "\nEmits something.\n",
            "beta": "\nInvoke `alpha` by name and consume `Widget/v1`.\n",
        },
    )

    report = validator.validate_repository(root)

    assert codes(report) == ["ARTIFACT_NOT_DOCUMENTED"]
    assert "alpha: produces Widget/v1" in messages(report, "ARTIFACT_NOT_DOCUMENTED")[0]


def test_documented_artifact_fields_must_cover_the_contract(tmp_path):
    validator = load_validator()
    root = build_fixture(
        tmp_path,
        skill_bodies={
            "alpha": "\n- `Widget/v1`: `shape`, `color`, and\n  `weight`.\n",
            "beta": "\nInvoke `alpha` by name and consume `Widget/v1`.\n",
        },
    )

    report = validator.validate_repository(root)

    assert codes(report) == ["ARTIFACT_FIELDS_MISMATCH"]
    assert "omit required size" in messages(report, "ARTIFACT_FIELDS_MISMATCH")[0]


def test_a_bullet_that_documents_no_field_is_not_treated_as_a_field_list(tmp_path):
    validator = load_validator()
    root = build_fixture(
        tmp_path,
        skill_bodies={
            "alpha": "\n- `Widget/v1`: emitted once the run finishes.\n",
            "beta": "\nInvoke `alpha` by name and consume `Widget/v1`.\n",
        },
    )

    assert validator.validate_repository(root)["valid"] is True


def test_an_artifact_consumed_but_never_produced_is_reported(tmp_path):
    validator = load_validator()
    root = build_fixture(
        tmp_path,
        entries=[
            entry("alpha", produces=["Widget/v1"]),
            entry("beta", consumes=["Widget/v1", "Gadget/v1"], requiresSkills=["alpha"]),
        ],
        contracts={
            "Widget/v1": {"requiredData": ["shape", "size"]},
            "Gadget/v1": {"requiredData": ["shape"]},
        },
        skill_bodies={
            "alpha": "\nEmits `Widget/v1`.\n",
            "beta": "\nInvoke `alpha` by name; consume `Widget/v1` and `Gadget/v1`.\n",
        },
    )

    report = validator.validate_repository(root)

    assert codes(report) == ["DANGLING_ARTIFACT_EDGE"]
    assert (
        "Gadget/v1 is consumed by beta but produced by no skill"
        in messages(report, "DANGLING_ARTIFACT_EDGE")[0]
    )


def test_an_artifact_produced_but_never_consumed_is_reported(tmp_path):
    validator = load_validator()
    root = build_fixture(
        tmp_path,
        entries=[
            entry("alpha", produces=["Widget/v1", "Gadget/v1"]),
            entry("beta", consumes=["Widget/v1"], requiresSkills=["alpha"]),
        ],
        contracts={
            "Widget/v1": {"requiredData": ["shape", "size"]},
            "Gadget/v1": {"requiredData": ["shape"]},
        },
        skill_bodies={
            "alpha": "\nEmits `Widget/v1` and `Gadget/v1`.\n",
            "beta": "\nInvoke `alpha` by name and consume `Widget/v1`.\n",
        },
    )

    report = validator.validate_repository(root)

    assert codes(report) == ["DANGLING_ARTIFACT_EDGE"]
    assert (
        "Gadget/v1 is produced by alpha but consumed by no skill"
        in messages(report, "DANGLING_ARTIFACT_EDGE")[0]
    )


def test_a_contract_marked_terminal_may_be_produced_without_a_consumer(tmp_path):
    validator = load_validator()
    root = build_fixture(
        tmp_path,
        entries=[
            entry("alpha", produces=["Widget/v1", "Gadget/v1"]),
            entry("beta", consumes=["Widget/v1"], requiresSkills=["alpha"]),
        ],
        contracts={
            "Widget/v1": {"requiredData": ["shape", "size"]},
            "Gadget/v1": {"requiredData": ["shape"], "terminal": True},
        },
        skill_bodies={
            "alpha": "\nEmits `Widget/v1` and `Gadget/v1`.\n",
            "beta": "\nInvoke `alpha` by name and consume `Widget/v1`.\n",
        },
    )

    assert validator.validate_repository(root)["valid"] is True


def test_a_skill_without_a_completion_section_is_reported(tmp_path):
    validator = load_validator()
    root = build_fixture(tmp_path)
    skill_file = root / "skills" / "engineering" / "beta" / "SKILL.md"
    skill_file.write_text(
        skill_file.read_text(encoding="utf-8").replace(COMPLETION_SECTION, "\n"),
        encoding="utf-8",
    )

    report = validator.validate_repository(root)

    assert codes(report) == ["MISSING_COMPLETION"]
    assert messages(report, "MISSING_COMPLETION")[0].startswith(
        "skills/engineering/beta/SKILL.md: add a '## Completion' section"
    )


def test_two_skills_shipping_the_same_content_are_reported(tmp_path):
    validator = load_validator()
    root = build_fixture(tmp_path)
    shared = "\n".join(f"Step {index}: run the check." for index in range(40))
    for skill, header in (
        ("alpha", "# Alpha copy\n\nIntro paragraph.\n\n"),
        ("beta", "# Beta\n\n"),
    ):
        reference = root / "skills" / "engineering" / skill / "references" / "shared.md"
        reference.parent.mkdir(parents=True, exist_ok=True)
        reference.write_text(header + shared + "\n", encoding="utf-8")

    report = validator.validate_repository(root)

    assert codes(report) == ["DUPLICATE_FILE"]
    assert messages(report, "DUPLICATE_FILE")[0].startswith(
        "skills/engineering/alpha/references/shared.md and "
        "skills/engineering/beta/references/shared.md ship the same content"
    )


def test_two_files_inside_one_skill_may_share_content(tmp_path):
    validator = load_validator()
    root = build_fixture(tmp_path)
    shared = "\n".join(f"Step {index}: run the check." for index in range(40))
    for filename in ("first.md", "second.md"):
        reference = root / "skills" / "engineering" / "alpha" / "references" / filename
        reference.parent.mkdir(parents=True, exist_ok=True)
        reference.write_text(shared + "\n", encoding="utf-8")

    assert validator.validate_repository(root)["valid"] is True


def test_a_null_artifact_list_is_reported_instead_of_raising(tmp_path):
    validator = load_validator()
    root = build_fixture(
        tmp_path,
        entries=[
            entry("alpha", produces=None),
            entry("beta", requiresSkills=["alpha"]),
        ],
        contracts={},
        skill_bodies={"alpha": "\nEmits nothing.\n", "beta": "\nInvoke `alpha` by name.\n"},
    )

    report = validator.validate_repository(root)

    assert codes(report) == ["ARTIFACT_LIST_TYPE"]
    assert messages(report, "ARTIFACT_LIST_TYPE")[0].startswith(
        "alpha: produces must be an array of artifact names, got NoneType"
    )


def test_the_codex_host_layout_is_a_leak_like_every_other_host_layout(tmp_path):
    validator = load_validator()
    root = build_fixture(
        tmp_path,
        skill_bodies={
            "alpha": "\nEmits `Widget/v1` into .codex/skills.\n",
            "beta": "\nInvoke `alpha` by name and consume `Widget/v1`.\n",
        },
    )

    report = validator.validate_repository(root)

    assert codes(report) == ["HOST_LAYOUT_LEAK"]
    assert ".codex/skills" in messages(report, "HOST_LAYOUT_LEAK")[0]


def test_invocation_parity_is_checked_in_both_directions(tmp_path):
    validator = load_validator()
    root = build_fixture(
        tmp_path,
        entries=[entry("alpha", invocation="human"), entry("beta")],
        contracts={},
        skill_bodies={"alpha": "\nAsk for it by name.\n", "beta": "\nNothing to declare.\n"},
    )
    beta = root / "skills" / "engineering" / "beta" / "SKILL.md"

    # Catalog says human, frontmatter leaves model invocation enabled.
    write_skill(root, "alpha", invocation="model", body="\nAsk for it by name.\n")
    catalog_human = validator.validate_repository(root)
    assert "INVOCATION_MISMATCH" in codes(catalog_human)
    assert "set disable-model-invocation: true" in messages(catalog_human, "INVOCATION_MISMATCH")[0]

    # Frontmatter disables model invocation, catalog says model.
    write_skill(root, "alpha", invocation="human", body="\nAsk for it by name.\n")
    beta.write_text(
        beta.read_text(encoding="utf-8").replace(
            "description: Sample beta skill.\n",
            'description: Sample beta skill.\ndisable-model-invocation: "true"\n',
        ),
        encoding="utf-8",
    )
    frontmatter_human = validator.validate_repository(root)
    assert "INVOCATION_MISMATCH" in codes(frontmatter_human)
    assert "drop disable-model-invocation" in messages(frontmatter_human, "INVOCATION_MISMATCH")[0]
