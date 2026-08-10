---
name: rhdh-forge
description: >-
  Reads GitHub on behalf of the other RHDH skills: parse an issue or pull
  request reference, fetch issue detail into IssueContext/v1, resolve the plugin
  workspace an issue belongs to, read check status and failed workflow logs, and
  read repository files through the API. Use for a GitHub issue URL or bare
  #number, "which workspace is this issue in", a stale statusCheckRollup, "why
  did that check fail", gh or jq syntax for a forge read, and the exact payload
  behind a comment, label, assignee, or /publish write.
compatibility: "GitHub CLI authenticated through gh auth login, plus Python 3."
---

# RHDH Forge

One home for reading GitHub. Issue parsing, issue fetch, workspace resolution,
check and workflow-run reads, repository content reads, and the `gh` behaviours
that mislead a caller who has not met them before all live here, because
otherwise every skill that touches a forge keeps its own drifting copy.

This skill reads. It never executes a write.

## Route by outcome

| Outcome | Load and follow |
|---|---|
| Turn an issue reference into structured context | Run `uv run scripts/fetch_issue_context.py <reference>` |
| Parse a reference without a network call | `references/issue-context.md` |
| Resolve the plugin workspace an issue belongs to | `references/issue-context.md` |
| Read PR state, labels, assignees, files, or check status | `references/gh-cli.md` |
| Explain a failing, stale, or missing check | `references/gh-cli.md` |
| Read a file from a repository or a PR branch | `references/gh-cli.md` |
| Prepare a comment, label, assignee, or `/publish` payload | `references/issue-context.md`, then the caller's mutation gate |

Callers invoke this skill by name and consume the artifact. Do not load its
files from another skill.

## Invariants

- Every route here is read-only. A caller that needs a write gets a payload, not
  an execution.
- Construct an issue or PR URL from the resolved owner, repository, and number.
  Never retain the user's raw URL; it may carry a fragment or a query string.
- A Jira key is not this skill's work. Extract it, hand it back, and let the
  caller invoke `/rhdh-jira` for the detail.
- `gh pr checks` and `statusCheckRollup` are cached views and go stale. Confirm
  a check verdict against `gh run list --branch` before acting on it.
- Report an unresolved workspace as unresolved. Guessing one sends a caller into
  the wrong repository.
- Never read a credential file. If `gh auth status` fails, stop and report the
  missing capability.

## Mutation boundary

The command patterns in `references/issue-context.md` and `references/gh-cli.md`
are payloads, not authorization. Before any comment, label, assignee, review, or
`/publish` write, the calling skill states the exact command, repository, issue
or PR number, head SHA, and body or label in `MutationPlan/v1`, obtains approval
of that plan's material hash, and returns `MutationReceipt/v1` with exactly one
outcome per planned operation. `/rhdh-artifacts` owns the envelope, the material
hash rule, and both mutation shapes; this skill does not restate them.

A request to fetch, triage, or analyze is intent to read. It approves no write.

## Artifact contracts

`IssueContext/v1` output, from `scripts/fetch_issue_context.py`:

```yaml
contract: IssueContext/v1
id: github-owner-repo-issue-607
createdAt: ISO-8601
data:
  key: owner/repo#607
  summary: issue title
  source: github
  url: https://github.com/owner/repo/issues/607
  repository: owner/repo
  number: 607
  state: OPEN | CLOSED
  labels: []
  description: full issue body
  workspace: {name: null, strategy: label | body | title | package | unresolved}
  comments: []
```

- `IssueContext/v1`: `key` is `owner/repo#number`, `summary` is the issue title,
  and `source` is `github`.

`/rhdh-jira` emits the same contract with `data.source: jira`, so a caller
consumes either without branching on shape.

Keep an unresolved workspace `null` with `strategy: unresolved` rather than
inventing a name.

## Scripts and references

- `scripts/fetch_issue_context.py` deterministically creates `IssueContext/v1`
  from an issue URL, a bare `#number`, or `owner/repo#number`.
- `references/issue-context.md` covers reference parsing, field extraction,
  workspace resolution, and the gated interaction payloads.
- `references/gh-cli.md` covers `gh` and `jq` read patterns, check and
  workflow-run reads, repository content reads, the failure table, and the
  overlay repository's `/publish` rules.

## Completion

A fetch is complete when `IssueContext/v1` carries `key`, `summary`, and `source`,
`data.url` was rebuilt from the resolved owner, repository, and number rather than
copied from the request, and `data.workspace.strategy` names the rule that
resolved it or reads `unresolved` with `name: null`. A check verdict is complete
only once `gh run list --branch` confirmed it; a `gh pr checks` or
`statusCheckRollup` value alone is a cached view, not a verdict. A write payload
is complete when it states the exact command, repository, issue or PR number, head
SHA, and body or label, and is handed back unexecuted for the caller's mutation
gate. A Jira key found in the issue is reported to the caller, never resolved
here.
