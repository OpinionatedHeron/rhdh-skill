# Contributing

This guide explains how to change the promoted skill pack without widening its
interfaces or breaking distribution.

## Set up the repository

```bash
uv sync --extra dev
git config core.hooksPath .githooks
uv run pytest
```

For end-to-end skill use, install the complete pack documented in
[README.md](README.md), including `/grilling` and `/humanizer`.

## Choose the owning module

Before editing, identify the one skill that owns the behavior. Category folders
are editorial:

- `skills/engineering/`
- `skills/operations/`
- `skills/maintainers/`

A category move must not change how callers invoke a skill. Compose with a
stable `/skill-name`; never reference another category's internal file.

Split a new skill only when it has independent invocation value or a distinct
leading phrase users naturally request. Put branch-only knowledge in an owned
reference and deterministic work in a script.

When the same material appears in two skills, do not copy it a third time. Ask
which module owns it and pick one of three answers: **extract** it into a
reference skill when nothing owns it, **enforce** the existing seam when a
module owns it and a caller copied past its interface, or **document** it once
when it is a rule rather than a capability — in `AGENTS.md` for rules governing
this repository, in `skills/meta/rhdh-skill-authoring/` for rules that must ship
with the pack, because `AGENTS.md` does not travel with it.

That applies to prose only. Bundled scripts are self-contained and may duplicate
utility code; there is no shared runtime package. See
[ADR-0006](docs/adr/0006-duplication-by-layer.md).

Draft work belongs under `internal/in-progress/`, outside the promoted discovery
root. Retired history belongs under `internal/deprecated/`. Neither ships.

## Add or change a promoted skill

1. Create the skill at `skills/<category>/<name>/SKILL.md`, where `<category>` is
   `engineering`, `operations`, or `maintainers`. Keep the frontmatter `name`
   lowercase and equal to the directory name.
2. Write a description that states the capability and genuine trigger branches
   in fewer than 1024 characters.
3. Keep the `SKILL.md` interface concise and disclose branch-only material.
4. Add `agents/openai.yaml` with display name and short description.
5. Use human-only metadata only for `ask-rhdh` and `setup-rhdh-skills`.
6. Invoke other skills by name. Exchange structured data through a versioned
   artifact whose shape is registered in
   `skills/engineering/rhdh-context/scripts/artifact-contracts.json`. Add the
   contract there before any skill declares that it produces or consumes it.
7. For external writes, produce a `MutationPlan`, obtain approval, execute the
   selected adapter, and write a hash-matched mutation receipt. Setup may also
   return `SetupReceipt`, but it never replaces the mutation receipt.
8. Add the skill to `skills/engineering/setup-rhdh-skills/assets/catalog.json`
   with its category, invocation, required skills, and produced and consumed
   artifacts. A skill missing from that file fails
   `scripts/validate_skill_catalog.py`, and nothing installs it. Update
   `README.md` in the same change whenever membership or naming changes.
9. Add script, artifact, adapter, and catalog contract tests as applicable.
10. Run `uv run pytest`.

Do not add prose-shape assertions. Tests should survive editorial improvements
that preserve the skill interface.

## Preserve setup and state compatibility

Changes to skill layout must retain established runtime locations unless an ADR
explicitly changes them:

- `~/.config/rhdh-skill/config.json`
- `.rhdh/worklog.jsonl`
- `.rhdh/TODO.md`
- the artifact store under the operating system temporary directory

Keep the existing `rhdh` and `rhdh-local` CLI behavior compatible. Update setup
routing rather than introducing a second configuration source.

Keep credentials inside an authenticated adapter backed by a native tool store
or host connector. Only the adapter retrieves a transient credential and
authenticates its request. Keep workflow inputs and outputs credential-free,
return `SetupRequired` when capability is missing, and leave login to the human
setup router.

For external writes, record exactly one ordered `MutationReceipt/v1` outcome
for each approved operation, including failures and skips. Keep the operation
identity and approved plan hash unchanged between plan and receipt.

## Document architectural changes

Update an ADR when a change alters distribution, invocation, composition,
artifact contracts, adapters, or CLI portability. Preserve superseded ADRs as
history and link them to the replacing decision.

Keep `CONTEXT.md` limited to domain language. Skill names and implementation
layout belong in architecture or contributor documentation.

## Release

Git tags are authoritative. Do not add a version file.

- Patch tag: compatible behavior fix.
- Minor tag: new backward-compatible skill or capability.
- Major tag: breaking rename, removal, interface, or artifact change.

The 24-to-18 catalog migration ships as one major cutover. Old skill aliases and
a mixed old/new catalog are intentionally excluded.

After the breaking branch is merged and tagged, a maintainer signs in at
`https://skills.sh/packs/create`, creates the `RHDH complete` pack from the
tagged repository plus `grilling` and `humanizer`, and records the resulting
`https://skills.sh/p/<pack-id>` URL in the setup catalog. Packs are unlisted,
not access-controlled, so never include credentials or private files. Until
that URL exists, `/setup-rhdh-skills` emits the equivalent three-source install
plan.
