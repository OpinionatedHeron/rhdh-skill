# RHDH ReleasePlanAdmission files (stone-prod-p02)

Path (relative to konflux-release-data root):

`config/stone-prod-p02.hjvn.p1/product/ReleasePlanAdmission/rhdh/`

## Stream RPAs updated by this skill

| Pattern | Purpose |
|---------|---------|
| `rhdh-1-{N}-prod.yaml` | Hub, operator, bundle — production |
| `rhdh-1-{N}-stage.yaml` | Hub, operator, bundle — staging |
| `rhdh-plugin-catalog-1-{N}-prod.yaml` | Plugin catalog index/builder/plugins — production |
| `rhdh-plugin-catalog-1-{N}-stage.yaml` | Plugin catalog — staging |

`{N}` is the minor stream with dots replaced by dashes (`1.9` → `1-9`, `1.10` → `1-10`).

## RPAs not updated by patch-bump script

| File | Reason |
|------|--------|
| `rhdh-1-*-fbc-*.yaml` | FBC (File-Based Catalog) operator index, separate lifecycle |
| `rhdh-plugin-catalog-1-stage.yaml` | Rolling `1.next` / stage catalog, not a versioned stream |
| `rhdh-plugin-catalog-builder-1-*-stage.yaml` | Builder-only stage RPAs |

## Tag shapes

**Hub/operator defaults** (`rhdh-1-9-prod.yaml`):

```yaml
defaults:
  tags:
    - "1.9"
    - "1.9.7"
    - "1.9.7-{{ timestamp }}"
```

**Plugin catalog defaults** (same patch tags; `timestamp` template):

```yaml
defaults:
  tags:
    - "1.9"
    - "1.9.7"
    - "1.9.7-{{ timestamp }}"
```

**Plugin catalog component** (RHDH patch + upstream plugin version):

```yaml
tags:
  - "1.9"
  - "1.9.7"
  - "1.9.7--1.20.2"
  - "1.9.7--1.20.2-{{ release_timestamp }}"
```

The patch-bump script replaces the RHDH patch prefix everywhere it appears in
these four stream files. A full plugin semver refresh (changing `--1.20.2` suffixes)
is a separate, manual MR when snapshots ship new plugin versions.
