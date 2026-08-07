---
name: rhdh-bump-yarn
description: >-
  Bumps Yarn Berry (release binary, yarnPath, packageManager, Containerfile pins,
  and yarn.lock via install) across RHDH-related repos: rhdh-plugins, rhdh midstream,
  rhdh-plugin-export-overlays, rhdh downstream, and rhdh-plugin-catalog. Use when
  aligning Yarn versions (e.g. RHIDP-16074 / rhdh-plugins#2918 yarn 4.17.1), scanning
  checkouts for yarn pins, or mirroring a Renovate yarn bump into midstream/downstream trees.
---

# RHDH multi-repo Yarn bump

## Goal

Propagate a Yarn Berry version bump (reference: [rhdh-plugins#2918](https://github.com/redhat-developer/rhdh-plugins/pull/2918), [RHIDP-16074](https://redhat.atlassian.net/browse/RHIDP-16074)) across the five related trees:

| Repo | Host | Typical shape |
|------|------|----------------|
| `redhat-developer/rhdh-plugins` | GitHub | root `.yarn/releases` + `packageManager` + `yarnPath` |
| `redhat-developer/rhdh` | GitHub | root + `.ci` + `dynamic-plugins` + `e2e-tests` + `build/containerfiles/Containerfile` |
| `redhat-developer/rhdh-plugin-export-overlays` | GitHub | many `packageManager` pins (e2e/smoke/validate); few/no release binaries |
| `rhidp/rhdh` | GitLab | `distgit/containers/rhdh-hub` binary + `Containerfile` `ENV YARN=` |
| `rhidp/rhdh-plugin-catalog` | GitLab | per-workspace `.yarn/releases` + `builder.Containerfile` (`yarn set version`) + `overlay-repo` pins |

## Script location

Scripts live under this skill’s `scripts/` directory. Resolve that path from the
installed skill root (or this checkout):

```bash
SKILL="$(dirname "$(realpath "$0")")/.."   # when already in scripts/
# or, from repo checkout:
SKILL="skills/rhdh-bump-yarn"
```

**Execute** [scripts/bump-yarn.js](scripts/bump-yarn.js); do not reimplement the workflow inline.

## Run the script (preferred)

```bash
node "$SKILL/scripts/bump-yarn.js" --to 4.17.1 \
  --root /path/to/rhdh-plugins \
  --root /path/to/rhdh \
  --root /path/to/overlays \
  --root /path/to/rhdh-downstream \
  --root /path/to/rhdh-plugin-catalog
```

Defaults:
- `--from 4.12.0,4.14.1` (versions RHIDP-16074 replaced). Versions **not** in `--from` (e.g. `4.8.1`, `4.9.2`, Yarn 3.x, `dcm`’s `4.15.0`) stay put.
- **Refresh `yarn.lock`** with `yarn install --mode=update-lockfile` for **every** lock that will run under `--to` yarn — including nested workspaces that only inherit a root `yarnPath` / `packageManager` (this is what `yarn install --immutable` CI needs after a root-only Renovate bump). Skips `dist-dynamic/**` and dirs with an explicit pin outside `--from`/`--to`. Regenerating locks across all five repos can take **>45 minutes**; opt out with `--no-refresh-locks` if you only need pins/binaries first.
- **Binaries** are written `chmod +x` (`100755`) so `yarnPath` stays runnable.

### Useful modes

```bash
# Inventory pins / binaries
node "$SKILL/scripts/bump-yarn.js" --scan --root /path/to/repo

# Preview pins/binaries only (does not run install)
node "$SKILL/scripts/bump-yarn.js" --to 4.17.1 --root /path/to/repo --dry-run

# Cache the Berry CLI binary only
node "$SKILL/scripts/bump-yarn.js" --fetch-only --to 4.17.1

# Skip lock refresh (pins + binaries only)
node "$SKILL/scripts/bump-yarn.js" --to 4.17.1 --root /path/to/repo --no-refresh-locks
```

Binary cache: `~/.cache/rhdh-bump-yarn/yarn-<ver>.cjs`  
Source URL: `https://raw.githubusercontent.com/yarnpkg/berry/@yarnpkg/cli/<ver>/packages/yarnpkg-cli/bin/yarn.js`

## What the script changes

1. **Binaries** — for each `.yarn/releases/yarn-<from>.cjs`, write `yarn-<to>.cjs` (mode `0755`) and remove the old file.
2. **Text pins** in `package.json`, `.yarnrc.yml`, `Containerfile` / `*.Containerfile`, `Dockerfile`, `run-e2e.sh` (and similar):
   - `yarnPath: …/yarn-<from>.cjs`
   - `"packageManager": "yarn@<from>"` (also strips optional `+sha…` suffixes)
   - `yarn set version <from>`
   - `ENV YARN=…yarn-<from>.cjs`
3. **yarn.lock** (default) — discover every `yarn.lock` under the root (except `dist-dynamic` / `node_modules`) whose effective Yarn is `--to` (local `packageManager`/`yarnPath` is `--to` or was in `--from`, **or** there is no local pin and the workspace inherits the bumped root). Run `yarn install --mode=update-lockfile` so `__metadata` (e.g. v8→v10) and builtin patch hashes update; without this, CI `yarn install --immutable` fails with YN0028. Expect **>45 minutes** when refreshing every workspace across the five-repo set.
4. **Report** — remaining `--from` hits (should be none), binaries left alone, lock refresh results, locks skipped for explicit older pins.

## What it does not do

- **Commits / PRs / MRs** — after the bump, commit and open with [`jira-pr-mr-link`](../jira-pr-mr-link/SKILL.md) when the user asks (cite the Jira key they name).
- **rhdh-cli Yarn 3.x** — out of scope unless `--from` includes those versions.

## Agent workflow

1. Confirm `--to` / `--from` (or use defaults for a 4.12/4.14 → 4.17.1 style bump).
2. Resolve local `--root` checkouts for the repos in scope (ask if paths unclear; `rhdh` config keys `plugins`, `rhdh`, `overlay`, `downstream`, `catalog` may help).
3. `--scan` each root; note versions that will be left alone.
4. Run the bump (prefer `--dry-run` first if the tree is dirty/unfamiliar). Expect lock refresh to take **>45 minutes** for a full multi-repo run unless `--no-refresh-locks`.
5. Re-scan or trust script “remaining from-versions: none”; note any failed lock refreshes.
6. Summarize: binaries replaced, files updated, left-alone versions, lock refresh counts/failures.
7. Only commit / open PR·MRs when the user requests; link Jira via `jira-pr-mr-link`.

## Checklist

- [ ] `--to` matches the reference PR (e.g. 4.17.1).
- [ ] `--from` covers every version intended to move; others stay put.
- [ ] All in-scope roots scanned and bumped.
- [ ] No unexpected remaining `--from` pins.
- [ ] Lock refresh completed for inheriting workspaces too (or `--no-refresh-locks` was intentional); failures investigated.
- [ ] New `yarn-*.cjs` binaries are executable (`100755`).
- [ ] PR/MR + Jira only after user asks.
