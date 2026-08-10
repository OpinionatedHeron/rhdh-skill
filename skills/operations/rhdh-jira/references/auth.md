# Jira capability check

This reference detects capability; it does not create credentials. Human-facing
credential setup is owned by the user-invoked skill `/setup-rhdh-skills`.

## Check

Run the local detector without reading credential contents into context:

```bash
python scripts/setup.py --json
```

Use its boolean capability fields. A normal Jira smoke check is
`acli jira project list --recent 1`; `acli auth status` can report a false negative
for API-token authentication.

## API preference

1. Use `acli` for ordinary and bulk reads and supported mutations.
2. Use an authenticated host Atlassian adapter for relationship-heavy GraphQL reads.
3. Use that same host-managed boundary for fields or writes unsupported by `acli`.

Never read, print, copy, transform, or repair credential material in model context.

## Missing capability

If required Jira capability is absent, stop the affected branch and emit
`SetupRequired/v1`:

```json
{
  "contract": "SetupRequired/v1",
  "id": "jira-setup-required",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "ownerSkill": "setup-rhdh-skills",
    "route": "jira",
    "reason": "Jira authentication or API capability is unavailable",
    "missing": ["acli|jira-auth|rest|graphql"],
    "nextCommand": "/setup-rhdh-skills jira"
  }
}
```

Tell the human to run `/setup-rhdh-skills jira`. Do not duplicate its credential
creation, storage, login, or repair instructions here. After setup completes,
rerun `scripts/setup.py --json` and resume only when the required capability passes.

## Non-auth errors

| Symptom | Interpretation |
|---|---|
| `acli auth status` says unauthorized but the smoke check succeeds | Ignore the false negative |
| Host REST/GraphQL adapter is unavailable | Emit `SetupRequired/v1` for route `atlassian-mcp` |
| Required authenticated capability is absent | Emit `SetupRequired/v1` for route `jira` or `atlassian-mcp` |
| 429 response | Wait briefly and retry once; this is not a setup failure |
