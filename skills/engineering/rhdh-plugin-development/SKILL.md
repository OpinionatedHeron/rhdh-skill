---
name: rhdh-plugin-development
description: >-
  Develops Red Hat Developer Hub and Backstage plugins: scaffold backend or
  frontend dynamic plugins, implement features, export and wire packages,
  upgrade Backstage dependencies, migrate legacy frontend plugins to NFS,
  diagnose and fix plugin bugs, and place tests at the cheapest effective
  layer. Use for code changes in rhdh-plugins or community-plugins, plugin
  creation, createFrontendPlugin or Blueprint migrations, Backstage version
  bumps, plugin test design, and Jira or GitHub plugin bug fixes. Hand off PR
  publication, overlay catalog work, or local RHDH execution to the named
  domain skill after producing the artifact defined below.
compatibility: "Node.js 22+, Yarn, and Python 3; container runtime for plugin export or local verification."
---

# RHDH Plugin Development

Own the source-code lifecycle. Discover the workspace before choosing a route,
keep deterministic operations in `scripts/`, and stop at a verified change
artifact unless the user also requests a named downstream skill.

## Start here

1. Read repository instructions and any linked specification or issue.
2. Run `python scripts/detect-rhdh-context.py --path <plugin-or-workspace>` when
   working in an existing checkout. Record role, frontend system, plugin ID,
   dynamic status, and package manager.
3. Establish the target RHDH and Backstage versions. Prefer an explicit user or
   repository value. Otherwise invoke `/rhdh-context` and request
   `RhdhContext/v1`; if that skill is unavailable, ask the user instead of
   guessing.
4. Protect existing work: inspect branch and status before modifying files.

For a new plugin, public API change, or migration with materially different
valid designs, `/grilling` is a required design gate when the intent does not
already settle the choice. Use its resulting constraints, then show the design
choice before implementation. If `/grilling` is not
installed, return
`SetupRequired/v1` with `data.missing: [grilling]` and
`data.nextCommand: /setup-rhdh-skills`, then pause that branch.

## Route by outcome

| Outcome | Load and follow |
|---|---|
| Create a backend dynamic plugin | `references/backend.md`; run `scripts/scaffold.py` |
| Create a frontend dynamic plugin | `references/frontend.md`; also load `references/bui.md` and `references/nfs.md` |
| Implement or review plugin code | `references/development-patterns.md`, then only the relevant `references/plugin-types.md`, `references/rhdh.md`, `references/testing.md`, `references/dev-app.md`, or `references/bui.md` |
| Export, package, or publish an artifact | `references/export.md`; run `scripts/export-plugin.py` |
| Generate frontend wiring | `references/wiring.md`; load `references/frontend-wiring.md` for non-trivial mount points |
| Upgrade Backstage dependencies | `workflows/upgrade-backstage.md` |
| Migrate legacy frontend code to NFS | `workflows/migrate-nfs.md` |
| Test an NFS migration | `workflows/test-nfs-plugin.md` |
| Reproduce, diagnose, and fix a plugin bug | `workflows/fix-bug.md` |
| Decide where a test belongs or write it | `references/test-placement.md` |

Infer a clear route from the request. Ask only when the missing choice changes
the implementation, such as backend versus frontend or alpha versus colocated
NFS exports.

## Invariants

- Match the target repository's instructions and neighboring implementation.
- Use the Backstage new backend system. Preserve legacy frontend consumers
  during NFS migration unless the user explicitly approves a breaking change.
- Reproduce a bug before fixing it. Temporary reproduction tests and captured
  artifacts never enter the deliverable diff.
- Choose the cheapest test layer that can catch the failure. Mirror a current
  neighboring test instead of recalling unstable Backstage test APIs.
- Verify visual changes in a running app in addition to type checking and tests.
- Do not stage, commit, push, or create a PR as part of this skill. Leave the
  changed files unstaged and list them in `ChangeHandoff/v1` `data.files`; the
  publishing skill stages exactly those paths under its own approval gate.
- A triage label or checklist comment on a GitHub issue is an external write.
  Invoke the named skill `rhdh-artifacts`, obtain approval of the
  `MutationPlan/v1` material hash, and return `MutationReceipt/v1`. A request to
  fix a bug approves no issue write.

## Artifact contracts

`RhdhContext/v1` input uses the standard envelope; version selection lives in
`data.configuration`:

```yaml
contract: RhdhContext/v1
id: context-id
createdAt: ISO-8601
data:
  repositories: [{name: overlay, path: /abs/path}]
  tools: {git: installed}
  configuration:
    dataDirectory: path
    projectConfig: path
    userConfig: path
    targetRhdh: "1.x"
    targetBackstage: "1.x.y"
    source: user | repository | rhdh-context
```

`source` records where the versions came from: `user` for an explicit value,
`repository` for a checkout that pins Backstage in `backstage.json`, and
`rhdh-context` for the checked-in compatibility matrix.

`ChangeHandoff/v1` output:

```yaml
contract: ChangeHandoff/v1
id: change-id
createdAt: ISO-8601
data:
  summary: concise change summary
  files: []
  verification:
    contract: VerificationEvidence/v1
    id: change-verification-id
    createdAt: ISO-8601
    data: {subject: change-id, checks: [], result: pass | fail | partial}
  repository: owner/repo
  workspace: path
  changeKind: feature | bug-fix | upgrade | nfs-migration | scaffold | packaging
  issue: {source: jira | github | none, keyOrNumber: null, url: null, title: null}
  rootCause: null
  recordings: {before: null, after: null}
  testPlan: []
  releaseNote: null
```

Keep absent optional fields `null`; never invent evidence.

## Named handoffs

- To resolve a GitHub issue or pull request reference, invoke `/rhdh-forge` and
  consume `IssueContext/v1`. Load `references/github-input.md` for the field
  mapping and the gated interaction payloads.
- To publish a verified change, invoke `/rhdh-pull-request` with the complete
  `ChangeHandoff/v1`, `data.files` populated and unstaged. That skill stages those
  paths and owns changesets, commit, push, PR body, recording upload, and issue
  updates. It has no auto-approve mode; every external write still requires
  approval of an exact `MutationPlan/v1` material hash.
- To test an exported plugin in local RHDH, invoke `/rhdh-local` with a
  `ChangeHandoff/v1` whose data includes the exact package artifact, plugin
  config, required environment variable names, and verification checklist.
- To add or update catalog packaging, invoke `/rhdh-overlay` with a
  `ChangeHandoff/v1` containing source repository/ref, package names,
  target versions, and any produced artifacts.

Do not load another skill's files. Invoke it by name and pass the artifact in
the conversation.

## Completion

Report the chosen route, changed files, verification evidence, unresolved
risks, and the final `ChangeHandoff/v1`. Offer the appropriate named handoff only
when publication, overlay work, or local execution is in scope.
