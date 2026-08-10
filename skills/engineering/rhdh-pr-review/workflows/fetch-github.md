# Workflow: Fetch GitHub PR Context

Fetch PR metadata, diff, linked issues, existing comments, and CI status from GitHub. Produces `ReviewContext/v1` for `review-code.md` and `review-operator-pr.md`.

## Script

Run the fetch script to collect all PR context in one call:

```bash
python scripts/fetch_pr_context.py <PR_URL_OR_NUMBER> [--repo owner/repo]
```

The path is relative to the skill directory.

The script accepts:

- A full URL: `https://github.com/owner/repo/pull/123`
- A number (detects repo from git remote): `123`
- A shorthand: `owner/repo#123`

Optional flags:

- `--repo owner/repo` — override repo detection
- `--no-diff` — skip diff (metadata-only queries)
- `--no-comments` — skip existing review comments
- `--no-issues` — skip fetching linked GitHub issues

Consume the full JSON output. Do not pipe through `head`, `tail`, or `grep`.

## ReviewContext/v1

The script outputs this structure as JSON:

```
ReviewContext/v1
├── contract: "ReviewContext/v1"
├── id, createdAt
└── data
    ├── repository: "owner/repo"
    ├── changeRequest: {forge, number, headSha, baseRef, headRef, title, body, author, state, url, labels}
    ├── files: [{path, additions, deletions}, ...]
    ├── totalAdditions, totalDeletions
    ├── diff: "full unified diff text"
    ├── linkedIssues: [{number, title, body, labels, state}, ...]
    ├── jiraKeys: ["RHIDP-1234", ...]
    ├── existingComments: [{user, path, line, body, createdAt}, ...]
    ├── existingReviews: [{user, state, body}, ...]
    └── ciStatus: "pass" | "fail" | "pending" | "unknown"
```

## Jira keys

The script extracts Jira keys (for example, `RHIDP-1234`) from the PR body but
does not fetch them. When Jira detail affects the review, invoke `/rhdh-jira`
with the keys and consume `IssueContext/v1` or `JiraQueryResult/v1`. Otherwise
retain the keys and continue. Do not select a Jira transport or inspect Jira
credentials from this workflow.

## After fetching

Proceed to the workflow the router selected (typically `review-code.md`). Pass the full `ReviewContext/v1` — downstream workflows depend on its structure.
