# Jira bulk-read adapter

Use `acli` for bulk reads unless the agent host exposes an already-authenticated Atlassian
GraphQL capability. This reference owns query semantics, not credentials or HTTP transport.

## Capability gate

1. Read `JiraCapabilities/v1` from the `rhdh-jira` entry check.
2. If `acli` is ready, prefer its paginated JSON search:

   ```bash
   acli jira workitem search --jql "<JQL>" --paginate \
     --fields "key,summary,status,issuetype,priority,assignee,parent,labels,fixVersions" --json
   ```

3. Use GraphQL only when the host exposes a ready authenticated Atlassian adapter and the branch
   needs relationship or custom-field data that `acli` cannot return efficiently.
4. If neither adapter satisfies the branch, emit `SetupRequired/v1` with route `atlassian-mcp` and
   `nextCommand: "/setup-rhdh-skills atlassian-mcp"`.

Never create an `AUTH` variable, read a token file, build an Authorization header, or invoke a raw
HTTP client with credentials. Authentication stays inside the native CLI or host connector.

## Query contract

The adapter accepts a GraphQL document plus variables and returns response data without exposing
request headers or credentials. Keep GraphQL read-only; all writes follow the `MutationPlan/v1`
contract and use the supported `acli` or authenticated host operation.

### Schema discovery

Use targeted introspection through the adapter when a field or type is unknown:

```graphql
query IntrospectType($name: String!) {
  __type(name: $name) {
    name
    fields {
      name
      type { name kind ofType { name kind } }
    }
  }
}
```

Do not load a full schema dump into model context. If offline inspection is necessary, save the
adapter response to a temporary file and query only the relevant type names programmatically.

### Search issues

```graphql
query SearchIssues($cloudId: ID!, $jql: String!, $first: Int!, $after: String) {
  jira {
    issueSearchStable(cloudId: $cloudId, jql: $jql, first: $first, after: $after) {
      edges {
        node {
          key
          summary
          status { name }
          issueType { name }
          priority { name }
          assignee { name accountId }
          parentIssue { key summary }
          storyPoints
          labels
          fixVersions { name }
        }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
```

Paginate until `hasNextPage` is false. Store only normalized issue data in `JiraQueryResult/v1`;
never store raw connector metadata.

### Single issue

```graphql
query GetIssue($cloudId: ID!, $key: String!) {
  jira {
    issueByKey(cloudId: $cloudId, key: $key) {
      key
      summary
      status { name }
      issueType { name }
      priority { name }
      assignee { name accountId }
      parentIssue { key summary }
      storyPoints
      labels
      fixVersions { name }
      fields { edges { node { __typename } } }
    }
  }
}
```

## Fallback rules

| Need | Adapter |
|---|---|
| Normal or bulk JQL search | `acli jira workitem search --paginate --json` |
| Single issue with custom fields | `acli jira workitem view KEY --fields '*all' --json` |
| Relationship-heavy bulk read | Authenticated host GraphQL adapter |
| Unsupported custom-field read or write | [rest-api-fallback.md](rest-api-fallback.md) |
| No capable authenticated adapter | `SetupRequired/v1` |

`issueSearchStable` is an evolving API. When it fails, fall back to paginated `acli`, not raw REST
search. Enrich and normalize results with `scripts/parse_issues.py` before claiming a field is
missing.
