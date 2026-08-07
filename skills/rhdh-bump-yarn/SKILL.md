---
name: rhdh-bump-yarn
description: >-
  Bumps Yarn Berry across RHDH-related repos (rhdh-plugins, rhdh midstream,
  rhdh-plugin-export-overlays, rhdh-cli, GitLab CEE rhidp/rhdh +
  rhdh-plugin-catalog) using `yarn set version` + install, plus Containerfile /
  ENV YARN= extras. Use for RHIDP-16074-style upgrades or scanning yarn pins.
---

# RHDH multi-repo Yarn bump

## Goal

Propagate a Yarn Berry bump (e.g. [rhdh-plugins#2918](https://github.com/redhat-developer/rhdh-plugins/pull/2918), [RHIDP-16074](https://redhat.atlassian.net/browse/RHIDP-16074)) across:

| Repo | Notes |
|------|--------|
| [`redhat-developer/rhdh-plugins`](https://github.com/redhat-developer/rhdh-plugins) | root workspace (+ Fullsend if hardcoded) |
| [`redhat-developer/rhdh`](https://github.com/redhat-developer/rhdh) | root + nested workspaces + Containerfile |
| [`redhat-developer/rhdh-plugin-export-overlays`](https://github.com/redhat-developer/rhdh-plugin-export-overlays) | many `packageManager` pins |
| [`redhat-developer/rhdh-cli`](https://github.com/redhat-developer/rhdh-cli) | Yarn **3.8.6** → use `--from 3.8.6` (not in default `--from`) |
| [`gitlab.cee.redhat.com/rhidp/rhdh`](https://gitlab.cee.redhat.com/rhidp/rhdh) | distgit binary + `ENV YARN=` (copy binary from GH bump) |
| [`gitlab.cee.redhat.com/rhidp/rhdh-plugin-catalog`](https://gitlab.cee.redhat.com/rhidp/rhdh-plugin-catalog) | per-workspace pins + Containerfiles |

## What actually changes

For each matching workspace:

```bash
yarn set version <to>                 # packageManager + yarnPath + .yarn/releases
chmod +x .yarn/releases/yarn-<to>.cjs
yarn install --mode=update-lockfile
```

Plus pins Yarn cannot see: `ENV YARN=`, Containerfile / Dockerfile / embedded `yarn set version`.

**No binary download.** Bump GitHub repos first (`yarn set version` produces `yarn-<to>.cjs`). For **GitLab CEE** midstream/distgit trees (`gitlab.cee.redhat.com/rhidp/rhdh`, `…/rhdh-plugin-catalog`) that only ship a checked-in release + `ENV YARN=`, copy that same `yarn-<to>.cjs` into `.yarn/releases/` (and remove the old `yarn-<from>.cjs`), then run the script so text pins update. Use `glab` against `gitlab.cee.redhat.com` (not `gitlab.com`) when opening MRs for those roots.

Use an **exact** `--to` (not `stable`) so every repo matches the Renovate/reference PR.

## Script

```bash
SKILL="skills/rhdh-bump-yarn"
# GH first (4.12/4.14 defaults), then GL (after copying yarn-<to>.cjs into distgit if needed)
node "$SKILL/scripts/bump-yarn.js" --to 4.17.1 \
  --root /path/to/rhdh-plugins \
  --root /path/to/rhdh \
  --root /path/to/overlays \
  --root /path/to/rhdh-downstream \
  --root /path/to/rhdh-plugin-catalog

# rhdh-cli is still on Yarn 3.8.6 — pass --from explicitly
node "$SKILL/scripts/bump-yarn.js" --to 4.17.1 --from 3.8.6 \
  --root /path/to/rhdh-cli
```

Defaults:
- `--from 4.12.0,4.14.1` — only those move (`4.8.1` / `4.9.2` / dcm `4.15.0` stay). **`rhdh-cli` needs `--from 3.8.6`.**
- Lock refresh for every `yarn.lock` under `--to` (incl. inherited root pin); skip `dist-dynamic` and explicit older pins. Full multi-repo regen can take **>45 minutes**; use `--no-refresh-locks` to skip

```bash
node "$SKILL/scripts/bump-yarn.js" --scan --root /path/to/repo
node "$SKILL/scripts/bump-yarn.js" --to 4.17.1 --root /path/to/repo --dry-run
node "$SKILL/scripts/bump-yarn.js" --to 4.17.1 --root /path/to/repo --no-refresh-locks
```

## Agent workflow

1. Confirm `--to` / `--from`.
2. Resolve local `--root` checkouts; bump **GitHub** roots first.
3. For GitLab CEE midstream/distgit (`gitlab.cee.redhat.com/rhidp/rhdh`, `…/rhdh-plugin-catalog`): copy `yarn-<to>.cjs` from a GH bump into `.yarn/releases/` (drop old `--from` binary).
4. `--scan`, then bump (`--dry-run` first if unfamiliar).
5. Summarize set-version dirs, extras, lock refresh.
6. Commit / PR·MR only when the user asks ([`jira-pr-mr-link`](../jira-pr-mr-link/SKILL.md)).

## Checklist

- [ ] Exact `--to` matches the reference bump
- [ ] `--from` covers intended versions only (`3.8.6` for rhdh-cli; default 4.12/4.14 otherwise)
- [ ] GH bumped before GL CEE; distgit binary copied (no curl)
- [ ] Containerfile / `ENV YARN=` extras checked
- [ ] Lock refresh done (or `--no-refresh-locks` intentional)
- [ ] New `yarn-*.cjs` binaries executable (`100755`)
