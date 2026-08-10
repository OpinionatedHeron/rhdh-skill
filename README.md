# RHDH Skills

Composable Agent Skills for Red Hat Developer Hub engineering, operations, and
repository maintenance. The pack captures RHDH-specific repository knowledge,
version policy, delivery workflows, CI, release operations, and local testing
behind a small set of task-oriented interfaces.

## Install the complete pack

The complete setup is the 18 promoted RHDH skills plus two required external
skills. `--all` is the only supported way to install this repository: the skills
reach each other by name, so a hand-picked subset is not a working pack.

```bash
npx skills@latest add redhat-developer/rhdh-skill --all -g -y
npx skills@latest add mattpocock/skills --skill grilling -g -y
npx skills@latest add blader/humanizer -g -y
```

To bootstrap through the setup router instead, install that entry skill on its
own, restart the agent client so it is discovered, and invoke
`/setup-rhdh-skills install`:

```bash
npx skills@latest add redhat-developer/rhdh-skill --skill setup-rhdh-skills -g -y
```

The setup router then installs the complete pack (or its catalog-listed direct
sources) and tells you when another client restart is required. That single
skill is a bootstrap step, not a supported end state.

Upgrading from the previous 24-skill layout? Installing the new pack does not
remove the old directories. See
[the architecture migration reference](docs/architecture-migration.md#upgrading-an-existing-installation).

- `/grilling` supplies the interview discipline required by skill authoring and
  Jira creation flows.
- `/humanizer` is required before PR-review prose is presented or posted.

After installation, invoke `/setup-rhdh-skills` once to discover repository
checkouts, verify tools and authentication, and preserve the existing RHDH CLI
state. Invoke `/ask-rhdh` whenever you want help choosing a flow.

The two entry skills are human-invoked. The other 16 skills are model-invoked
and can also be invoked explicitly.

## Skill catalog

Folders are editorial categories for readers. Skills compose by name, never by
walking category-relative paths.

### Engineering

Human-invoked:

- [`ask-rhdh`](skills/engineering/ask-rhdh/SKILL.md) — choose the RHDH skill or
  flow that fits the request; performs no work itself.
- [`setup-rhdh-skills`](skills/engineering/setup-rhdh-skills/SKILL.md) — set up
  repository paths, tools, authentication, and shared state.

Model-invoked:

- [`rhdh-context`](skills/engineering/rhdh-context/SKILL.md) — repository map,
  version compatibility, workspace lookup, and general RHDH ecosystem context.
- [`rhdh-artifacts`](skills/engineering/rhdh-artifacts/SKILL.md) — the artifact
  envelope, mutation plan and receipt protocol, setup handoffs, and credential
  redaction shared by every skill.
- [`rhdh-forge`](skills/engineering/rhdh-forge/SKILL.md) — read GitHub issues,
  pull requests, checks, and files on behalf of the other skills.
- [`rhdh-plugin-development`](skills/engineering/rhdh-plugin-development/SKILL.md)
  — create and change plugins, upgrade Backstage, migrate to NFS, and place
  tests.
- [`rhdh-overlay`](skills/engineering/rhdh-overlay/SKILL.md) — onboard and
  update Workspaces, fix Overlay builds, triage PRs, and manage publish
  triggers.
- [`rhdh-local`](skills/engineering/rhdh-local/SKILL.md) — run RHDH locally and
  enable, disable, test, troubleshoot, back up, and restore plugins.
- [`rhdh-pull-request`](skills/engineering/rhdh-pull-request/SKILL.md) — take a
  plugin bug or prepared change through verification and PR creation.
- [`rhdh-pr-review`](skills/engineering/rhdh-pr-review/SKILL.md) — analyze and
  post PR reviews, including live cluster testing for operator changes.

### Operations

- [`rhdh-jira`](skills/operations/rhdh-jira/SKILL.md) — create, refine, assign,
  plan, report, and update work in the RHDH Jira projects.
- [`rhdh-platform-support`](skills/operations/rhdh-platform-support/SKILL.md) —
  answer platform and product lifecycle/support questions.
- [`rhdh-test-plan`](skills/operations/rhdh-test-plan/SKILL.md) — review an RHDH
  release test plan against lifecycle and milestone evidence.
- [`rhdh-release`](skills/operations/rhdh-release/SKILL.md) — release dates,
  status, freeze communication, blocker and CVE reporting, notes, and release
  data.
- [`rhdh-ci`](skills/operations/rhdh-ci/SKILL.md) — manage Prow and Konflux
  configuration and trigger nightly jobs.
- [`rhdh-base-images`](skills/operations/rhdh-base-images/SKILL.md) — update and
  analyze base images, RPM lockfiles, and related runtime pins.

### Maintainers

- [`rhdh-agent-readiness`](skills/maintainers/rhdh-agent-readiness/SKILL.md) —
  assess and improve one repository or the RHDH repository set for coding
  agents.
- [`skill-authoring`](skills/maintainers/skill-authoring/SKILL.md) — create,
  audit, and consolidate Agent Skills.

Draft and retired material belongs outside the promoted discovery root, under
`internal/in-progress/` and `internal/deprecated/`. Neither ships with the pack.

## How skills compose

A skill invokes another skill by its stable name, such as `/rhdh-context` or
`/rhdh-jira`. Category paths are not part of the interface.

When a flow crosses a real seam, the producing skill writes a versioned artifact
to the operating system temporary directory, namespaced by project root. Each
artifact carries `contract` (for example, `ChangeHandoff/v1`), `id`, `createdAt`,
and contract-specific `data`. Consumers validate the contract before use. No
artifact is written into a checkout, so none can reach a commit; the price is
that a cross-session artifact expires when the operating system purges temporary
files, which the store reports along with the skill to re-run.

Every external mutation is represented by a `MutationPlan`. The plan names the
operation, target, preview, checks, and recovery information. A user approves
the plan before the selected adapter executes it; the result is captured as a
mutation receipt. Read-only discovery and analysis do not require mutation
approval.

Skills share prose through foundation skills invoked by name, and share runtime
code through one versioned package, `rhdh_common`, in `packages/rhdh-common/`.
Neither is reached by walking the filesystem.

See [the architecture migration and catalog reference](docs/architecture-migration.md),
[ADR-0005](docs/adr/0005-composable-skill-distribution.md), and
[ADR-0006](docs/adr/0006-foundation-skills.md) for the complete contracts.

## CLI and state compatibility

The architecture changes skill names and composition, not the established CLI
or state formats:

- `rhdh` and `rhdh-local` command behavior remains compatible.
- Repository configuration remains at `~/.config/rhdh-skill/config.json`.
- Worklog and todo state remains under `.rhdh/`.
- New cross-skill artifacts live in the operating system temporary directory.

The skill rename is delivered as one breaking cutover. No aliases ship, and the
old skill directories are dropped from this repository — but an installation
that already has them keeps them until you remove them yourself, as described in
[the migration reference](docs/architecture-migration.md#upgrading-an-existing-installation).
Existing CLI configuration and local state are reused.

## Development

```bash
uv sync --extra dev
git config core.hooksPath .githooks
uv run pytest
```

Tests protect scripts, structured artifacts, adapters, and catalog contracts.
They do not pin incidental prose shape. See [CONTRIBUTING.md](CONTRIBUTING.md).

Versions are published exclusively as git tags. Changes to skill behavior or
scripts require the appropriate patch, minor, or major tag after merge.

## License

Apache-2.0 — see [LICENSE](LICENSE).
