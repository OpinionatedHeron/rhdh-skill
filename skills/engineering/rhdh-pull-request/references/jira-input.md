# Jira input and handoff

Resolve Jira input locally, then compose with `/rhdh-jira` through artifacts.
This skill does not authenticate to Jira or select among `acli`, REST, GraphQL,
or MCP.

## Parse a Jira reference

Accept these formats and normalize them to a key and browse URL:

| Input | Example | Extraction |
|---|---|---|
| Bare key | `RHDHBUGS-1934` | Match directly |
| Browse URL | `https://redhat.atlassian.net/browse/RHDHBUGS-1934` | Take the segment after `/browse/` |
| URL without scheme | `redhat.atlassian.net/browse/RHIDP-15252` | Take the segment after `/browse/` |
| URL with query or fragment | `https://redhat.atlassian.net/browse/RHIDP-15252?focusedId=123` | Strip query and fragment |

1. If the input contains `atlassian.net/browse/`, extract the next path
   segment.
2. Otherwise, scan for
   `(RHIDP|RHDHBUGS|RHDHPLAN|RHDHSUPP)-\d+`.
3. Reject input that matches neither form.
4. Construct the canonical browse URL from the normalized key; do not retain a
   query string or fragment.

## Read handoff

When the caller did not provide Jira context, invoke `/rhdh-jira` with the key
and consume this envelope:

```yaml
contract: IssueContext/v1
id: jira-issue-context-id
createdAt: ISO-8601
data:
  key: ISSUE-123
  summary: Issue summary
  source: jira
  url: https://redhat.atlassian.net/browse/RHDHBUGS-1934
```

If the named skill cannot provide the artifact, retain the key and URL, leave
the summary unresolved, and return `SetupRequired/v1` for the Jira enrichment
branch. Never inspect a credential file as a fallback.

## Write handoff after PR publication

After the PR URL exists, ask `/rhdh-jira` to plan the desired comment,
transition, and remote-link outcomes. Consume its `MutationPlan/v1`, surface
the complete plan and exact material hash for approval, then consume its
`MutationReceipt/v1`. The Jira skill owns capability detection, adapter choice,
execution, and verification.

Failure to update Jira does not invalidate a successfully created PR. Preserve
the `PullRequestReceipt/v1`, attach the setup requirement or failed Jira
receipt, and report the desired Jira outcomes for retry.
