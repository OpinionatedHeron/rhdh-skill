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
- GitHub issue reads belong to `/rhdh-forge`, which returns the same
  `IssueContext/v1` with `data.source: github`. Load
  `references/github-input.md` when the request supplies an issue URL or number.
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

`data.files` is the change set. The producing skill does not stage, so those
paths arrive unstaged or untracked: verify them against the working tree, keep
them out of the pre-existing baseline, and stage exactly them alongside the
build-generated files at the workflow's staging gate. An empty index is a stop
condition only when no artifact was supplied.

When no artifact is supplied, derive these fields from the staged diff and ask
only for unresolved issue context or release intent.

## Mutation contract

Read-only inspection, builds, and draft construction do not approve a write. A
push, recording upload, PR creation, or GitHub issue update is a mutation:
invoke the named skill `rhdh-artifacts` and follow its plan, approval hash, and
receipt protocol rather than restating it here.

Operations use `ownerSkill: rhdh-pull-request` with adapter `git` or `github`,
and operation `git.push`, `github.contents.create`,
`github.pull-request.create`, or `github.issue.comment`. Stage exactly the paths
in the approved plan, derived from `ChangeHandoff/v1` `data.files` when a
handoff supplied them. If an earlier operation produces material a later one
needs, such as an uploaded recording URL used in the PR body, close the first
batch with its receipt, build a new exact plan, and obtain a new approval.
Reject legacy `--a` as unsupported. Outcomes also record the changed resource or
URL, verification, and remaining recovery action.

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
