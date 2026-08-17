"""Composition contracts for prose that leaves an RHDH workflow.

These tests pin named-skill seams, not the wording of the prompts around them.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("relative", "anchor", "end_anchor", "register"),
    [
        (
            "skills/plugins/rhdh-pr-review/workflows/review-code.md",
            "Edit before show-user",
            "What this workflow hands on",
            "flavored",
        ),
        (
            "skills/plugins/rhdh-pr-review/workflows/review-operator-pr.md",
            "Phase 7: Findings & Recommendations",
            "</process>",
            "flavored",
        ),
        (
            "skills/jira/rhdh-jira-create/workflows/create-issue.md",
            "Step 6 — Review before creating",
            "Step 7 — Duplicate check",
            "flavored",
        ),
        (
            "skills/jira/rhdh-jira-create/workflows/create-issue.md",
            "Step 9 — Comments",
            "Step 10 — Decompose",
            "flavored",
        ),
        (
            "skills/jira/rhdh-jira-update/workflows/update-issue.md",
            "Compose the status comment",
            "Propose a transition",
            "flavored",
        ),
        (
            "skills/jira/rhdh-jira-refine/workflows/refine-issues.md",
            "Remediation",
            "Writes prefer",
            "flavored",
        ),
        (
            "skills/release/rhdh-release-announce/workflows/freeze-announcement.md",
            "Edit, then present",
            "Step 3 (fallback)",
            "voiced",
        ),
        (
            "skills/release/rhdh-test-plan-review/workflows/review-test-plan.md",
            "Apply changes — post comment",
            "Step 8: Create child tasks",
            "flavored",
        ),
        (
            "skills/plugins/rhdh-pr-create/workflows/create-pull-request.md",
            "Generate a PR title from the commit subject line",
            "Create the PR using `gh pr create`",
            "flavored",
        ),
        (
            "skills/jira/rhdh-jira-link/SKILL.md",
            "Preferred: one-shot create",
            "```bash",
            "flavored",
        ),
        (
            "skills/plugins/rhdh-overlay/workflows/draft-notification.md",
            "Review and Send",
            "</process>",
            "voiced",
        ),
        (
            "skills/plugins/rhdh-overlay/workflows/onboard-plugin.md",
            "Open Pull Request",
            "Trigger Build",
            "flavored",
        ),
        (
            "skills/plugins/rhdh-overlay/workflows/onboard-plugin.md",
            "Take back its per-check results",
            "Phase 6: PR Approval & Merge",
            "flavored",
        ),
        (
            "skills/plugins/rhdh-overlay/workflows/update-plugin.md",
            "Create PR",
            "Trigger Build",
            "flavored",
        ),
        (
            "skills/plugins/rhdh-overlay/workflows/update-plugin.md",
            "Test and Merge",
            "Follow-up record",
            "flavored",
        ),
        (
            "skills/plugins/rhdh-plugin-bug-fix/workflows/fix-bug.md",
            "Triage for agent readiness",
            "Discover workspace and choose mode",
            "flavored",
        ),
        (
            "skills/plugins/rhdh-plugin-midstream-propagate/SKILL.md",
            "Preferred (surgical)",
            "Who owns `.tekton`",
            "flavored",
        ),
        (
            "skills/ci/rhdh-prow-release-branch/workflows/commission-release.md",
            "Verify and summarize",
            "Important Notes",
            "flavored",
        ),
        (
            "skills/ci/rhdh-prow-release-branch/workflows/decommission-release.md",
            "Confirm completion",
            "Important Notes",
            "flavored",
        ),
    ],
)
def test_external_prose_composers_invoke_named_editor(
    relative: str, anchor: str, end_anchor: str, register: str
) -> None:
    text = _text(relative)
    start = text.index(anchor)
    end = text.index(end_anchor, start)
    section = text[start:end]

    assert re.search(
        rf"(?:invoke|run)\s+`/prose-editing`[^\n]*(?:\n[^\n]*){{0,3}}\b{register}\b",
        section,
        re.IGNORECASE,
    )


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("skills/plugins/rhdh-pr-review/workflows/review-operator-pr.md", 1),
        ("skills/jira/rhdh-jira-create/workflows/create-issue.md", 2),
        ("skills/jira/rhdh-jira-update/workflows/update-issue.md", 1),
        ("skills/jira/rhdh-jira-refine/workflows/refine-issues.md", 1),
        ("skills/release/rhdh-test-plan-review/workflows/review-test-plan.md", 1),
        ("skills/plugins/rhdh-pr-create/workflows/create-pull-request.md", 1),
        ("skills/jira/rhdh-jira-link/SKILL.md", 1),
        ("skills/plugins/rhdh-overlay/workflows/draft-notification.md", 1),
        ("skills/plugins/rhdh-overlay/workflows/onboard-plugin.md", 2),
        ("skills/plugins/rhdh-overlay/workflows/update-plugin.md", 2),
        ("skills/plugins/rhdh-plugin-bug-fix/workflows/fix-bug.md", 1),
        ("skills/plugins/rhdh-plugin-midstream-propagate/SKILL.md", 1),
        ("skills/ci/rhdh-prow-release-branch/workflows/commission-release.md", 1),
        ("skills/ci/rhdh-prow-release-branch/workflows/decommission-release.md", 1),
    ],
)
def test_each_final_composer_owns_exactly_one_pass_per_artifact(
    relative: str, expected: int
) -> None:
    assert _text(relative).count("/prose-editing") == expected


def test_final_workflows_own_shared_caller_policy() -> None:
    assert "/prose-editing" not in _text("skills/plugins/rhdh-pr-review/SKILL.md")
    assert "/prose-editing" not in _text("skills/release/rhdh-release-announce/SKILL.md")


def test_konflux_skill_routes_release_data_rpa_updates() -> None:
    text = _text("skills/ci/rhdh-konflux-tasks/SKILL.md")

    assert "workflows/konflux-rpa-update.md" in text


def test_jira_authoring_edits_direct_handback_but_not_caller_handoff() -> None:
    text = _text("skills/reference/rhdh-jira-authoring/SKILL.md")
    completion = text[text.index("## Completion") :]

    assert re.search(
        r"invokes this skill directly.*?invoke `/prose-editing` once.*?flavored",
        completion,
        re.IGNORECASE | re.DOTALL,
    )
    assert "/rhdh-jira-create" in completion
    assert "/rhdh-jira-refine" in completion
    assert re.search(r"calls this skill.*?without editing", completion, re.DOTALL)
    assert text.count("/prose-editing") == 1


def test_pr_and_issue_transport_layers_do_not_reedit_prose() -> None:
    for relative in (
        "skills/plugins/rhdh-pr-review/workflows/post-to-github.md",
        "skills/jira/rhdh-jira-link/scripts/create-pr-mr.js",
        "skills/jira/rhdh-jira-link/scripts/link-pr-mr.js",
        "skills/ci/rhdh-base-images/scripts/base-images-and-rpms.sh",
        "skills/ci/rhdh-konflux-tasks/scripts/update-rpa-tags.sh",
    ):
        assert "/prose-editing" not in _text(relative)


def test_local_authored_artifacts_do_not_get_an_automatic_pass() -> None:
    pr_workflow = _text("skills/plugins/rhdh-pr-create/workflows/create-pull-request.md")
    changeset = pr_workflow[
        pr_workflow.index("Generate changeset per workspace") : pr_workflow.index(
            "Step 7 — Identify build-generated files"
        )
    ]
    assert "/prose-editing" not in changeset

    onboarding = _text("skills/plugins/rhdh-overlay/workflows/onboard-plugin.md")
    catalog_copy = onboarding[
        onboarding.index("Create Plugin Entity") : onboarding.index("Trigger Build & Tests")
    ]
    assert "/prose-editing" not in catalog_copy


def test_base_image_automation_pr_body_passes_static_prose_lint() -> None:
    script = _text("skills/ci/rhdh-base-images/scripts/base-images-and-rpms.sh")
    match = re.search(r'--body "([^"]+)"', script)
    assert match, "expected the fixed automation PR body"

    lint_path = ROOT / "skills/reference/prose-editing/scripts/lint.py"
    spec = importlib.util.spec_from_file_location("prose_editing_lint_callers", lint_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    report = module.lint(match.group(1), register="flavored")
    assert report["total"] == 0


def test_rpa_automation_mr_body_passes_static_prose_lint() -> None:
    script = _text("skills/ci/rhdh-konflux-tasks/scripts/update-rpa-tags.sh")
    fragments = re.findall(r'description="\$\{description\}\n(.*?)"', script, re.DOTALL)
    initial = re.search(r'description="(Generated-by: cursor.*?)"\n', script, re.DOTALL)
    assert initial and fragments, "expected the fixed RPA merge-request template"

    body = "\n".join((initial.group(1), *fragments))
    body = re.sub(r"\$\{[^}]+\}", "VALUE", body)

    lint_path = ROOT / "skills/reference/prose-editing/scripts/lint.py"
    spec = importlib.util.spec_from_file_location("prose_editing_lint_rpa", lint_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    report = module.lint(body, register="flavored")
    assert report["total"] == 0
