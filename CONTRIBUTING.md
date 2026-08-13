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
are editorial and are stripped at install:

- `skills/jira/`
- `skills/plugins/`
- `skills/ci/`
- `skills/release/`
- `skills/reference/`
- `skills/meta/`

A category move must not change how callers invoke a skill. Compose with a
stable `/skill-name`; never reference another category's internal file.

A skill claims exactly one trigger phrase. Split by verb rather than by noun, and
weight the split by what a misroute costs: merge where a misroute produces a wrong
write, split where it produces an obvious wrong answer. Put branch-only knowledge
in an owned reference and deterministic work in a script.

When the same material appears in two skills, do not copy it a third time. Ask
which module owns it and pick one of three answers: **extract** it into a
reference skill when nothing owns it, **enforce** the existing seam when a
module owns it and a caller copied past its interface, or **document** it once
when it is a rule rather than a capability — in `AGENTS.md` for rules governing
this repository, in `skills/meta/skill-authoring/` for rules that must ship
with the pack, because `AGENTS.md` does not travel with it.

That applies to prose only. Bundled scripts are self-contained and may duplicate
utility code; there is no shared runtime package. See
[ADR-0006](docs/adr/0006-duplication-by-layer.md).

Draft work belongs under `internal/in-progress/`, outside the promoted discovery
root. Retired history belongs under `internal/deprecated/`. Neither ships.

## Add or change a promoted skill

1. Create the skill at `skills/<category>/<name>/SKILL.md`. Keep the frontmatter
   `name` lowercase and equal to the directory name. Name it after its subject:
   `rhdh-` belongs on a skill about Red Hat Developer Hub, and a genuinely generic
   skill takes a generic name.
2. Write a description that states the capability and genuine trigger branches
   in fewer than 1024 characters. It is the routing surface — keep the literal
   proper nouns, and never name a sibling skill or a literal you are disclaiming.
3. Keep the `SKILL.md` interface concise and disclose branch-only material.
4. Add `agents/openai.yaml` with display name and short description.
5. Use human-only metadata only for `ask-rhdh` and `setup-rhdh-skills`.
6. Invoke other skills by name and read what they report. There are no artifact
   contracts: no versioned envelope, no store, no material hash.
7. For an external write, state each operation with its target, exact command,
   preview, and failure behaviour; get approval for that stated set; execute; then
   report the outcome of every operation, including the skipped ones. Cite
   `/rhdh-mutation-gate` rather than restating the rule.
8. Add the skill to `skills/meta/setup-rhdh-skills/assets/catalog.json` with its
   category, invocation, and required skills. A skill missing from that file fails
   `scripts/validate_skill_catalog.py`, and nothing installs it. Update
   `README.md` in the same change whenever membership or naming changes, and
   regenerate the `/ask-rhdh` table with
   `cd skills/meta/ask-rhdh && python scripts/render_routes.py --write`.
9. Cite nothing outside the skill's own directory. `AGENTS.md`, `CONTEXT.md`,
   this file, and `docs/adr/` do not ship — a skill that references them is broken
   for everyone who installs it. Restate the rule locally instead.
10. Add script, adapter, and catalog contract tests as applicable.
11. Run `uv run pytest`.

Do not add prose-shape assertions. Tests should survive editorial improvements
that preserve the skill interface.

## Preserve setup and state compatibility

Changes to skill layout must retain established runtime locations unless an ADR
explicitly changes them:

- `~/.config/rhdh-skill/config.json`
- `.rhdh/worklog.jsonl`
- `.rhdh/TODO.md`

Keep the existing `rhdh` and `rhdh-local` CLI behavior compatible. Update setup
routing rather than introducing a second configuration source.

Keep credentials inside an authenticated adapter backed by a native tool store
or host connector. Only the adapter retrieves a transient credential and
authenticates its request. Keep workflow inputs and outputs credential-free, name
the missing capability and its exact `/setup-rhdh-skills <route>` when one is
absent, and leave login to the human setup router.

For external writes, report one outcome for each approved operation, including
failures and skips, naming the target it changed.

## Document architectural changes

Update an ADR when a change alters distribution, invocation, composition,
adapters, or CLI portability. Preserve superseded ADRs as history and link them
to the replacing decision — unless the decision never shipped, in which case
rewrite it in place rather than recording a supersession no reader ever saw.

Keep `CONTEXT.md` limited to domain language. Skill names and implementation
layout belong in architecture or contributor documentation.

## Release

Git tags are authoritative. Do not add a version file.

- Patch tag: compatible behavior fix.
- Minor tag: new backward-compatible skill or capability.
- Major tag: breaking rename, removal, or interface change.

The decomposition to one skill per trigger phrase ships as one major cutover. Old
skill aliases and a mixed old/new catalog are intentionally excluded.

After the breaking branch is merged and tagged, a maintainer signs in at
`https://skills.sh/packs/create`, creates the `RHDH complete` pack from the
tagged repository plus `grilling` and `humanizer`, and records the resulting
`https://skills.sh/p/<pack-id>` URL in the setup catalog. Packs are unlisted,
not access-controlled, so never include credentials or private files. Until
that URL exists, `/setup-rhdh-skills` emits the equivalent three-source install
plan.
