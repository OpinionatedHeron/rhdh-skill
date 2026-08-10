# Issue context

Resolve a GitHub issue reference, fetch its detail, and locate the workspace it
belongs to. `scripts/fetch_issue_context.py` performs all of this and emits
`IssueContext/v1`; the rules below are the same logic for a caller that needs to
parse without a network call, or that needs to explain a result.

## Parse a reference

Accept any of these and normalize to a repository plus number:

| Input | Example | Extraction |
|---|---|---|
| Full URL | `https://github.com/redhat-developer/rhdh-plugins/issues/607` | Owner, repository, and number from the path |
| URL without scheme | `github.com/backstage/community-plugins/issues/3574` | Same, prepending `https://` |
| URL with fragment or query | `.../issues/607#issuecomment-123` | Strip fragment and query, then extract |
| Shorthand | `redhat-developer/rhdh-plugins#607` | Split on `#` |
| Bare number in a checkout | `#123` | Resolve the repository from `git remote -v` |

1. If the input contains `github.com/`, read `/<owner>/<repo>/issues/<number>`
   from the path.
2. If the input matches `<owner>/<repo>#<number>`, split it directly.
3. If the input matches `#\d+` or a bare number, resolve the repository from the
   current checkout.
4. If none match, the input is not a GitHub issue. Hand it back so the caller
   can try its Jira parser.

Construct the canonical URL from the resolved owner, repository, and number.
Never store the raw input as the URL.

### Repository profile

| Reference contains | Profile |
|---|---|
| `rhdh-plugins`, but not `community-plugins` | rhdh-plugins |
| `community-plugins` | community-plugins |
| Neither, or a bare number | Detect from `git remote -v` |

## Fetch the issue

```bash
gh issue view <number> --repo <owner/repo> --json number,title,body,labels,state,url,comments
```

| Field | JSON path |
|---|---|
| `data.summary` | `.title` |
| `data.description` | `.body` |
| `data.labels` | `.labels[].name` |
| `data.state` | `.state` (`OPEN` or `CLOSED`) |
| `data.comments` | `.comments[] | {author, body, createdAt}` |

## Resolve the workspace

Both `rhdh-plugins` and `community-plugins` organize code under
`workspaces/<name>/`. Apply these strategies in order and record which one
answered, because a caller that knows the strategy can judge the confidence:

1. **Label** — a label of the form `workspace/<name>` (for example
   `workspace/rbac`, `workspace/report-portal`). Take the part after the slash.
2. **Body field** — a `### Workspace` heading followed by the name. The
   community-plugins bug template emits this.
3. **Title prefix** — titles often read `plugin-<name>: description` or
   `<workspace>: description`. Take the prefix before the first colon and drop a
   leading `plugin-`.
4. **Package name** — scan the body for
   `@red-hat-developer-hub/backstage-plugin-<name>` or
   `@backstage-community/plugin-<name>` and derive the workspace from it.
5. **Unresolved** — report `null` and ask the user which workspace to target.

A Jira issue carries no workspace label. Map its Component to a workspace
directory instead; `/rhdh-plugin-development` owns that table.

## Interaction payloads

These are payloads, not authorization. Before any of them runs, the calling
skill puts the exact command, repository, issue number, and body or label into
`MutationPlan/v1`, obtains approval of the plan's material hash, and returns
`MutationReceipt/v1` afterwards. `/rhdh-artifacts` owns both shapes. This skill
executes none of these commands.

```bash
gh issue comment <number> --repo <owner/repo> --body "<exact body>"
gh issue edit <number> --repo <owner/repo> --add-label "<label>"
gh issue edit <number> --repo <owner/repo> --remove-label "<label>"
```

## Errors

| Scenario | Action |
|---|---|
| `gh` not authenticated | Stop at the readiness check and report that `gh auth login` is required |
| Issue not found (404) | Report `Issue #<n> not found in <repo>` and ask the user to confirm the number and repository |
| No write access | A label or comment write fails; report it and let the caller continue the read-only work |
| Issue already closed | Report the state and ask whether to proceed |
| Repository undetectable for a bare number | Ask for the repository rather than guessing from a similarly named remote |
