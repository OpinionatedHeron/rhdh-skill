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
- Consumes: no cross-skill artifact.
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
mutation. First run read-only discovery or `--dry-run`, then present:

```json
{
  "contract": "MutationPlan/v1",
  "id": "base-image-mutation-<stable-id>",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "summary": "...",
    "operations": [{
      "order": 1,
      "ownerSkill": "rhdh-base-images",
      "adapter": "shell",
      "operation": "repository.base-images.update",
      "target": "rhdh:release-1.x",
      "preview": {"commandOrRequest": "..."},
      "preconditions": [],
      "checks": [],
      "recovery": []
    }],
    "materialHash": "sha256:<canonical-plan-hash>"
  }
}
```

Ask for explicit approval of the exact plan. Execute only approved actions. Return
`MutationReceipt/v1` whose `data` contains `planId`, the same `materialHash`, and
`outcomes` containing status, attempted/completed operations, changed resources,
verification, and remaining risks.

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

This skill is independently installable and exposes artifacts rather than script
paths to other skills.
