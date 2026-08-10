---
name: rhdh-overlay
description: >-
  Manages the rhdh-plugin-export-overlays repository and Extensions Catalog:
  onboard plugins, update upstream versions, repair export or publish failures,
  inspect workspace health, triage and analyze overlay pull requests, and
  trigger publish checks. Use for source.json, plugins-list.yaml,
  backstage.json, catalog metadata, overlay CI, plugin import, overlay PRs, or
  testing exact PR artifacts before merge.
compatibility: "Git, GitHub CLI, Python 3, and a checkout of rhdh-plugin-export-overlays."
---

# RHDH Overlay

Own catalog packaging and overlay-repository operations. Work from a checkout
whose remote identifies `redhat-developer/rhdh-plugin-export-overlays`; do not
depend on another installed skill's files or CLI.

## Start here

1. Read repository instructions and run `gh auth status`.
2. Confirm the checkout and remote with `git remote -v`.
3. Inspect the target workspace, a similar workspace, and the relevant PR or CI
   logs before changing metadata.
4. For environment problems, follow `workflows/doctor.md`.

## Route by outcome

| Outcome | Load and follow |
|---|---|
| Onboard a plugin | `workflows/onboard-plugin.md` |
| Update source version or commit | `workflows/update-plugin.md` |
| Diagnose an export or publish failure | `workflows/fix-build.md` |
| Check workspace status | `references/overlay-repo.md`, then inspect workspace files and recent `gh` runs |
| Triage the open PR backlog | `workflows/triage-prs.md`; use `scripts/triage-prs.py` for deterministic classification |
| Analyze one overlay PR | `workflows/analyze-pr.md`; use `scripts/analyze-pr.py` |
| Draft stale-PR notifications | `workflows/draft-notification.md` |
| Trigger publish | Run the guarded publish procedure below |

Infer a clear route. Ask only for a missing plugin, workspace, source ref, or PR
number that cannot be discovered from the checkout.

## Invariants

- Every export is configured in the overlay repository; CI performs the export.
- `source.json` `repo-backstage-version` is the upstream source's actual
  Backstage version. `backstage.json` `version` is the RHDH compatibility
  override. Never substitute one for the other.
- Derive packages and refs from upstream and generated metadata; never invent an
  OCI URL.
- Copy the structure of a current, similar workspace when repository conventions
  differ from this skill's examples.
- Before merge, test the exact PR artifact. Authentication errors from an
  otherwise loaded plugin may be acceptable; installation or boot errors are
  not.

## Guarded publish

Before posting `/publish`, verify the PR is open, lacks `do-not-merge`, and has
no successful publish check for the current head. Construct this exact plan:

```yaml
contract: MutationPlan/v1
id: overlay-publish-plan-id
createdAt: ISO-8601
data:
  summary: Trigger Overlay publication for the current PR head
  operations:
    - order: 1
      ownerSkill: rhdh-overlay
      adapter: github
      operation: github.comment.create
      target: redhat-developer/rhdh-plugin-export-overlays#<number>@<head-sha>
      preview: {body: /publish}
      preconditions: [open, no-do-not-merge, no-successful-publish-for-head]
      checks: [capture-comment-url, capture-publish-check-url]
      recovery: [report-comment-for-manual-removal-if-trigger-was-wrong]
  materialHash: sha256:<canonical-plan-data-hash>
```

Compute `materialHash` from the UTF-8 JSON encoding of the complete `data`
object after removing `materialHash`, with keys sorted and separators `,` and
`:`. This binds the summary and every material operation field. Show the
complete plan and exact hash. Only after the user approves that hash, run:

```bash
gh pr comment <number> --repo redhat-developer/rhdh-plugin-export-overlays --body "/publish"
```

Return:

```yaml
contract: MutationReceipt/v1
id: overlay-publish-receipt-id
createdAt: ISO-8601
data:
  planId: overlay-publish-plan-id
  materialHash: sha256:<approved-hash>
  outcomes:
    - order: 1
      ownerSkill: rhdh-overlay
      adapter: <same-as-plan-operation>
      operation: <same-as-plan-operation>
      target: <same-as-plan-operation>
      status: completed | failed | skipped
```

Return exactly one ordered outcome for every planned operation, including
failures and skips; identity fields must match the plan. Outcomes also include
the comment and check URLs or failure plus recovery. A request to trigger
publication is intent, not approval of the exact plan.

## Other external mutations

The same contract applies to every push, PR creation, notification, or other
external write in a selected workflow. Build the plan only after targets and
payloads are exact. Re-plan and obtain a new hash approval when a branch, head
SHA, file set, PR body, comment, or recipient changes. Execute no workflow
command absent from the approved operations and return one
`MutationReceipt/v1` per approved batch. Read-only triage and analysis need no
plan.

## Artifact contracts

Input is `ChangeHandoff/v1`; use these additional `data` fields:

```yaml
contract: ChangeHandoff/v1
id: overlay-request-id
createdAt: ISO-8601
data:
  summary: overlay request
  files: []
  verification:
    contract: VerificationEvidence/v1
    id: source-verification-id
    createdAt: ISO-8601
    data: {subject: source-ref, checks: [], result: pending}
  sourceRepository: owner/repo
  sourceRef: commit-or-tag
  packages: []
  upstreamBackstageVersion: "1.x.y"
  targetRhdh: "1.x"
```

Output is `OverlayChange/v1`:

```yaml
contract: OverlayChange/v1
id: overlay-change-id
createdAt: ISO-8601
data:
  workspace: name
  changes: {sourceRef: commit-or-tag, packages: [], metadataFiles: []}
  verification:
    contract: VerificationEvidence/v1
    id: overlay-verification-id
    createdAt: ISO-8601
    data: {subject: overlay-change-id, checks: [], result: pass | fail | partial}
  pullRequest: null
  publishStatus: not-requested | pending | passed | failed
  mutationReceipts: []
```

For local verification, invoke `/rhdh-local` with `ChangeHandoff/v1` derived
from `OverlayChange/v1`: exact artifact values, plugin config, named
environment variables, and checks. Consume `VerificationEvidence/v1`.
Do not load the local skill's files.

## Completion

Report workspace and metadata changes, commands or scripts run, CI and local
verification evidence, mutation receipts, remaining compatibility risks, and
the final `OverlayChange/v1`.
