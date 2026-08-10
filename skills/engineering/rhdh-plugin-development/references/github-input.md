# GitHub issue input

GitHub issue reads belong to `/rhdh-forge`. Invoke it by name with the raw
reference and consume `IssueContext/v1`; do not parse the URL, run
`gh issue view`, or keep a local copy of its error handling here.

## What comes back

`data.key`, `data.summary`, `data.source`, `data.url`, `data.repository`,
`data.number`, `data.state`, `data.labels`, and `data.description` populate the
issue fields that Step 1 of `workflows/fix-bug.md` records.

`data.workspace` carries the resolved workspace and the strategy that resolved
it — `label`, `body`, `title`, `package`, or `unresolved`. Treat it as a
candidate: confirm the directory exists in the checkout before working in it,
and ask the user when the strategy is `unresolved`.

For a Jira key, invoke `/rhdh-jira` instead. It emits the same contract with
`data.source: jira`.

If `/rhdh-forge` is unavailable, return `SetupRequired/v1` with
`data.missing: [rhdh-forge]` and `data.nextCommand: /setup-rhdh-skills`, then
ask the user for the issue detail rather than guessing at it.

## Issue writes

Commenting a PR link on the issue belongs to `/rhdh-pull-request`, which owns
issue updates after publication. When this skill performs an issue write itself
— adding `not-ready-for-agent`, posting a triage checklist — it is an external
mutation: state the exact command, repository, issue number, and body or label
in `MutationPlan/v1`, obtain approval of its material hash, and return
`MutationReceipt/v1` after execution. A request to fix a bug approves no issue
write.
