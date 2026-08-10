# Workflow: Retrieve Release and Key Dates

Table of release versions with five critical dates: Feature Freeze, Code Freeze, Doc Freeze, Go/No Go, GA Announce.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | Invoke `rhdh-jira`; require the needed capability in `JiraCapabilities/v1` |

If Jira capability is missing, surface `SetupRequired/v1` and direct the human to
`/setup-rhdh-skills jira`.

</prerequisites>

<process>

## Step 1: Run CLI

```bash
uv run scripts/release.py --json dates
```

If the CLI succeeds, use its output directly. If it fails, follow the manual steps below.

## Step 2 (fallback): Find active release issues

Invoke `rhdh-jira` with the `active_release` JQL from `references/jql-release.md`
and consume `JiraQueryResult/v1`.

## Step 3 (fallback): Extract dates from each release issue

For each release issue returned, ask `rhdh-jira` for the full issue including its
description, and consume `JiraQueryResult/v1`.

Extract from the description:

- Feature Freeze date
- Code Freeze date
- Doc Freeze date
- Go/No Go date
- GA Announce date

## Step 4 (fallback): Format output

Present as a table:

| Release | Feature Freeze | Code Freeze | Doc Freeze | Go/No Go | GA Announce | Source |
|---------|---------------|-------------|------------|----------|-------------|--------|
| {{VERSION}} | {{DATE}} | {{DATE}} | {{DATE}} | {{DATE}} | {{DATE}} | [{{ISSUE_KEY}}](https://issues.redhat.com/browse/{{ISSUE_KEY}}) |

</process>

<gotchas>

- Dates are embedded in the Jira issue description, not in custom fields — parse the description text.
- Some releases may have dates marked as TBD.
- Include the Jira issue link for traceability.

</gotchas>

<success_criteria>

- [ ] Table with one row per active release
- [ ] Each row has all five dates (or TBD) and a Jira source link

</success_criteria>
