---
name: rhdh-test-plan
description: >-
  Reviews an RHDH Jira test plan against release scope, platform support, dates,
  coverage, ownership, and evidence. Use for test-plan review, test-day readiness,
  release validation coverage, or a Jira test-plan URL/key.
compatibility: "Python 3; gog for Google Sheets schedule access when required."
---

# RHDH test-plan review

Review plans as a read-first workflow. The skill owns synthesis; source owners own
Jira, lifecycle, and release facts.

## Interfaces

- Consumes from `rhdh-jira`: `IssueContext/v1` for the plan issue,
  `JiraCapabilities/v1`, `JiraQueryResult/v1`, and, for approved publishing only,
  `MutationReceipt/v1`.
- Consumes from `rhdh-platform-support`: `LifecycleAssessment/v1`.
- Consumes from `rhdh-release`: `ReleaseSnapshot/v1` or `ReleaseSchedule/v1`.
- Produces: `TestPlanDelta/v1`; may propose `MutationPlan/v1` for `rhdh-jira`.

## Intake and route

1. Resolve the plan key or URL and target RHDH version.
2. Load `workflows/review-test-plan.md`.
3. Load `references/sources.md`; load `references/google-sheets-setup.md` only when
   schedule access fails.
4. Gather the named artifacts below, then apply the workflow rubric.

## Named-skill handoffs

- Invoke `rhdh-jira` for the plan, linked issues, ownership, labels, and status.
  Consume `JiraQueryResult/v1`.
- Invoke `rhdh-platform-support` for supported OCP/Kubernetes/database versions.
  Consume `LifecycleAssessment/v1`.
- Invoke `rhdh-release` for milestones and release scope. Consume
  `ReleaseSnapshot/v1` or `ReleaseSchedule/v1`.

Never find, read, or execute a sibling skill's files. If a named skill is absent,
report that dependency and the review dimension that remains unverified.

Local scripts `check_gsheets.py` and `fetch_schedule.py` are deterministic
adapters for schedule access, not cross-skill interfaces. `gog` keeps Google
credentials behind its native interface.

## Output contract

Return the shared `TestPlanDelta/v1` contract:

```json
{
  "contract": "TestPlanDelta/v1",
  "id": "test-plan-rhidp-123",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "source": {"plan": "RHIDP-123", "release": "1.x"},
    "changes": [],
    "findings": [{
      "verdict": "ready|ready-with-risks|not-ready|incomplete",
      "coverage": [],
      "gaps": [],
      "risks": [],
      "owners": [],
      "evidence": [],
      "unverified": []
    }]
  }
}
```

Separate absent coverage from unavailable evidence. Cite the issue, sheet range,
or lifecycle source supporting each material finding.

## Optional Jira update

Do not edit Jira as part of the read-only review. If the user asks to publish the
review, invoke `rhdh-jira` with a `MutationPlan/v1` whose targets, comment body,
field changes, risks, rollback, and verification are explicit. Wait for approval,
then consume and surface its `MutationReceipt/v1` in the final review.

## Completion

Complete when every rubric dimension in `workflows/review-test-plan.md` carries a
verdict in `data.findings`, every material finding cites the issue key, sheet
range, or lifecycle source behind it, and each dimension the review could not
verify appears in `unverified` naming the skill or source that was unavailable.
Absent coverage belongs in `gaps` and missing evidence belongs in `unverified`; a
dimension may not be omitted from both. When publishing was requested, complete
only after `rhdh-jira` returns a `MutationReceipt/v1` whose outcomes cover every
operation in the approved `MutationPlan/v1` and that receipt appears in the
review.
