---
name: rhdh-jira
description: >-
  Reads and changes Jira work for RHDH projects RHIDP, RHDHPLAN, RHDHBUGS,
  and RHDHSUPP. Use for Jira keys, JQL, issue creation, assignment, refinement,
  sprint planning or reporting, release readiness, support-case intake, or Jira
  status updates.
compatibility: "acli on PATH; Python 3 for bundled deterministic adapters. Windows, macOS, Linux."
---

# RHDH Jira

Route Jira work through one model-invoked skill. Keep credentials out of context and
use the lightest interface that preserves the required fields: authenticated `acli`
for normal and bulk operations, then an authenticated host Atlassian adapter for
relationship-heavy GraphQL reads or unsupported REST fields.

## Interfaces

- Produces: `JiraCapabilities/v1`, `JiraQueryResult/v1`, `SetupRequired/v1`,
  `MutationPlan/v1`, and `MutationReceipt/v1`.
- Invokes by name: `grilling` on create paths. This is a control handoff, never a
  filesystem handoff.

## Route

| Intent | Load |
|---|---|
| Verify Jira/auth capability | `references/auth.md`, then `scripts/setup.py --json` |
| Query Jira or construct JQL | `references/jql-patterns.md`; add `references/graphql-queries.md` for bulk reads |
| Assign work | `references/assign.md` |
| Refine issues or find duplicates | `references/refine.md`, `references/duplicates.md` |
| Prepare a sprint | `references/plan.md` |
| Report a sprint | `references/sprint-report.md` |
| Assess release readiness | `references/release.md` |
| Create a Feature | `references/to-feature.md` |
| Create an Epic | `references/to-epic.md` |
| Create a Story, Task, Bug, Spike, or support issue | `references/to-issue.md`; add `references/support.md` for support cases |
| Update status, fields, links, or comments | `references/update-jira-status.md`, `references/workflows.md` |

Load only the selected branch and the field/auth reference it explicitly needs.
`scripts/command-metadata.json` is the deterministic command catalog.

## Read contract

Return `JiraCapabilities/v1` for setup checks:

```json
{
  "contract": "JiraCapabilities/v1",
  "id": "jira-capabilities",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "adapters": ["acli"],
    "authenticated": true,
    "warnings": []
  }
}
```

If a required capability is false, load `references/auth.md`, emit
`SetupRequired/v1`, and direct the human to `/setup-rhdh-skills jira`. This skill
detects capability but does not create, store, or repair credentials.

Return `JiraQueryResult/v1` for reads:

```json
{
  "contract": "JiraQueryResult/v1",
  "id": "jira-query-<stable-id>",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "query": "...",
    "fields": [],
    "issues": [],
    "truncated": false,
    "warnings": []
  }
}
```

Always use `--limit 500` or pagination for bulk searches and enrich results before
claiming labels, Team, sprint, size, story points, components, or fix versions are
missing. `scripts/parse_issues.py` is the local enrichment adapter.

## Write contract

Issue creation, assignment, transition, edit, link, and comment operations are
mutations. Before any mutation, present a concrete `MutationPlan/v1`:

```json
{
  "contract": "MutationPlan/v1",
  "id": "jira-mutation-<stable-id>",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "summary": "...",
    "operations": [{
      "order": 1,
      "ownerSkill": "rhdh-jira",
      "adapter": "acli",
      "operation": "jira.issue.update",
      "target": "RHIDP-123",
      "preview": {"commandOrRequest": "acli ... --yes"},
      "preconditions": [],
      "checks": [],
      "recovery": ["..."]
    }],
    "materialHash": "sha256:<canonical-plan-hash>"
  }
}
```

Ask for explicit approval of that exact plan. Do not treat earlier discussion as
approval. After approval, execute only the listed actions and return
`MutationReceipt/v1` whose `data` contains the approved plan's `planId` and
`materialHash`, plus `outcomes` containing status, attempted/completed operations,
changed resources, verification, and remaining risks. Reject execution when the
material hash differs.

Create paths have an additional gate: invoke the installed skill named `grilling`
once for Fill Gaps and Challenge, then apply `references/grill.md`. Never locate or
read another skill's files. If `grilling` is unavailable, report the missing named
skill and stop before creation.

## Invariants

- Customer names never go in unprotected fields. Prefer the support case key, add
  `RHDH-Customer`, and place names only in restricted comments.
- Formatted descriptions use ADF from `scripts/jira-wiki-to-adf.py`.
- Mutating `acli` commands use non-interactive flags such as `--yes` when supported.
- REST and GraphQL never receive model-constructed credentials. Use a ready authenticated host
  adapter or return `SetupRequired/v1` for the `atlassian-mcp` setup route.
- Do not remove `rhdh-X.Y-candidate` labels without PM approval.
- Feature Exploration is the process; Refinement is the Jira status.
- Feature-to-Epic hierarchy uses Parent Link, not ordinary issue links.

## Local deterministic adapters

| File | Purpose |
|---|---|
| `scripts/setup.py` | Capability and auth detection; `--json` for structured output |
| `scripts/parse_issues.py` | Enrich, flatten, select, filter, or CSV-export Jira results |
| `scripts/validate_components.py` | Compare documented components with live Jira |
| `scripts/jira-wiki-to-adf.py` | Convert Jira wiki-style templates to ADF JSON |

These scripts are local implementation details. Other skills compose with
`rhdh-jira` through the versioned artifacts above, never through script paths.
