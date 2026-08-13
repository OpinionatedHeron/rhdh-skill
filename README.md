# RHDH Skills

Composable Agent Skills for Red Hat Developer Hub engineering, operations, and
repository maintenance. The pack captures RHDH-specific repository knowledge,
version policy, delivery workflows, CI, release operations, and local testing
behind a small set of task-oriented interfaces.

## Install the complete pack

The complete setup is the 41 promoted RHDH skills plus two required external
skills. `--all` is the default and the recommended install. A single skill can be
installed on its own — bundled scripts are self-contained and there is no shared
runtime package — but skills reach each other by name, so anything a skill
invokes has to be present too.

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

Upgrading from the previous 24-skill layout? Re-running the install above
replaces the collection, retiring the skills that no longer exist along with it.
Restart the agent client afterwards so the discovery cache reflects the new set,
then invoke `/setup-rhdh-skills`. Existing `~/.config/rhdh-skill/config.json` and
`.rhdh/` state carry over untouched.

Nearly every skill was renamed, so an agent that somehow ends up with both sets
sees two candidates for the same request and may route to a retired copy. If you
suspect that — an old `rhdh-jira` answering when a `rhdh-jira-*` skill should —
list what is installed and remove the leftovers by name.

`/setup-rhdh-skills` itself removes nothing. It installs and verifies; it cannot
tell a stale copy of `overlay` from one you wrote and kept, so deleting anything
it did not install is yours to do.

- `/grilling` supplies the interview discipline required by skill authoring and
  Jira creation flows.
- `/humanizer` is required before PR-review prose is presented or posted.

After installation, invoke `/setup-rhdh-skills` once to discover repository
checkouts, verify tools and authentication, and preserve the existing RHDH CLI
state. Invoke `/ask-rhdh` whenever you want help choosing a flow.

The two entry skills are human-invoked. The other 39 skills are model-invoked
and can also be invoked explicitly.

## Skill catalog

`/ask-rhdh` is the catalog. Describe what you are doing and it names the skill to
use; it performs no work itself. The machine-readable roster lives in
`skills/meta/setup-rhdh-skills/assets/catalog.json`, which is the single source of
truth for membership — this file deliberately does not restate it.

Skills are grouped into six editorial folders. Folders are for readers of this
repository: they are stripped at install, and skills compose by name rather than
by path.

| Folder | Covers |
|---|---|
| `jira/` | Creating, refining, updating, and reporting on RHIDP, RHDHPLAN, RHDHBUGS, and RHDHSUPP work, plus sprint ceremonies and linking PRs to issues. |
| `plugins/` | Authoring, wiring, exporting, and fixing Backstage dynamic plugins; the overlays repository; local RHDH; opening and reviewing pull requests; midstream propagation. |
| `ci/` | Prow job configuration and nightly triggers, Konflux and Tekton task updates, base images, and Yarn bumps. |
| `release/` | Release status and readiness, milestone schedules, freeze announcements, teams, test-plan review, platform lifecycle, and the plugin CVE export. |
| `reference/` | The reusable layer other skills invoke by name: repository and version context, the forge read seam, the write gate, and the Jira and Backstage reference material. |
| `meta/` | The two human-invoked entry points, plus skill authoring and repository agent-readiness. |

Two skills are human-invoked and never selected automatically: `/ask-rhdh` and
`/setup-rhdh-skills`. Every other skill is model-invoked and can also be called
by name.

## How skills compose

A skill claims one trigger phrase, and invokes another skill by its stable name,
such as `/rhdh-context` or `/rhdh-jira-api`. Category paths are not part of the
interface. Handoffs happen in the conversation: there is no artifact envelope and
no artifact store. When context needs to survive into a later session, run
`/handoff`.

Every external write goes through the write gate. The skill states each operation
with its target, exact command, preview, and what happens on failure; you approve
that stated set; then it executes and reports the outcome of every operation,
including the ones it skipped. Read-only discovery and analysis need no approval.

`/rhdh-forge` reads GitHub and GitLab and constructs forge payloads, but never
executes a write — a caller that needs one gets a command, not an effect. That
separation is what keeps the gate enforceable.

Skills share prose through reference skills invoked by name, never by walking the
filesystem. They do not share runtime code: bundled scripts are self-contained, so
a single skill can be installed on its own.

See [ADR-0005](docs/adr/0005-one-skill-per-trigger-phrase.md),
[ADR-0006](docs/adr/0006-duplication-by-layer.md),
[ADR-0007](docs/adr/0007-write-gate.md), and
[ADR-0008](docs/adr/0008-skill-naming-and-namespace-isolation.md).

## CLI and state compatibility

The architecture changes skill names and composition, not the established CLI
or state formats:

- `rhdh` and `rhdh-local` command behavior remains compatible.
- Repository configuration remains at `~/.config/rhdh-skill/config.json`.
- Worklog and todo state remains under `.rhdh/`.
- Cross-session handoff is not a pack feature; run `/handoff` when you need it.

The skill rename is delivered as one breaking cutover. No aliases ship, and the
old skill directories are dropped from this repository; re-running the install
retires them from your environment too. Existing CLI configuration and local
state are reused.

## Development

```bash
uv sync --extra dev
git config core.hooksPath .githooks
uv run pytest
```

Tests protect scripts, adapters, and catalog contracts. They do not pin
incidental prose shape. See [CONTRIBUTING.md](CONTRIBUTING.md).

Versions are published exclusively as git tags. Changes to skill behavior or
scripts require the appropriate patch, minor, or major tag after merge.

## License

Apache-2.0 — see [LICENSE](LICENSE).
