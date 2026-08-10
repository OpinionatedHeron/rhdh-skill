---
name: setup-rhdh-skills
description: Install, configure, diagnose, or repair the complete RHDH skills environment.
disable-model-invocation: true
---

# Set Up RHDH Skills

Bootstrap the complete pack, then configure the capabilities needed by its model skills. This is a
human entry point because installation, credentials, and external mutations require human agency.

## Choose a setup branch

| Request | Load |
|---|---|
| Install, upgrade, or repair the complete skill collection | [references/install.md](references/install.md) |
| Configure Jira CLI, REST, or GraphQL access | [references/jira.md](references/jira.md) |
| Configure Google Workspace access for schedules and test plans | [references/google-workspace.md](references/google-workspace.md) |
| Configure the RHDH private-data checkout | [references/private-data.md](references/private-data.md) |
| Authenticate Atlassian MCP in Cursor | [references/atlassian-mcp.md](references/atlassian-mcp.md) |
| Discover or configure RHDH repositories | [references/repositories.md](references/repositories.md) |
| Configure containers and the local RHDH runtime | [references/local-runtime.md](references/local-runtime.md) |
| Authenticate the OpenShift CI Gangway adapter | [references/openshift-ci.md](references/openshift-ci.md) |
| Inspect or clean persisted cross-session artifacts | [references/artifacts.md](references/artifacts.md) |

With no branch in the request, show this table and wait for the user's selection.

## Preflight

Run the setup doctor before every branch:

```bash
python scripts/setup.py doctor --json
```

Consume the complete `SetupStatus/v1` response. Reuse it during the session unless setup changes.
The doctor reports capability status and configuration locations; it does not read credentials.

## Mutation contract

Before installation or configuration changes, present one complete `MutationPlan/v1`. Its `data`
contains `summary`, `operations`, and `materialHash`. Every operation contains ordered
`ownerSkill`, `adapter`, `operation`, `target`, `preview`, `preconditions`, `checks`, and `recovery`
fields. The hash binds the summary and complete operation array. Apply the plan only after the user
approves that hash. Re-plan and ask again when any bound material changes or when a new irreversible
action appears. Finish every applied plan with `MutationReceipt/v1`, carrying the approved `planId`
and `materialHash`. `SetupReceipt/v1` may additionally summarize the resulting capability status; it
never replaces the mutation receipt.

Credentials remain in the owning tool's credential store or OS keyring. Pass secrets directly to
the tool without placing them in conversation, configuration JSON, artifacts, or pack content.

Setup is complete when the doctor reports every promoted skill plus `grilling` and `humanizer`, and
the selected branch's smoke check succeeds. Tell the user to restart or rescan the agent after new
skills are installed.
