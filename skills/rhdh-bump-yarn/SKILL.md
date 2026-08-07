---
name: rhdh-bump-yarn
description: >-
  Bumps Yarn Berry across RHDH-related repos (rhdh-plugins, rhdh midstream,
  rhdh-plugin-export-overlays, rhdh downstream, rhdh-plugin-catalog) using
  `yarn set version` for workspaces, plus Containerfile / Fullsend / inherited
  lock refresh. Use for RHIDP-16074-style upgrades or scanning yarn pins.
---

# RHDH multi-repo Yarn bump

## Goal

Propagate a Yarn Berry bump (e.g. [rhdh-plugins#2918](https://github.com/redhat-developer/rhdh-plugins/pull/2918), [RHIDP-16074](https://redhat.atlassian.net/browse/RHIDP-16074)) across:

| Repo | Notes |
|------|--------|
| `redhat-developer/rhdh-plugins` | root workspace + Fullsend helper |
| `redhat-developer/rhdh` | root + nested workspaces + Containerfile |
| `redhat-developer/rhdh-plugin-export-overlays` | many `packageManager` pins |
| `rhidp/rhdh` | distgit binary + `ENV YARN=` |
| `rhidp/rhdh-plugin-catalog` | per-workspace pins + Containerfiles |

## Prefer Yarn’s own bump

Workspace `packageManager` / `yarnPath` / `.yarn/releases` are updated with:

```bash
yarn set version <to>    # exact version, not `stable`
yarn install --mode=update-lockfile
```

Do **not** hand-download Berry binaries or regex-rewrite `package.json` / `.yarnrc.yml` for normal workspaces. Use an exact `--to` so trees match the Renovate/reference PR.

## Script

```bash
SKILL="skills/rhdh-bump-yarn"   # or installed skill root
node "$SKILL/scripts/bump-yarn.js" --to 4.17.1 \
  --root /path/to/rhdh-plugins \
  --root /path/to/rhdh \
  --root /path/to/overlays \
  --root /path/to/rhdh-downstream \
  --root /path/to/rhdh-plugin-catalog
```

Defaults:
- `--from 4.12.0,4.14.1` — only those move; `4.8.1` / `4.9.2` / Yarn 3.x / dcm `4.15.0` stay
- For each matching `packageManager`: run `yarn set version <to>`
- Rewrite **extra** pins Yarn cannot see: Containerfile / Dockerfile / `ENV YARN=` / embedded `yarn set version` / Fullsend `.fullsend/**/bin/yarn`
- Replace orphan `.yarn/releases` binaries (e.g. distgit) with no `packageManager`
- Refresh every `yarn.lock` that will run under `--to` (including inherited root pins); skip `dist-dynamic` and explicit older pins. Full five-repo regen can take **>45 minutes**; use `--no-refresh-locks` to skip

```bash
node "$SKILL/scripts/bump-yarn.js" --scan --root /path/to/repo
node "$SKILL/scripts/bump-yarn.js" --to 4.17.1 --root /path/to/repo --dry-run
node "$SKILL/scripts/bump-yarn.js" --to 4.17.1 --root /path/to/repo --no-refresh-locks
```

### Fullsend (rhdh-plugins only)

Prefer deriving the binary from `${FULLSEND_TARGET_REPO_DIR}/.yarnrc.yml` `yarnPath` ([rhdh-plugins#4199](https://github.com/redhat-developer/rhdh-plugins/pull/4199)). The script only rewrites leftover `yarn-<from>.cjs` hardcodes and warns.

## Agent workflow

1. Confirm `--to` / `--from`.
2. Resolve local `--root` checkouts.
3. `--scan`, then bump (`--dry-run` first if unfamiliar).
4. Summarize set-version dirs, extra files, orphan binaries, lock refresh.
5. Commit / PR·MR only when the user asks ([`jira-pr-mr-link`](../jira-pr-mr-link/SKILL.md)).

## Checklist

- [ ] Exact `--to` matches the reference bump
- [ ] `--from` covers intended versions only
- [ ] `yarn set version` used for workspaces (not custom binary rewrite)
- [ ] Containerfile / distgit / Fullsend extras checked
- [ ] Inherited lock refresh done (or `--no-refresh-locks` intentional)
- [ ] New `yarn-*.cjs` binaries executable (`100755`)
