---
name: rhdh-ci
description: >-
  Inspects and changes RHDH CI configuration across openshift/release Prow and
  Konflux. Use for OCP/AKS/EKS/GKE jobs, cluster pools, coverage gaps, commissioning
  or decommissioning releases, triggering nightly jobs, or Tekton task migrations.
compatibility: "Python 3.9+ and uv; gh for remote config access; kubectl/oc for Prow triggers; skopeo, jq, yq for Konflux updates."
---

# RHDH CI operations

Use one CI skill for inventory, coverage analysis, generation, triggers, and
pipeline maintenance. Read branches are safe; write branches require an approved
mutation plan.

## Interfaces

- Consumes from `rhdh-platform-support`: `LifecycleAssessment/v1` for
  support-aware coverage.
- Produces: `CiInventory/v1`, `CiCoverageReport/v1`, `ProwRunReceipt/v1`,
  `KonfluxUpdateReport/v1`, `MutationPlan/v1`, and `MutationReceipt/v1`.
- All Prow repository/YAML adapters are local; there is no Python or filesystem
  handoff to another skill.

## Route

| Intent | Load or run | Output |
|---|---|---|
| List OCP jobs or configs | `workflows/ocp-jobs.md` | `CiInventory/v1` |
| List cluster pools | `workflows/ocp-pools.md` | `CiInventory/v1` |
| Analyze OCP coverage | `workflows/ocp-coverage.md` | `CiCoverageReport/v1` |
| List AKS/EKS/GKE jobs | `workflows/k8s-jobs.md` | `CiInventory/v1` |
| Commission a release | `workflows/commission-release.md` | `MutationPlan/v1` |
| Decommission a release | `workflows/decommission-release.md` | `MutationPlan/v1` |
| Trigger a nightly Prow job | `workflows/trigger-nightly.md` | `ProwRunReceipt/v1` |
| Update Konflux Tekton task digests/migrations | `workflows/konflux-task-update.md` | `KonfluxUpdateReport/v1` |

Load only the selected workflow. `references/release-branch-config.md` is shared
local meaning for Prow release branches; the `konflux-*` references are local to
the Konflux branch.

If the nightly adapter lacks `oc`, the dedicated CI context, or valid authentication, emit
`SetupRequired/v1` with route `openshift-ci` and
`nextCommand: "/setup-rhdh-skills openshift-ci"`. This model skill never starts login.
The workflow gives only a kubeconfig path and request data to the private
`gangway_adapter.py`; that adapter alone retrieves the transient native `oc`
credential and authenticates the request.

## Composition

For support-aware coverage, invoke the named skill `rhdh-platform-support` and
consume `LifecycleAssessment/v1`. Do not import its Python package or locate it
on disk. The CI scripts retain local repository/YAML adapters so this skill remains
standalone; `scripts/analyze_coverage.py` uses authoritative APIs directly when it
needs lifecycle facts.

## Read artifacts

- `CiInventory/v1`: `repository`, `mode`, `jobs`, `pools`, `branches`, `warnings`.
- `CiCoverageReport/v1`: `as_of`, `configured`, `supported`, `gaps`, `stale`,
  `review_required`, `sources`.

## Mutation contract

Generating files, editing Prow or Tekton YAML, committing, triggering a job,
pushing, and opening a PR are mutations. Present this before execution:

```json
{
  "contract": "MutationPlan/v1",
  "id": "ci-mutation-<stable-id>",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "summary": "...",
    "operations": [{
      "order": 1,
      "ownerSkill": "rhdh-ci",
      "adapter": "<adapter-name>",
      "operation": "<adapter.operation-name>",
      "target": "...",
      "preview": {"commandOrRequest": "..."},
      "preconditions": [],
      "checks": [],
      "recovery": []
    }],
    "materialHash": "sha256:<canonical-plan-hash>"
  }
}
```

Wait for explicit approval of that exact plan, execute only approved actions, and
return `MutationReceipt/v1` whose `data` contains `planId`, the same
`materialHash`, and exactly one ordered outcome for every planned operation.
Each outcome repeats `order`, `ownerSkill`, `adapter`, `operation`, and `target`,
records `completed`, `failed`, or `skipped`, and includes verification or remaining risk.
For a successful nightly trigger, also return `ProwRunReceipt/v1` with job name,
parameters, API response, and run URL/ID. For Konflux, return
`KonfluxUpdateReport/v1` with digest changes, migrations applied, regenerated
PipelineRuns, verification, and follow-up.

Never push a Konflux update or execute a non-dry-run trigger merely because the
user approved inspection. Decommission plans are destructive and must name every
removed pool/job/config plus rollback.
