---
name: rhdh-plugin-midstream-propagate
description: >-
  Propagates an rhdh-plugins workspace change through overlays and
  rhdh-plugin-catalog (midstream): changeset + npm publish, overlays source.json
  to the Version Packages SHA, then a surgical catalog MR (overlay-repo/,
  workspaces/, plugin_builds/, .tekton PLR tags like 2.0.0--0.0.3) without a full
  sync-midstream --force-clone. Use when promoting plugin versions, waiting on
  npm @red-hat-developer-hub packages, bumping overlays repo-ref, or midstream
  Hermeto/lock/PLR updates for one workspace.
---

# RHDH plugin → overlays → catalog propagate

Three-step chain after a fix or feature in [`redhat-developer/rhdh-plugins`](https://github.com/redhat-developer/rhdh-plugins):

1. Update **rhdh-plugins** with the change, including a **changeset**; wait until merged and new package(s) are published to npmjs.com (e.g. [`@red-hat-developer-hub/backstage-plugin-app-defaults`](https://www.npmjs.com/package/@red-hat-developer-hub/backstage-plugin-app-defaults) `0.0.3` and other packages published at the same time).
2. Update the **overlays** repo (`rhdh-plugin-export-overlays`) to fetch the commit SHA for the **Version Packages** PR related to the above change.
3. Grab the specific changes from that SHA and push them into **rhdh-plugin-catalog**, updating `overlay-repo/`, `workspaces/`, and other paths that `sync-midstream.sh` would touch for a full clone of **just that workspace**; open an MR that applies the updated files and bumps associated PLR(s) in `.tekton/` to the appropriate tags (e.g. `2.0.0--0.0.3`).

Prefer a **surgical** catalog MR over `build/ci/sync-midstream.sh --force-clone <workspace>` (minutes vs a long full re-clone/export). Fall back to scoped `--force-clone` only when export / `plugin_builds` annotations / workspace transform must be regenerated.

## Repos and config

| Step | Repo | Config key |
|------|------|------------|
| 1 | [`redhat-developer/rhdh-plugins`](https://github.com/redhat-developer/rhdh-plugins) | `plugins` |
| 2 | [`redhat-developer/rhdh-plugin-export-overlays`](https://github.com/redhat-developer/rhdh-plugin-export-overlays) | `overlay` |
| 3 | [`gitlab.cee.redhat.com/rhidp/rhdh-plugin-catalog`](https://gitlab.cee.redhat.com/rhidp/rhdh-plugin-catalog) | `catalog` |

Resolve checkouts via `$RHDH config get <key>` when set. Use `glab` against **`gitlab.cee.redhat.com`** for catalog MRs (not `gitlab.com`).

Confirm a Jira key before opening PRs/MRs; use `jira-pr-mr-web-link` / `create-pr-mr.js`.

---

## Step 1 — rhdh-plugins (+ changeset → npm)

1. Implement the change in `workspaces/<ws>/` (resolutions, sources, lock refresh as needed).
2. Add a **changeset** under `workspaces/<ws>/.changeset/` so Changesets opens a **Version Packages** PR. A merge without a changeset will not bump/publish packages.
3. Open/merge the fix PR, then wait for the bot **Version Packages** PR to merge.
4. Confirm npm publish for every package in that release:

```bash
npm view @red-hat-developer-hub/backstage-plugin-<name> version
npm view @red-hat-developer-hub/backstage-plugin-<name>@<ver> gitHead
# Sibling packages often publish together — list from the Version Packages PR / changeset
```

Gate: npm versions match the Version Packages bump; `gitHead` equals the Version Packages merge commit SHA.

Optional: chain [`raise-pr`](../raise-pr/SKILL.md) for build/changeset/PR on rhdh-plugins.

---

## Step 2 — overlays (`source.json` → Version Packages SHA)

After npm is live:

1. Resolve SHA (prefer npm `gitHead`; cross-check Version Packages merge commit):

```bash
SHA=$(npm view @red-hat-developer-hub/backstage-plugin-<name>@<ver> gitHead)
gh pr view <version-packages-pr> --repo redhat-developer/rhdh-plugins \
  --json mergeCommit --jq .mergeCommit.oid
```

2. In overlays `workspaces/<ws>/`:
   - Set `source.json` `repo-ref` to that full SHA.
   - Keep `repo-backstage-version` aligned with upstream at that commit.
   - Bump `metadata/*.yaml` `spec.version` and `dynamicArtifact` OCI tags (`bs_<bs>__<pluginVer>`) for every package published in the same Version Packages PR.

3. Open/merge the overlays PR. Catalog midstream must wait until this lands on overlays `main` (or the release branch you target).

See [`overlay` update-plugin](../overlay/workflows/update-plugin.md) for the generic source.json pattern; this skill requires the SHA to be the **Version Packages** commit (not the earlier fix commit).

---

## Step 3 — catalog surgical midstream MR

**Read** [`references/catalog-surgical-update.md`](references/catalog-surgical-update.md) before editing.

Goal: same file set `sync-midstream.sh --force-clone '<ws>'` would refresh for **one** workspace, without cloning every workspace.

### Preferred (surgical)

1. Sync `overlay-repo/workspaces/<ws>/` from overlays main (`source.json`, `plugins-list.yaml`, `metadata/`, overlays/patches if present).
2. Apply upstream deltas at `$SHA` into `workspaces/<ws>/` — at minimum `package.json`, `yarn.lock`, and any plugin `package.json` version bumps; expand to plugin sources when the Version Packages change is not lock/metadata-only.
3. Align `plugin_builds/<ws>/*.json` `registryReference` tags (`quay.io/rhdh/...:<rhdh>--<pluginVer>`, e.g. `2.0.0--0.0.3`).
4. Bump associated `.tekton/` PLRs / Containerfiles:
   - `konflux.additional-tags` → `<xy>--<ver>,<x.y.z>--<ver>` (e.g. `2.0--0.0.3,2.0.0--0.0.3`)
   - `DESCRIPTION` plugin version fragment
   - `UPSTREAM_REPO` overlays tree SHA when known
   - Or regenerate with `.tekton/generatePipelineRunsForPlugins.sh -v <rhdh> --path '<ws>/plugins/<plugin>'` / `--package` (after `package.json` versions are updated).
5. Open a catalog MR via `create-pr-mr.js` (CEE GitLab). Cite sibling package versions in the body.

### Fallback (scoped sync)

When export / annotations / `update-workspace.js` transforms are required:

```bash
# From catalog checkout — still scope to one workspace; do not --always-clone
./build/ci/sync-midstream.sh --debug --no --nopush \
  --force-clone '<ws>' \
  --skip-clone 'workspaces/'
# Review diff, then commit / open MR yourself
```

`--force-clone` alone still walks every `source.json`; pair with skip/force so only the target workspace is re-cloned. Prefer surgical when the delta is known (pin, lock, versions).

---

## Checklist

- [ ] rhdh-plugins change includes a changeset; Version Packages merged
- [ ] npm packages published; `gitHead` == Version Packages SHA
- [ ] overlays `repo-ref` + metadata versions/OCI tags updated and merged
- [ ] catalog `overlay-repo/workspaces/<ws>/` matches overlays
- [ ] catalog `workspaces/<ws>/` reflects `$SHA` (lock/resolutions/versions as needed)
- [ ] `plugin_builds/` + `.tekton/` tags match new plugin versions (`x.y.z--<pluginVer>`)
- [ ] Catalog MR on CEE GitLab; Jira linked

## Example (RHIDP-16097 / app-defaults)

| Step | Artifact |
|------|----------|
| 1 | rhdh-plugins fix + changeset → Version Packages → `@…/app-defaults@0.0.3` (`gitHead` `18f4229…`) |
| 2 | overlays PR bumping `workspaces/app-defaults/source.json` + metadata |
| 3 | catalog MR syncing `overlay-repo/…/app-defaults` + workspace lock pin (surgical; no `--force-clone`) |
