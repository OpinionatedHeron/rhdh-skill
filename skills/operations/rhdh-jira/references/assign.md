# Recommend and assign Jira work

Recommend assignees from team membership, recent expertise, current capacity, and context proximity.
Accept one or more issue keys, a JQL query, and an optional Jira team ID.

## Choose a mode

- **Deep**: authenticated team roster plus recent work and sprint capacity. Default when the needed
  host and CLI capabilities are ready.
- **Quick**: use only issue and assignee evidence already in context. If evidence is insufficient,
  say so instead of guessing.

## Capability boundary

Use paginated `acli` for issue reads. Team roster may use the authenticated host GraphQL adapter in
`graphql-queries.md`. If it is unavailable, emit `SetupRequired/v1` for route `atlassian-mcp` or ask
whether to continue in quick mode. Never construct credentials or raw HTTP requests.

## Deep analysis

1. Fetch the team roster through the host adapter with the `GetTeamRoster` query in
   `graphql-queries.md` → Team roster. Keep members whose `state` is `FULL_MEMBER`; drop `INVITED`
   and `ALUMNI`. Capture display name and account ID; paginate past 50 members.
2. For each member, fetch up to 90 days of recent work:

   ```bash
   acli jira workitem search \
     --jql "project in (RHIDP, RHDHPLAN, RHDHSUPP, RHDHBUGS) AND assignee = ACCOUNT_ID AND updated >= -90d ORDER BY updated DESC" \
     --fields "key,summary,status,issuetype,components" --limit 50 --json
   ```

3. Build an expertise profile: top components, issue-type counts, recurring domain phrases, and the
   percentage of work in the leading component.
4. Fetch active and future sprint load:

   ```bash
   acli jira workitem search \
     --jql "project in (RHIDP, RHDHPLAN, RHDHSUPP, RHDHBUGS) AND assignee = ACCOUNT_ID AND sprint in (openSprints(), futureSprints()) AND status != Closed" \
     --fields "key,summary,status,storypoints,sprint,parent,components" --paginate --json
   ```

5. Mark a member overloaded at 10 open issues or 21 committed story points.
6. Score context proximity: +3 per shared component, +1 per shared meaningful phrase, and +5 for a
   shared parent.

Use `score = expertise_match * 3 + proximity * 2 - open_issue_count`. Add a 10-point penalty for an
overloaded member. For Blocker or Critical work, choose the strongest domain expert and disclose the
capacity risk. Otherwise exclude overloaded members. Include a runner-up when scores are within 20%.

Also flag:

- one person owning more than 60% of a component's recent work;
- the same person being recommended for four or more issues in the batch;
- a low-priority issue that could safely broaden another member's experience.

## Recommendation output

Return issue key, summary, priority, proposed account ID and display name, score, short evidence,
runner-up, capacity, and warnings. Do not imply certainty when component or sprint metadata is absent.

## Apply assignments

Assignment is a mutation. Build one `MutationPlan/v1` containing each issue-to-account mapping and
the exact `acli` command, then obtain approval for its material hash.

```bash
acli jira workitem assign --key RHIDP-1234 --assignee "ACCOUNT_ID" --yes
```

`assign` takes `--key`, not a positional issue key, and hangs on an interactive prompt without
`--yes`. `acli-commands.md` → Key Syntax Rules covers both, plus the flag differences between
`assign`, `edit`, and `transition`. There is no GraphQL mutation for assignment; `acli` and the
authenticated adapter are the only two paths.

For a batch, use the supported `--from-file` form and include the complete redacted file content in
the plan preview. If `acli` cannot perform a required assignment, use the authenticated host adapter
from `rest-api-fallback.md`; do not fall back to raw HTTP. Verify each assignee after execution and
return the hash-matched `MutationReceipt/v1` with successes, skips, and permission failures.

## Failure handling

| Failure | Action |
|---|---|
| Team ID is unknown | Ask for it; do not infer a team from names |
| Member has no recent work | Keep the member but mark expertise unknown |
| Rate limit | Honor the adapter delay and retry once |
| All members are overloaded | Recommend the least-loaded qualified member with a warning |
| Issue has no useful metadata | Score only available evidence and label confidence low |
