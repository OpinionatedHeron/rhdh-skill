# Workflow: Retrieve List of CVEs

Compile all CVE issues for a release.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | Invoke `rhdh-jira`; require the needed capability in `JiraCapabilities/v1` |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
uv run scripts/release.py --json cves {{RELEASE_VERSION}}
```

If the CLI succeeds, use its output directly. If it fails, follow the manual steps below.

## Step 2 (fallback): Query CVE issues

Invoke `rhdh-jira` with the `cves` JQL from `references/jql-release.md`.
Consume enriched `JiraQueryResult/v1` fields for key, summary, type, status,
priority, and assignee.

## Step 3 (fallback): Get count

Take the count from the same `JiraQueryResult/v1`. Check `truncated` before
reporting it as a total.

## Step 4 (fallback): Format output

Present full details for each CVE:

| Key | Summary | Type | Status | Priority | Assignee |
|-----|---------|------|--------|----------|----------|
| [{{KEY}}](https://issues.redhat.com/browse/{{KEY}}) | {{SUMMARY}} | {{TYPE}} | {{STATUS}} | {{PRIORITY}} | {{ASSIGNEE}} |

**Total:** {{COUNT}} CVEs — [View in Jira](https://issues.redhat.com/issues/?jql=...)

</process>

<gotchas>

- CVEs are critical for security tracking — after Code Freeze, only critical severity CVEs are considered for inclusion before GA.
- If no release version is specified, ask the user.

</gotchas>

<success_criteria>

- [ ] Each CVE listed with key, summary, severity, and status
- [ ] Total count with Jira search link

</success_criteria>
