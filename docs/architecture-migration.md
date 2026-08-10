# Architecture migration and skill catalog

This reference maps the former 24-skill layout to the promoted 16-skill pack and
records the compatibility rules for the breaking cutover.

## Entry points

- Invoke `/setup-rhdh-skills` once after installation or when repository paths,
  tools, or authentication change.
- Invoke `/ask-rhdh` when you want a recommendation. It performs no work.
- Describe a concrete task normally to trigger one of the 14 model-invoked
  skills.

## Migration map

| Former skill or outcome | New owner |
|---|---|
| `agent-ready` | `/rhdh-agent-readiness` |
| `backstage-upgrade` | `/rhdh-plugin-development` |
| `base-images-and-rpms` | `/rhdh-base-images` |
| `bug-fix` | `/rhdh-pull-request` |
| `compute-plugin-package-overlay-cve-list` | `/rhdh-release` |
| `create-plugin` | `/rhdh-plugin-development` |
| `cursor-mcp-auth` | `/setup-rhdh-skills` auth route |
| `konflux-release-data-rpa` | `/rhdh-release` |
| `konflux-tekton-updates` | `/rhdh-ci` |
| `lifecycle` | `/rhdh-platform-support` |
| `nfs-migration` | `/rhdh-plugin-development` |
| `overlay` | `/rhdh-overlay` |
| `prow` | `/rhdh-ci` |
| `prow-trigger-nightly` | `/rhdh-ci` |
| `raise-pr` | `/rhdh-pull-request` |
| `rhdh` catalog/intake | `/ask-rhdh` |
| `rhdh` doctor/config/auth | `/setup-rhdh-skills` |
| `rhdh` repository/version/workspace context | `/rhdh-context` |
| `rhdh` worklog/todo behavior | compatible CLI/state implementation behind the setup and mutation contracts |
| `rhdh-coding` | `/rhdh-plugin-development` |
| `rhdh-jira` | `/rhdh-jira` |
| `rhdh-local` | `/rhdh-local` |
| `rhdh-pr-review` | `/rhdh-pr-review` |
| `rhdh-release` | `/rhdh-release` |
| `rhdh-test-plan-review` | `/rhdh-test-plan` |
| `skill-maker` | `/skill-authoring` |
| `test-placement` | `/rhdh-plugin-development` |

The old names are removed in one major release. No redirect skills or aliases
ship with the new catalog.

## Composition contract

Skills compose by stable name. A caller may invoke `/rhdh-context`; it must not
open `../engineering/rhdh-context/references/...` directly. This keeps category
moves editorial.

Cross-skill data is a typed artifact under `.rhdh/artifacts/` with:

- `contract`, including its version (for example `RhdhContext/v1`)
- `id`
- `createdAt`
- contract-specific `data`

Consumers reject unsupported contracts with a clear migration message.
Common artifacts cover setup state, issue context, change handoff, evidence,
mutation plans and receipts, lifecycle snapshots, release snapshots, and CI
requests/results.

## Mutation approval

A mutating flow first emits `MutationPlan/v1`. Every ordered operation names its
owner skill, adapter, operation, exact target, preview, preconditions, checks,
and recovery. The plan hash binds the canonical JSON of all plan data except the
hash itself. The user must approve that exact hash before execution. The
adapter records success or failure in `MutationReceipt/v1` with the same plan
ID and hash. Its outcomes preserve plan order and repeat each operation's
identity and `completed`, `failed`, or `skipped` status; the receipt is invalid
if an operation is missing, extra, or reordered. `SetupReceipt/v1` may
additionally summarize the resulting setup state, but never replaces that
receipt. Read-only inspection bypasses this gate.

Credentials remain inside authenticated adapters backed by native CLI stores
or host connectors. Workflow instructions and non-adapter scripts use
credential-free interfaces and return `SetupRequired/v1` when a capability is
unavailable. Only the adapter retrieves a transient credential and authenticates
the request; setup owns login and never creates a parallel credential store.

## Distribution

The promoted discovery root contains only:

- `skills/engineering/`
- `skills/operations/`
- `skills/maintainers/`

Draft and retired skills live under `internal/` so recursive installers do not
discover them. Distribution validation compares the promoted catalog, skill
directories, manifests, invocation metadata, and documentation.

The complete functional pack includes the external `/grilling` and
`/humanizer` skills. They remain external sources of truth rather than copied
references.

## Compatibility

The cutover preserves the `rhdh` and `rhdh-local` CLI behavior,
`~/.config/rhdh-skill/config.json`, and existing worklog/todo state. The
`.rhdh/` ignore rule also covers new artifacts.

Git tags are authoritative for both skill and artifact producer versions. The
cutover is published once under the next major tag.
