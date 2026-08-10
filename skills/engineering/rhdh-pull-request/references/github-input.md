# GitHub input and handoff

Resolve GitHub issue input by composing with `/rhdh-forge`. This skill does not
parse issue URLs, call `gh issue view`, or hold its own copy of the `gh` error
table.

## Read handoff

Invoke `/rhdh-forge` with the raw reference — a URL, a bare `#number`, or
`owner/repo#number` — and consume the `IssueContext/v1` it returns. Take
`data.key`, `data.summary`, `data.source`, `data.url`, `data.repository`,
`data.number`, `data.labels`, and `data.state` from the envelope. Construct
`github_issue_url` from `data.url`; never retain the user's raw input.

`data.source` is `github` here and `jira` when the same contract arrives from
`/rhdh-jira`, so Step 1.5 branches on `data.source`, not on shape.

If `/rhdh-forge` is unavailable, retain the number and repository, leave the
title unresolved, and return `SetupRequired/v1` for the GitHub enrichment
branch. Do not fall back to a local parser or read a credential file.

## Write handoff after PR publication

A comment on the issue or a label change is an external mutation. Plan it in
`MutationPlan/v1` with the exact command, repository, issue number, and body or
label, surface the complete plan and its material hash for approval, execute
only after approval, and return `MutationReceipt/v1`. `/rhdh-forge` supplies the
payload; it executes nothing.

Failure to update the issue does not invalidate a created PR. Preserve the
`PullRequestReceipt/v1` and report the desired issue outcomes for retry.
