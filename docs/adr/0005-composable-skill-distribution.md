# Composable skill distribution

**Status:** Accepted.

**Amended by [ADR-0006](0006-foundation-skills.md)**: artifacts persist under
the operating system temporary directory rather than `.rhdh/artifacts/`; the
complete pack is the only supported install, retiring selective installation;
and skills may depend on one versioned shared package, `rhdh_common`. The rest
of this decision stands as recorded below.

## Context

The repository grew to 24 top-level skills plus a broad model-invoked `rhdh`
orchestrator. Callers had overlapping descriptions, duplicated route maps, and
cross-skill file references. Promoted and non-promoted material also need an
unambiguous distribution seam for recursively discovering Agent Skills clients.

## Decision

Ship one promoted catalog of 16 skills in three editorial categories:

- `skills/engineering/`
- `skills/operations/`
- `skills/maintainers/`

Only `/ask-rhdh` and `/setup-rhdh-skills` are human-invoked. The remaining 14
skills are model-invoked. Every skill carries native harness metadata, and
catalog validation enforces invocation parity.

The machine-readable catalog owned by `/setup-rhdh-skills` is the source of
truth for promoted membership, invocation mode, named dependencies, artifact
contracts, and complete-pack sources. Human documentation summarizes that
catalog and must not define a competing inventory.

Category folders are not composition paths. Skills invoke each other by stable
name and communicate across real seams with typed, versioned artifacts under
`.rhdh/artifacts/`. The `.rhdh/` directory remains local, gitignored state.
Each artifact uses the envelope `contract`, `id`, `createdAt`, and `data`; the
contract version is part of `contract`. Contract-specific required fields live
under `data`. A consumer validates the declared contract before using it.

Human-invoked skills are entry points for people and are never invoked by model
skills. Model-invoked skills may compose only other model-invoked skills, by
stable name and artifact contract. They never discover a sibling through a
filesystem path, import its implementation, or read its private references.

Setup preserves the existing `rhdh` and `rhdh-local` CLI behavior,
`~/.config/rhdh-skill/config.json`, worklog, and todo locations. Setup state is
the precondition for workflows that need configured repositories, tools, or
authentication.
`/setup-rhdh-skills` is the exclusive human setup router. Domain skills may
detect missing capability, but must return `SetupRequired/v1` with an exact
setup command instead of installing, authenticating, or probing host skill
directories themselves.

Credentials stay inside an authenticated adapter backed by the owning CLI's
native store or a host connector. Only that adapter may retrieve a transient
credential, construct request authentication, and redact errors. Its public
arguments, output, logs, plans, and artifacts are credential-free. Workflow
instructions and non-adapter scripts use non-secret capability checks; setup
owns login and never creates token files or a parallel credential store.

Mutating workflows emit a `MutationPlan/v1` before execution. Every operation
records `order`, `ownerSkill`, `adapter`, `operation`, `target`, `preview`,
`preconditions`, `checks`, and `recovery`. The plan's SHA-256 `materialHash`
binds the canonical JSON of all plan data except the hash itself. A user
approves that exact hash before an adapter executes; `MutationReceipt/v1`
records the plan ID, the same hash, and exactly one ordered outcome for every
planned operation. Each outcome repeats the operation identity and records
`completed`, `failed`, or `skipped`; missing, extra, or reordered outcomes are
invalid. Read-only workflows do not require this gate. Setup mutations follow
the same rule: `SetupReceipt/v1` may additionally summarize resulting
capabilities, but every applied setup plan still produces its hash-matched
`MutationReceipt/v1`.

External variation stays behind adapters. Current real seams include issue
sources, forges, container runtimes, lifecycle sources, CI systems, and release
data sources. Shared scripts expose contract-oriented structured output; prose
does not duplicate their implementation.

The complete functional distribution includes external `/grilling` and
`/humanizer` skills. They remain independently maintained sources of truth.
The setup skill installs either the hosted skills.sh pack recorded in the
catalog or the catalog's direct repository sources. The direct sources are the
required fallback until a pack is created after merge and the catalog records
its public URL.

Draft and retired skills live outside the discovery root under
`internal/in-progress/` and `internal/deprecated/`. Recursive installers and
promoted manifests therefore expose the same set.

Git tags are the authoritative skill versions. The Python wheel retains
`0.0.0` as an unversioned compatibility sentinel, and `rhdh --version` reads
that installed package metadata rather than advertising a second hard-coded
release. The 24-to-16 rename and consolidation ships as one major breaking
cutover with no compatibility aliases or mixed catalog period.

## Consequences

- Common callers select one task-oriented model skill with less description
  competition.
- Skill and artifact interfaces survive editorial category moves.
- Consumers must validate versioned artifact contracts before use.
- Setup and distribution validation become load-bearing contracts.
- Selective installation is supported only when its dependencies and shared
  setup/runtime contracts are also present; the complete pack is the default.
- Tests protect scripts, adapters, artifacts, catalog membership, invocation,
  and distribution. Incidental prose shape is deliberately untested.

This decision supersedes [ADR-0003](0003-orchestrator-plus-sub-skills.md). It
preserves ADR-0001's agent-assisted workflows, ADR-0002's portability rule, and
ADR-0004's Agent Skills format.
