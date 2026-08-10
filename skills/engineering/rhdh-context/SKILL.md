---
name: rhdh-context
description: Resolve RHDH repositories, version compatibility, configuration, workspace status, worklogs, and todos. Use for RHDH orientation and read-only context needed by another RHDH skill; implementation work belongs to the domain skill that owns the requested outcome.
---

# RHDH Context

Provide stable environment facts and preserved deterministic CLI behavior. Return context through
artifacts so consumers do not inspect this skill's files or import its Python package.

## Context interface

Produce `RhdhContext/v1` before another skill needs repository, tool, or configuration facts:

```bash
python scripts/context.py --project-root <repo> --json
```

Consume the entire JSON object. Reuse it within the session unless configuration or repository state
changes. If a required capability is missing, return `SetupRequired/v1` and tell the human to run
`/setup-rhdh-skills`; a model skill cannot invoke that human-only entry point.

## Preserved CLI

Use `rhdh` for deterministic operations whose public behavior predates this refactor:

| Outcome | Interface |
|---|---|
| Environment orientation and diagnostics | `rhdh status`, `rhdh doctor` |
| Layered project/user configuration | `rhdh config ...` |
| Repository submodule setup | `rhdh setup submodule ...` |
| Overlay workspace inspection | `rhdh workspace ...` |
| Worklog state | `rhdh log ...` |
| Todo state | `rhdh todo ...` |

Config, worklog, todo, JSON envelopes, exit codes, and existing `.rhdh` state remain compatible.
Local runtime actions belong to `/rhdh-local`. The compatibility command
`rhdh local ...` delegates to the standalone `rhdh-local` executable; this skill
does not import or locate another skill's files.

## Artifact interface

Keep ordinary handoffs in conversation. Persist only cross-session handoffs:

```bash
python scripts/artifact_store.py validate <artifact.json> --json
python scripts/artifact_store.py persist <artifact.json> --project-root <repo> --json
python scripts/artifact_store.py cleanup --project-root <repo> --older-than-days 30 --json
```

The store writes `.rhdh/artifacts/` and rejects credential-like fields recursively. A worklog or todo
mutation produces `WorkStateReceipt/v1`; it does not become a generic artifact automatically.

## Conditional references

- Read [references/rhdh-repos.md](references/rhdh-repos.md) when identifying an RHDH repository or
  explaining ecosystem relationships.
- Read [references/versions.md](references/versions.md) when a workflow needs the checked-in
  compatibility matrix. Prefer live repository facts when they disagree with cached prose.

Context is complete when every requested fact has a source, unresolved capabilities are explicit,
and the consumer receives a versioned artifact rather than a filesystem pointer.
