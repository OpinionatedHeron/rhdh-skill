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

The template has conditional sections. Include or omit them based on the resolved Jira context and caller context from Step 1.5.

```
## Description
<generated description — 2-4 sentences explaining what changed and why>

<pr_description_extra — if provided by caller context, insert here (e.g., root cause analysis)>

## Fixed                              ← include only if jira_key is set
- [<JIRA-KEY>](<jira_url>) — <jira_summary>

## UI before changes                  ← include only if recordings provided by caller
![Before fix](<before-gif-url>)       ← raw.githubusercontent.com URL from Step 10.2

## UI after changes                   ← include only if recordings provided by caller
![After fix](<after-gif-url>)         ← raw.githubusercontent.com URL from Step 10.2

## Test Plan                           ← include only if test_plan provided by caller
<test_plan — markdown checklist of verification steps>

## Checklist
- [x] A changeset describing the change and affected packages. ([more info](https://github.com/redhat-developer/rhdh-plugins/blob/main/CONTRIBUTING.md#creating-changesets))
- [ ] Added or Updated documentation
- [ ] Tests for new functionality and regression tests for bug fixes
- [ ] Screenshots attached (for UI changes)

## Note                                ← include only if recordings AND jira_key are both provided
> This bug fix was identified and implemented using the [bug-fix](https://github.com/redhat-developer/rhdh-plugins/blob/main/.agents/skills/bug-fix/SKILL.md) and [raise-pr](https://github.com/redhat-developer/rhdh-plugins/blob/main/.agents/skills/raise-pr/SKILL.md) agent skills. Please verify the fix thoroughly before merging.
```

**When no Jira key is set**: omit `## Fixed` entirely.
**When no recordings provided**: omit both `## UI before changes` and `## UI after changes`.
**When no test_plan provided**: omit `## Test Plan` entirely.
**When recordings AND jira_key are NOT both present**: omit `## Note` entirely.
**When all optional sections are absent**: the template reduces to `## Description` + `## Checklist` (the minimal form).

**Note on image URLs**: The `<before-gif-url>` and `<after-gif-url>` placeholders are replaced with real `raw.githubusercontent.com` URLs after uploading the GIF files to the branch via GitHub Contents API (Step 10.2 in the main skill). These are NOT local file paths.

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
