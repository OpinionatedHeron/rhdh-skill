---
name: ask-rhdh
description: Human wayfinder for the RHDH skills collection.
disable-model-invocation: true
---

# Ask RHDH

Turn an RHDH question into one precise model-skill invocation. This is a human entry point,
not a second discovery system: route by outcome and pass context as an artifact.

## Route the request

| Outcome | Model skill |
|---|---|
| Locate a repository, resolve versions, inspect configuration, worklog, or todos | `/rhdh-context` |
| Create, implement, export, wire, upgrade, migrate, diagnose, fix, or place tests for a plugin | `/rhdh-plugin-development` |
| Onboard, update, triage, repair, or publish an Overlay workspace | `/rhdh-overlay` |
| Start, stop, configure, or test RHDH locally | `/rhdh-local` |
| Prepare and submit a pull request | `/rhdh-pull-request` |
| Review code or live-test an operator pull request | `/rhdh-pr-review` |
| Create, refine, query, assign, or update Jira work; plan/report a sprint | `/rhdh-jira` |
| Evaluate RHDH, OpenShift, Kubernetes, PostgreSQL, AKS, EKS, or GKE lifecycle support | `/rhdh-platform-support` |
| Review an RHDH test plan | `/rhdh-test-plan` |
| Inspect or coordinate a release, notes, announcements, CVEs, or RPA data | `/rhdh-release` |
| Inspect or change Prow, nightly jobs, cluster pools, release branches, or Konflux tasks | `/rhdh-ci` |
| Analyze or update downstream base images and RPMs | `/rhdh-base-images` |
| Assess repositories for agent readiness | `/rhdh-agent-readiness` |
| Create, audit, or consolidate an agent skill | `/skill-authoring` |

If the outcome is ambiguous, ask one question that separates the competing rows. Otherwise,
create this handoff in the conversation and invoke the selected model skill:

```json
{
  "contract": "RhdhIntent/v1",
  "id": "intent-<short-id>",
  "createdAt": "<ISO-8601>",
  "data": {
    "domain": "<routing row>",
    "outcome": "<observable result>",
    "inputs": {},
    "constraints": [],
    "approvals": []
  }
}
```

Preserve the user's wording inside `inputs`; do not translate a request into filesystem paths or
implementation details. Routing is complete when exactly one model skill accepts the intent or
reports a concrete `SetupRequired/v1` handoff.
