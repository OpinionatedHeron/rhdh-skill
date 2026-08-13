---
name: rhdh-pr-review
description: >-
  Reviews Red Hat Developer Hub pull requests through a composable
  fetch-analyze-post pipeline, with optional live-cluster verification for
  rhdh-operator changes. Use for a GitHub PR URL or number, code review,
  analysis-only review, inline comments, posting a review, testing operator PR
  images or bundles on a cluster, or a combined code and cluster review.
compatibility: "GitHub CLI and Python 3; oc plus an accessible cluster for operator testing."
---

# RHDH Pull Request Review

Keep forge I/O at the edges: fetch produces context, analysis consumes only
that context and checked-out code, and posting consumes a verified findings
artifact. Cluster testing consumes the same context independently.

## Route by outcome

| Outcome | Workflow sequence |
|---|---|
| Code review and post | `workflows/fetch-github.md` → `workflows/review-code.md` → `workflows/post-to-github.md` |
| Analysis only | `workflows/fetch-github.md` → `workflows/review-code.md`; stop after the humanized draft |
| Test an rhdh-operator PR | `workflows/fetch-github.md` → `workflows/review-operator-pr.md` |
| Full review | fetch → review code → confirm and post → operator cluster test |

A bare PR URL or number defaults to code review and post. For an
`rhdh-operator` PR, offer full review because code and deployable bundle changes
can diverge, but respect an explicit route.

## Review invariants

- Verify every finding against code at the fetched head SHA. Drop stale,
  duplicated, speculative, or convention-conflicting findings.
- Prefer actionable inline comments. Reserve top-level prose for context and
  merge blockers; do not repeat every inline finding.
- Ask which installed specialist skills, if any, the user wants applied after
  fetch and before deep analysis. Invoke chosen skills by name and pass the
  `ReviewContext/v1`; never load their files.
- `/humanizer` is required before any review draft is shown, including
  analysis-only. If unavailable, return:
  `SetupRequired/v1` with `data.missing: [humanizer]` and
  `data.nextCommand: /setup-rhdh-skills`, then stop the draft path. Do not
  implement a local locator or substitute prose rewriting.
- Present the complete humanized draft and review event for confirmation before
  planning any post. An explicit request to post is intent, not approval of the
  exact external mutation.
- For cluster testing, deploy the full PR bundle or manifests, not only the
  operator binary image. Preserve and report the original cluster state and
  cleanup result.

## Mutation contract

Fetch and analysis are read-only. Posting a GitHub review, posting a test
request comment, or changing cluster resources is a mutation: invoke the named
skill `rhdh-mutation-gate` and follow its `MutationPlan/v1` approval hash and
`MutationReceipt/v1` protocol rather than restating it here.

Operations use `ownerSkill: rhdh-pr-review` with adapter `github` or
`openshift`, and operation `github.review.create`, `github.comment.create`,
`openshift.apply`, or `openshift.delete`. Targets pin the head SHA for a review
and the namespace for a cluster change. An earlier confirmation of findings does
not approve the mutation plan. Outcomes also record changed resources or review
URLs, verification, cleanup, and remaining recovery action.

## Artifact contracts

`ReviewContext/v1` from fetch:

```yaml
contract: ReviewContext/v1
id: github-owner-repo-pr-123-sha
createdAt: 2026-08-10T12:00:00Z
data:
  repository: owner/repo
  changeRequest: {forge: github, number: 123, headSha: sha, baseRef: main, headRef: branch}
  files: []
  diff: unified-diff
  linkedIssues: []
  jiraKeys: []
  existingComments: []
  existingReviews: []
  ciStatus: pass | fail | pending | unknown
```

`ReviewFindings/v1` from analysis:

```yaml
contract: ReviewFindings/v1
id: github-owner-repo-pr-123-review
createdAt: 2026-08-10T12:00:00Z
data:
  changeRequest: {repository: owner/repo, number: 123, headSha: sha}
  summary: text
  verdict: COMMENT | APPROVE | REQUEST_CHANGES
  findings: [{path: file, line: 1, startLine: null, type: question | observation | fix, body: text}]
  humanized: true
```

`VerificationEvidence/v1` from operator testing uses `data.subject`,
`data.checks`, and `data.result`; it may also record the deployed bundle or
manifests, original and final cluster state, findings, and cleanup status.

## Scripts and references

- `scripts/fetch_pr_context.py` deterministically creates `ReviewContext/v1`.
- `references/review-perspectives.md` routes optional specialist review lenses.
- `references/humanizer.md` defines the named `/humanizer` gate.
- `references/operator-pr-images.md` defines operator bundle/image extraction.

## Completion

Report the head SHA reviewed, humanized `ReviewFindings/v1`, post receipt when
applicable, every `MutationReceipt/v1`, `VerificationEvidence/v1` when
applicable, and any skipped checks or cleanup actions with reasons.
