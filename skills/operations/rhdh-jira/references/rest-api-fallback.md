# Jira authenticated API fallback

Use this seam only when `acli` cannot read or update a required Jira field. This reference defines
payload semantics; it never owns credentials or raw HTTP authentication.

## Capability gate

1. Try the supported `acli` operation first. For broad reads, use paginated search; for a single
   issue, use `acli jira workitem view KEY --fields '*all' --json`.
2. Use REST only through an already-authenticated host Atlassian adapter. The adapter owns the site,
   credential store, request headers, retries, and secret redaction.
3. If that adapter is unavailable, emit `SetupRequired/v1` with route `atlassian-mcp` and
   `nextCommand: "/setup-rhdh-skills atlassian-mcp"`.

Do not create token files, shell `AUTH` variables, Authorization headers, or credential-bearing
request previews. Do not fall back from a native tool to raw `curl`.

## Supported semantic operations

| Operation | Request semantics | Expected result |
|---|---|---|
| Read all fields | Get issue by key with `fields=*all` | Issue object |
| Discover fields | List Jira fields | Field IDs, types, and names |
| Check editability | Get edit metadata for an issue | Allowed operations and values |
| Update fields | Partial issue update with a `fields` object | No-content success or updated issue |
| Add comment | Add an ADF comment, with visibility when required | Comment receipt |
| Add remote link | Attach a web link to an issue key with `{"object": {"url": ..., "title": ...}}` | Created link with an id, or the id of the link it replaced |

The host adapter may expose these as tools instead of URL paths. Select by semantic capability, not
by tool name, and keep transport-specific response metadata out of `JiraQueryResult/v1`.

## Remote links

A remote link is the "web link" shown on a Jira issue. It is the supported way to record an
external URL — a pull request, a design document, a support case — against an issue, and `acli`
has no equivalent, so the authenticated adapter owns it.

```json
{"object": {"url": "https://github.com/redhat-developer/rhdh/pull/1234", "title": "GitHub PR: Fix plugin loader"}}
```

The target is the issue key; `object.url` and `object.title` are the whole payload. A second link
carrying the same URL replaces the first rather than creating a duplicate, so re-running a plan
after a partial failure is safe. The receipt records the link id.

Callers reach this through the skill, not the adapter. `rhdh-pull-request` asks `rhdh-jira` for a
plan whose outcomes are a comment, a transition to `Review`, and a remote link to the PR URL; all
three are operations in one `MutationPlan/v1` under the boundary below.

## Custom-field payloads

These are payload fragments for an authenticated adapter. They are not standalone HTTP commands.

```json
{"fields": {"customfield_10028": 5}}
```

Story Points is numeric.

```json
{"fields": {"customfield_10795": {"value": "M"}}}
```

Size is a select value: `XS`, `S`, `M`, `L`, or `XL`.

```json
{"fields": {"customfield_10001": {"id": "TEAM_ID"}}}
```

Team uses an Atlassian team ID. Discover it from an existing issue through the authenticated
adapter; never guess it.

```json
{"fields": {"customfield_10785": {"value": "Enhancement"}}}
```

Release Note Type is a select value. Allowed values include `Feature`, `Enhancement`,
`Developer Preview`, `Deprecated Functionality`, `Removed Functionality`, and
`Release Note Not Required`.

## Mutation boundary

Every REST-backed write is still owned by `rhdh-jira`. Before execution:

1. Put the exact semantic operation, target issue, and redacted payload in `MutationPlan/v1`.
2. Set the operation adapter to the authenticated Atlassian adapter; never include headers or
   credentials in `preview`.
3. Obtain approval for the plan's material hash.
4. Execute only the approved payload.
5. Read the changed fields back and return the hash-matched `MutationReceipt/v1`.

## Response handling

| Result | Action |
|---|---|
| Validation failure | Re-read field metadata and correct the payload; re-plan if material changes |
| Unauthenticated | Emit `SetupRequired/v1`; do not inspect or repair credentials here |
| Forbidden | Report the missing permission; do not retry with another identity |
| Not found | Verify the issue key before retrying |
| Rate limited | Honor the adapter retry delay and retry once |

REST search is not a fallback for bulk JQL in this skill. Use `acli --paginate` or the authenticated
GraphQL adapter instead.
