# Workflow: Retrieve Active Release Status by Issue Type

Compile status of all active releases with open issue counts by type.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | Invoke `rhdh-jira`; require the needed capability in `JiraCapabilities/v1` |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
uv run scripts/release.py --json status {{RELEASE_VERSION}}
```

If the CLI succeeds, use its output directly. If it fails, follow the manual steps below.

## Step 2 (fallback): Find active releases

Invoke `rhdh-jira` with the `active_release` JQL from `references/jql-release.md`
and consume `JiraQueryResult/v1`.

Extract the release versions from the results (from `fixVersions` or issue summary).

## Step 3 (fallback): Count issues by type for each release

For each release version and each of Feature, Epic, Story, Task, Sub-task, Bug,
Vulnerability, and Weakness, invoke `rhdh-jira` with the `open_issues_by_type`
JQL from `references/jql-release.md`, substituting `{{RELEASE_VERSION}}` and
`{{ISSUE_TYPE}}`. Take each count from `JiraQueryResult/v1`.

## Step 4 (fallback): Get total open issue count

Invoke `rhdh-jira` with the `open_issues` JQL from `references/jql-release.md`
and take the total from `JiraQueryResult/v1`.

## Step 5 (fallback): Format output

For each release version, present a table:

### RHDH {{RELEASE_VERSION}}

| Issue Type | Count | Jira Link |
|-----------|-------|-----------|
| Feature | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Epic | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Story | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Task | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Sub-task | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Bug | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Vulnerability | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Weakness | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| **Total** | **{{TOTAL}}** | [View](https://issues.redhat.com/issues/?jql=...) |

Include Jira search links by URL-encoding the JQL.

</process>

<gotchas>

- Ask `rhdh-jira` for counts only — don't fetch full issue data just for counts.
- URL-encode the JQL when building Jira search links: `https://issues.redhat.com/issues/?jql=<URL_ENCODED_JQL>`.
- Optionally include scope changes using the `features_added_to_release` JQL from `references/jql-release.md` to flag recent additions (last 14 days).

</gotchas>

<success_criteria>

- [ ] One table per active release with counts for each issue type
- [ ] Total count per release with Jira search link
- [ ] All counts come from `JiraQueryResult/v1` (no full issue fetch)

</success_criteria>
