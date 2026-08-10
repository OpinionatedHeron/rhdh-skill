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
uv run scripts/setup.py doctor --json
```

Consume the complete `SetupStatus/v1` response. Reuse it during the session unless setup changes.
The doctor reports capability status and configuration locations; it does not read credentials.

## Mutation contract

Installation and configuration changes are mutations. Invoke the named skill `rhdh-artifacts` and
follow its `MutationPlan/v1` approval hash and `MutationReceipt/v1` protocol rather than restating
it here. Installation operations use `ownerSkill: setup-rhdh-skills` with the `skills-cli/v1` adapter;
`scripts/setup.py install-plan` builds the plan and `scripts/setup.py apply` executes it against the
hash the user approved. `SetupReceipt/v1` may additionally summarize the resulting capability
status; it never replaces the mutation receipt.

Credentials remain in the owning tool's credential store or OS keyring. Pass secrets directly to
the tool without placing them in conversation, configuration JSON, artifacts, or pack content.

## Completion

A branch is complete when the doctor reports every promoted skill in `assets/catalog.json` plus
`grilling` and `humanizer` as installed, the branch's own capability reads `true` in that same
`SetupStatus/v1`, and the branch reference's smoke check has been run with its output shown. An
install branch additionally requires one recorded outcome for every operation in the approved
`MutationPlan/v1`, and the user told to restart or rescan the agent. When a model skill sent the
user here with `SetupRequired/v1`, every capability in its `data.missing` must report installed
before the branch closes. Name any capability still `false` as unresolved instead of closing on it.
