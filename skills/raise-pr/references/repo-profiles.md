# Repo Profiles

Auto-detect which repository you are in and load the matching profile. Read this file at the start of every `raise-pr` invocation.

## Detection

Run `git remote -v` and inspect all remote URLs (fetch lines). Match against the patterns below. If multiple remotes exist (e.g. `origin` pointing to a fork and `upstream` pointing to the canonical repo), prefer the canonical match.

| URL pattern | Profile |
|-------------|---------|
| Contains `rhdh-plugins` (but NOT `community-plugins`) | **rhdh-plugins** |
| Contains `community-plugins` | **community-plugins** |
| Neither matches | Ask the user: "Which repo are you targeting? (1) rhdh-plugins (2) community-plugins" |

## Profile: rhdh-plugins

| Field | Value |
|-------|-------|
| Upstream repo | `redhat-developer/rhdh-plugins` |
| npm scope | `@red-hat-developer-hub` |
| Changeset `fixed` group | `["@red-hat-developer-hub/*"]` |
| Changeset docs link | `https://github.com/redhat-developer/rhdh-plugins/blob/main/CONTRIBUTING.md#creating-changesets` |
| PR base branch | `main` |
| Commit signing | `-s` (Signed-off-by) |

### PR body template (rhdh-plugins)

```
## Description
<generated description — 2-4 sentences explaining what changed and why>

## Fixed
- <Jira link — ask the user, or leave as TODO>

## Checklist
- [x] A changeset describing the change and affected packages. ([more info](https://github.com/redhat-developer/rhdh-plugins/blob/main/CONTRIBUTING.md#creating-changesets))
- [ ] Added or Updated documentation
- [ ] Tests for new functionality and regression tests for bug fixes
- [ ] Screenshots attached (for UI changes)
```

## Profile: community-plugins

| Field | Value |
|-------|-------|
| Upstream repo | `backstage/community-plugins` |
| npm scope | `@backstage-community` |
| Changeset `fixed` group | `[]` (no fixed versioning) |
| Changeset docs link | `https://github.com/backstage/backstage/blob/master/CONTRIBUTING.md#creating-changesets` |
| PR base branch | `main` |
| Commit signing | `-s` (Signed-off-by — DCO required) |

### PR body template (community-plugins)

```
## Hey, I just made a Pull Request!

<generated description — 2-4 sentences explaining what changed and why>

#### Checklist

- [x] A changeset describing the change and affected packages. ([more info](https://github.com/backstage/backstage/blob/master/CONTRIBUTING.md#creating-changesets))
- [ ] Added or updated documentation
- [ ] Tests for new functionality and regression tests for bug fixes
- [ ] Screenshots attached (for UI changes)
- [x] All your commits have a `Signed-off-by` line in the message. ([more info](https://github.com/backstage/backstage/blob/master/CONTRIBUTING.md#developer-certificate-of-origin))
```
