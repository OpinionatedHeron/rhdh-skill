---
name: rhdh-base-images
description: >-
  Analyzes and updates RHDH base images, Node or Go toolchains, and RPM lockfiles
  across rhdh, rhdh-operator, and rhdh-must-gather. Use for weekly base-image
  maintenance, UBI/RHEL bumps, RPM lockfile refreshes, or image-version skew.
compatibility: "bash, jq, skopeo, curl, git; podman or docker for toolchain detection; gh for PR creation."
---

# RHDH base images

Use the bundled scripts instead of reconstructing their repository-specific logic.

## Interfaces

- Produces: `BaseImageReport/v1`, `MutationPlan/v1`, and `MutationReceipt/v1`.
- Consumes: no cross-skill artifact; it executes only from its own approved
  `MutationPlan/v1`.
- Repository checkouts are explicit user-scoped inputs, not skill-to-skill paths.

## Route

| Intent | Load or run | Output |
|---|---|---|
| Read-only current/latest image scan | `workflows/update-base-images.md`, then `scripts/base-images-and-rpms.sh --analyze ...` | `BaseImageReport/v1` |
| Explain repository rules | `references/repos.md` | guidance |
| Preview an update | `workflows/update-base-images.md`, then `scripts/base-images-and-rpms.sh --dry-run ...` | `MutationPlan/v1` evidence |
| Update images, lockfiles, Node headers, or Go toolchain | `workflows/update-base-images.md` | `MutationReceipt/v1` |

`BaseImageReport/v1` contains required `summary` and `changes`, plus
`repositories`, `fromImages`, `currentTags`, `latestTags`, `ubiSkew`,
`toolchainDrift`, `sources`, and `warnings`.

## Mutation contract

Any checkout, branch, file edit, dependency install, commit, push, or PR is a
mutation. First run read-only discovery or `--dry-run`, then invoke the named
skill `rhdh-mutation-gate` and follow its plan, approval hash, and receipt protocol
rather than restating it here. Operations use `ownerSkill: rhdh-base-images`
with adapter `shell`, operation names such as `repository.base-images.update`,
and a target naming the repository and branch, for example `rhdh:release-1.x`.
Outcomes also record changed resources, verification, and remaining risks.

Installing `rpm-lockfile-prototype`, logging into registries, using `--push`, and
opening PRs must appear as distinct actions. Default to local/no-push behavior; do
not push directly to protected branches. Verify branch existence and repository
cleanliness before mutation.

## Repository invariants

- Accepted branch selectors are `main` or `release-*`; map them to the documented
  GitLab scripts branch in `references/repos.md`.
- Keep base-image UBI minors aligned with RPM repository URLs.
- On RHDH, update Node headers when the builder image changes Node.
- On rhdh-operator `main`, align `go.mod` with the Go toolset image.
- Exclude RHDH `e2e-tests/` and `.ci/` from image scans.

This skill exposes artifacts rather than script paths to other skills.

## Completion

An analysis is complete when `BaseImageReport/v1` `data.changes` covers every
repository in scope with its current and latest tag, `data.ubiSkew` and
`data.toolchainDrift` are populated or explicitly empty, and every registry,
lockfile, or branch the scan could not read appears in `data.warnings` instead of
being reported as current. An update is complete when the target branch was
verified to exist against a clean working tree before any edit, every operation in
the approved `MutationPlan/v1` has one outcome in `MutationReceipt/v1`, and the
push and PR state is stated explicitly — including "not pushed" when the default
local behavior was kept.
