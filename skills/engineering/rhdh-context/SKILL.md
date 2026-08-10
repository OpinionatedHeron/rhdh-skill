---
name: rhdh-context
description: Resolve RHDH repositories, version compatibility, configuration, workspace status, worklogs, and todos. Use for RHDH orientation and read-only context needed by another RHDH skill; implementation work belongs to the domain skill that owns the requested outcome.
---

# RHDH Context

Provide stable environment facts and preserved deterministic CLI behavior. Return context through
artifacts so consumers do not inspect this skill's files or import its Python package.

## Context interface

Produce `RhdhContext/v1` before another skill needs repository, tool, version, or
configuration facts:

```bash
python scripts/context.py --project-root <repo> --json
```

`data.repositories` is an array of `{name, path}`; `data.configuration` carries the
config paths plus `targetRhdh`, `targetBackstage`, and `source`. The source is
`user` when `--target-rhdh` is given, `repository` when the checkout pins a version
in `backstage.json`, and `rhdh-context` when the answer comes from the checked-in
compatibility matrix.

Consume the entire JSON object. Reuse it within the session unless configuration or repository
state changes. If a required capability is missing, return `SetupRequired/v1` and tell the human to
run `/setup-rhdh-skills`; a model skill cannot invoke that human-only entry point.

## Preserved CLI

Run the CLI from this skill directory as `uv run scripts/rhdh <command>`. It is a
bundled wrapper, not an installed executable: `npx skills add` copies skill
directories and installs no console script. `uv` supplies the shared
`rhdh_common` runtime declared in the wrapper's script block, so plain `python`
is not enough.

| Outcome | Interface |
|---|---|
| Environment orientation and diagnostics | `uv run scripts/rhdh status`, `uv run scripts/rhdh doctor` |
| Layered project/user configuration | `uv run scripts/rhdh config ...` |
| Repository submodule setup | `uv run scripts/rhdh setup submodule ...` |
| Overlay workspace inspection | `uv run scripts/rhdh workspace ...` |
| Worklog state | `uv run scripts/rhdh log ...` |
| Todo state | `uv run scripts/rhdh todo ...` |

Config, worklog, todo, JSON envelopes, exit codes, and existing `.rhdh` state remain compatible.
Local runtime actions belong to `/rhdh-local`. The compatibility command
`uv run scripts/rhdh local ...` delegates to the standalone `rhdh-local` executable; this skill
does not import or locate another skill's files.

## Artifact interface

Keep ordinary handoffs in conversation. Persist only cross-session handoffs:

```bash
uv run scripts/artifact_store.py validate <artifact.json> --json
uv run scripts/artifact_store.py persist <artifact.json> --project-root <repo> --json
uv run scripts/artifact_store.py read <contract> <id> --project-root <repo> --producer <skill> --json
uv run scripts/artifact_store.py cleanup --project-root <repo> --older-than-days 30 --json
```

The store writes to the operating system temporary directory, namespaced by project root so two
checkouts never collide, and rejects credential-like fields and values recursively. `persist`
returns the absolute path it wrote. Because temporary storage is purged, a cross-session artifact
can disappear: `read` reports `ARTIFACT_EXPIRED` and names the skill to re-run instead of failing on
a missing file. A worklog or todo mutation produces `WorkStateReceipt/v1`; it does not become a
generic artifact automatically.

## Conditional references

- Read [references/rhdh-repos.md](references/rhdh-repos.md) when identifying an RHDH repository or
  explaining ecosystem relationships.
- Read [references/versions.md](references/versions.md) when a workflow needs the checked-in
  compatibility matrix. Prefer live repository facts when they disagree with cached prose.

## Completion

Report the resolved repositories, tool status, target versions and their source, and any
capability the caller must set up. Context is complete when every requested fact has a source,
unresolved capabilities are explicit, and the consumer receives a versioned artifact rather than a
filesystem pointer.
