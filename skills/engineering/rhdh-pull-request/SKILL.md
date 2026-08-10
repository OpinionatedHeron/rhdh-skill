---
name: rhdh-pull-request
description: >-
  Publishes verified changes from rhdh-plugins or community-plugins: detect the
  repository and affected workspaces, run the repository build pipeline,
  create package changesets, stage generated files safely, create a signed-off
  commit and branch, push, open a GitHub pull request, upload optional bug-fix
  recordings, and link Jira or GitHub issues. Use for raise PR, create or open
  a plugin PR, push verified plugin changes, or publish ChangeHandoff/v1.
compatibility: "Git, GitHub CLI, Yarn, and a rhdh-plugins or community-plugins checkout."
---

# RHDH Pull Request

Own publication after implementation is verified. Accept either the current
staged checkout or `ChangeHandoff/v1`; do not diagnose or modify product code.

## Start here

1. Load `references/repo-profiles.md` and identify the canonical upstream from
   all remotes.
2. Run `gh auth status` and inspect branch, status, staged diff, and upstream
   default branch.
3. If `ChangeHandoff/v1` is provided, validate its repository and files,
   issue fields, recordings, and verification evidence against the checkout.
   Treat the checkout as authoritative and report mismatches.
4. Follow `workflows/create-pull-request.md` sequentially. There is no
   auto-approve mode: an external write requires approval of its exact
   `MutationPlan/v1` material hash.

## Boundaries

- This skill stages, formats, validates, creates changesets, commits, pushes,
  opens the PR, uploads supplied recordings, and updates linked GitHub issues.
  Jira reads and writes belong to `/rhdh-jira` and cross this boundary only as
  `IssueContext/v1`, `MutationPlan/v1`, and `MutationReceipt/v1` artifacts.
- It does not implement fixes or features. If validation exposes a product-code
  failure, return failed `VerificationEvidence/v1` to
  `/rhdh-plugin-development` with the command and evidence.
- Pre-existing dirty or untracked files are outside the publication set unless
  the user explicitly identifies them as part of the change.
- Only published plugin source paths need changesets; private `packages/*`, dev
  apps, tests, fixtures, and stories do not.
- Never fabricate issue data, recording URLs, CI results, or reviewer evidence.

## Input contract

`ChangeHandoff/v1`:

```yaml
contract: ChangeHandoff/v1
id: change-id
createdAt: ISO-8601
data:
  summary: change summary
  files: []
  verification:
    contract: VerificationEvidence/v1
    id: change-verification-id
    createdAt: ISO-8601
    data: {subject: change-id, checks: [], result: pass}
```

When no artifact is supplied, derive these fields from the staged diff and ask
only for unresolved issue context or release intent.

## Mutation contract

Read-only inspection, builds, and draft construction do not approve a write.
Before a push, recording upload, PR creation, or GitHub issue update, construct
the exact external batch as this artifact:

```yaml
contract: MutationPlan/v1
id: pr-publication-plan-id
createdAt: ISO-8601
data:
  summary: Publish the prepared plugin change
  operations:
    - order: 1
      ownerSkill: rhdh-pull-request
      adapter: github
      operation: git.push | github.contents.create | github.pull-request.create | github.issue.comment
      target: owner/repository-or-resource
      preview: {commandOrRequest: exact-structured-input}
      preconditions: []
      checks: []
      recovery: []
  materialHash: sha256:<canonical-plan-data-hash>
```

Compute `materialHash` from the UTF-8 JSON encoding of the complete `data`
object after removing `materialHash`, with keys sorted and separators `,` and
`:`. This binds the summary and every material operation field. Present the
complete plan and exact hash. Execute only after the user approves that hash.
If an earlier operation produces material needed by a later one (for example
an uploaded recording URL used in the PR body), close the first batch with a
receipt, build a new exact plan, and obtain a new approval. A prior request to
publish is intent, not plan approval. Reject legacy `--a` as unsupported.

After each approved batch, return:

```yaml
contract: MutationReceipt/v1
id: pr-publication-receipt-id
createdAt: ISO-8601
data:
  planId: pr-publication-plan-id
  materialHash: sha256:<approved-hash>
  outcomes:
    - order: 1
      ownerSkill: rhdh-pull-request
      adapter: <same-as-plan-operation>
      operation: <same-as-plan-operation>
      target: <same-as-plan-operation>
      status: completed | failed | skipped
```

Return exactly one ordered outcome for every planned operation, including
failures and operations skipped after a failure. Its order, owner, adapter,
operation, and target must match the plan. Also record the changed resource or
URL, verification, and remaining recovery action. Never execute an operation
absent from the approved plan.

## Output contract

`PullRequestReceipt/v1`:

```yaml
contract: PullRequestReceipt/v1
id: pull-request-id
createdAt: ISO-8601
data:
  url: url
  repository: owner/repo
  head: {branch: name, commit: sha}
  changesets: []
  recordingUrls: {before: null, after: null}
  issueUpdates: []
  mutationReceipts: []
```

Return exact URLs and SHAs from command output. If any external update fails,
keep the successful PR receipt and record the failed update rather than hiding
it.

## Completion

Report the branch, commit, PR URL, generated changesets, uploaded evidence,
issue updates, mutation receipts, and final `PullRequestReceipt/v1`. A created PR is not complete
until its URL is captured and the requested artifact upload gates have either
succeeded or been reported for manual action.
