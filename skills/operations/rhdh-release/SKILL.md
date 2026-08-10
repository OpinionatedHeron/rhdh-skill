---
name: rhdh-release
description: >-
  Plans and reports RHDH releases, including schedules, status, teams, blockers,
  CVEs, release notes, freeze announcements, plugin-overlay CVE CSVs, and Konflux
  release-data RPA tag updates. Use for RHDH release readiness or release artifacts.
compatibility: "Python 3; Node.js for overlay CVE export; bash/yq for RPA updates; acli and gog for live release data."
---

# RHDH release operations

This skill is the release seam: it gathers facts, renders release artifacts, and
plans release mutations. Detailed procedures remain in local workflow files.

## Interfaces

- Consumes from `rhdh-jira`: `JiraCapabilities/v1`, `JiraQueryResult/v1`, and
  `IssueContext/v1` for a single named blocker or CVE issue.
- Produces: `ReleaseSnapshot/v1`, `ReleaseSchedule/v1`,
  `ReleaseAnnouncement/v1`, `ReleaseNotesDraft/v1`, `OverlayCveManifest/v1`,
  `RpaChange/v1`, `MutationPlan/v1`, and `MutationReceipt/v1`.
- Invokes `rhdh-ci` by name only for a separate Tekton update and consumes
  `KonfluxUpdateReport/v1` when that branch is requested.

## Route

| Intent | Load or run | Output |
|---|---|---|
| Check prerequisites | `scripts/release.py check` | capability report |
| Current/future dates | `workflows/release-dates.md` or `workflows/future-release-dates.md` | `ReleaseSchedule/v1` |
| Status, teams, blockers, epics, CVEs, notes | matching file in `workflows/` | `ReleaseSnapshot/v1` |
| Freeze/post-freeze announcement | matching `workflows/announce-*.md` or `workflows/post-code-freeze.md` | `ReleaseAnnouncement/v1` |
| Rich Filter catalog/query | `workflows/rich-filter-catalog.md` | `ReleaseSnapshot/v1` |
| Release-note draft | `workflows/release-notes.md` | `ReleaseNotesDraft/v1` |
| Plugin-package overlay CVE CSV | `workflows/overlay-cve-export.md` | `OverlayCveManifest/v1` |
| Konflux release-data RPA tag change | `workflows/konflux-rpa-update.md` | `RpaChange/v1` |

Use `scripts/release.py --json ...` for deterministic release facts. Load only the
chosen workflow and its directly linked local references.

## Named-skill handoff

Invoke `rhdh-jira` for Jira capability checks and Jira reads. Consume
`JiraCapabilities/v1` and `JiraQueryResult/v1`; do not locate `rhdh-jira` scripts or
references. If unavailable, report which release fields remain unverified.

## Artifact contracts

All artifacts use the shared `contract`, `id`, `createdAt`, and `data` envelope.
Contract-specific fields, including `asOf`, `sources`, and `warnings` where
applicable, live under `data`.

- `ReleaseSchedule/v1`: required `versions` and `source`, plus `milestones` and
  `date_conflicts`.
- `ReleaseSnapshot/v1`: required `version`, `asOf`, and `status`, plus `scope`,
  `counts`, `blockers`, `risks`, and `owners`.
- `ReleaseAnnouncement/v1`: required `kind` and `message`, plus `audience`,
  `channel`, and `evidence`.
- `ReleaseNotesDraft/v1`: required `version` and `sections`, each section holding
  `entries`, plus `missing_notes` and `unresolved_items`.
- `OverlayCveManifest/v1`: required `version` and `entries` for the CSV rows, plus
  `columns`, `source_refs`, and `unresolved`.
- `RpaChange/v1`: required `version` and `changes`, each change holding `file`,
  `old_tag`, and `new_tag`, plus `repository` and `verification`.

## Mutation contract

CSV generation to a new local file is an artifact write; RPA edits, commits, pushes,
merge requests, Jira changes, and message posting are mutations. Before any such
action, invoke the named skill `rhdh-artifacts` and follow its plan, approval
hash, and receipt protocol rather than restating it here. Operations use
`ownerSkill: rhdh-release` with the adapter that performs the write, and outcomes
also record changed resources, verification, and remaining risks. Drafting text in
chat and dry-run inspection remain read-only.

## Local deterministic adapters

| File | Purpose |
|---|---|
| `scripts/release.py` | Release data and announcement CLI; supports `--json` |
| `scripts/compute-plugin-package-overlay-cve-list.mjs` | Compute overlay CVE CSV rows |
| `scripts/update-rpa-tags.sh` | Update Konflux RPA tags |

These adapters are local implementation details; named artifacts, not filesystem
paths, are the public composition seam. Jira field extraction comes from
`rhdh_common.jira`, and Jira reads cross `rhdh-jira` by name — this skill keeps
no copy of either.

## Completion

Complete when every release fact in the answer names the workflow or
`scripts/release.py --json` call that produced it, `data.asOf` records when it was
read, and every Rich Filter or JQL behind it appears in `data.sources`. A field
`rhdh-jira` could not supply is listed as unverified, never inferred from an
earlier release. A rendered artifact is complete only when it carries the fields
required above for its contract. Any RPA edit, posted message, or Jira change is
complete only when its `MutationReceipt/v1` holds one outcome per operation in
the approved `MutationPlan/v1`, naming the changed file and tag or the message
URL.
