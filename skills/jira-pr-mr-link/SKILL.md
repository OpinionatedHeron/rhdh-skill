---
name: jira-pr-mr-link
description: >-
  Create GitHub PRs / GitLab MRs and link them to Jira (Web link, comment,
  optional missing-field defaults, open diffs) via create-pr-mr.js, or link an
  existing PR/MR with link-pr-mr.js / mark-merged. Title format `repo #N: <title>`.
  Use when linking existing PRs/MRs to Jira, marking merged Web links, replacing
  hand-rolled remotelink/comment steps, or creating+linking outside the
  rhdh-plugins / community-plugins raise-pr workflow. For the full monorepo PR
  flow (build, changeset, recordings), use raise-pr instead.
---

# Jira PR / MR create + Web links

Zero-token Node scripts for **GitHub and GitLab**: create the PR/MR, attach a
Jira remote Web link, post/update a structured comment, and optionally fill
empty issue fields.

Scripts live under this skill’s `scripts/` directory. Resolve that path from the
installed skill root (agents already have it when reading this file):

```bash
SKILL="$(cd "$(dirname "$0")" && pwd)"   # or absolute path to skills/jira-pr-mr-link
node "$SKILL/scripts/create-pr-mr.js" …
node "$SKILL/scripts/link-pr-mr.js" …
```

From `raise-pr`, call the linker with a relative path:

```bash
node "../jira-pr-mr-link/scripts/link-pr-mr.js" link …
```

## Preferred: one-shot create (`create-pr-mr.js`)

After the feature branch is committed:

```bash
node "$SKILL/scripts/create-pr-mr.js" \
  --issue RHIDP-12345 \
  --title 'fix: short summary' \
  --target main \
  --body "$(cat <<'EOF'
## Summary
- …

## Test plan
- [ ] …

Generated-by: cursor
EOF
)"
```

1. `git push -u origin HEAD` (unless `--no-push`)
2. Detects GitHub vs GitLab from `origin`
3. Runs `gh pr create` or `glab mr create`
4. Runs `link-pr-mr.js link` (unless `--no-link`). Missing Jira auth is an
   error; pass `--no-link` to skip linking.
5. Opens the diffs page (unless `--no-open`)

Flags: `--draft`, `--no-push`, `--no-link`, `--no-open`, `--no-defaults`,
`--no-comment`, `--no-jira-ref`, `--host github|gitlab`.

### Auth

Either works (same token either way):

1. `JIRA_API_TOKEN` + `login`/`server` in `~/.config/.jira/.config.yml`, or
2. `.jira-token` (`email:token`) next to `acli` — same as
   [`rhdh-jira` auth](../rhdh-jira/references/auth.md)

`create-pr-mr.js` appends `Ref: https://redhat.atlassian.net/browse/KEY` and
`Generated-by: cursor` to the **PR/MR body** when missing. It skips the Jira
`Ref:` line for `community-plugins` remotes (or when `--no-jira-ref` is set) so
that repo stays free of Jira browse URLs in git history / PR text.

## Link-only: `link-pr-mr.js`

When a PR/MR already exists:

```bash
node "$SKILL/scripts/link-pr-mr.js" link \
  --issue RHIDP-12345 \
  --url 'https://gitlab.cee.redhat.com/rhidp/example/-/merge_requests/817' \
  --title 'example #817: fix: short summary' \
  --host gitlab
```

- `--host` optional; inferred from URL when omitted.
- `--no-defaults` skips In Progress + metadata fills (Web link + comment still run).
- `--no-comment` skips the Jira comment.
- If a comment already mentions the PR/MR URL, it is **updated** in place
  (comments are paginated).

### RHDHPLAN → RHIDP auto-move

If the linked issue is an **Epic**, **Story**, or **Task** in **RHDHPLAN**,
`link` moves it to **RHIDP** (same issue type) via the Jira bulk-move API, then
continues Web link / defaults / comment on the **new** key. Features and other
RHDHPLAN types are left alone.

Stdout includes `move: …` and the post-move `issue:` key.

Comment shape (only **newly set** fields; omit `kept` values):

```
PR/MR:
* example #817: fix: short summary

Adjusted fields:
* Priority: Normal
* Status: In Progress
```

Visible link text matches the Web link title (`repo #N: <title>`).

### Mark merged

```bash
node "$SKILL/scripts/link-pr-mr.js" mark-merged --issue RHIDP-12345
```

Prefixes Web link titles with `[x] merged: `. Does not re-apply defaults/comment.
Stdout lists each title **and** its PR/MR URL (indented under the title).

`mark-merged` checks merge status via `gh` / `glab`. Failed checks print a
`warn:` line. For GitLab remotelinks it passes `--hostname` from the URL
(e.g. `gitlab.cee.redhat.com`), so CEE MRs resolve against the right host.
Prefer `glab` default `host: gitlab.cee.redhat.com` in
`~/.config/glab-cli/config.yml` for day-to-day CEE work.

When summarizing to the user, use markdown links (`[title](url)`).

## Title format (for `link --title`)

```
<repo-short-name> #<id>: <full PR/MR title>
```

Merged: `[x] merged: <repo-short-name> #<id>: <full PR/MR title>`

## Defaults `link` applies (only if empty)

**No built-in team/assignee values.** First run with defaults enabled requires a
config file (or env/CLI). Missing keys error **when applying defaults** (Web link
+ comment still succeed with `--no-defaults`).

```bash
mkdir -p ~/.config/jira-pr-mr-link
cp "$SKILL/config.example.json" ~/.config/jira-pr-mr-link/config.json
# edit assigneeEmail, teamId, teamName, boardId, …
```

Also accepted: `$JIRA_PR_MR_CONFIG` or `$SKILL/config.local.json`
(keep personal email out of the repo).

Precedence: **CLI > env > config file > Jira CLI hints** (`login` / `board.id`
from `~/.config/.jira/.config.yml` may fill assignee/board only).

| Field | Required when applying defaults |
|-------|----------------------------------|
| `assigneeEmail` | yes (or Jira `login` email) |
| `teamId` / `teamName` | yes, or set either to `NONE` to skip team **and** sprint |
| `boardId` | yes (or jira CLI `board.id`), unless team/sprint skipped via `NONE` |
| `storyPoints` | yes |
| `priorityName` | yes (only fills when priority is empty) |
| `storyPointsField` | yes |
| `teamField` / `sprintField` | yes, unless team/sprint skipped via `NONE` |
| Status | → **In Progress** unless already In Progress / Review / Closed |

Skip all defaults: `--no-defaults` or `JIRA_PR_MR_APPLY_DEFAULTS=0`.

Skip only team + sprint (still set points / assignee / priority / In Progress):

```json
"teamName": "NONE",
"teamId": "NONE"
```

## Relationship to `raise-pr`

[`raise-pr`](../raise-pr/SKILL.md) owns the **rhdh-plugins** /
**community-plugins** monorepo PR flow (build, changesets, recordings). This
skill owns the Jira Web link + comment (and optional defaults) for any repo.

After `raise-pr` creates a PR, Step 11 calls `link-pr-mr.js` with `--no-defaults`
so `raise-pr` can still transition the issue to **Review** (see
[references/raise-pr-integration.md](references/raise-pr-integration.md)).

## Agent checklist

1. Resolve Jira key. Ask if missing (unless user skipped Jira).
2. Commit on a feature branch. Put the Jira browse URL and `Generated-by: cursor`
   in the **PR/MR body** (`create-pr-mr.js` appends them when missing; skips
   `Ref:` for community-plugins).
3. Run **`create-pr-mr.js`** once. Report `url:` / `diffs:` / `browserOpened:` /
   `jiraLink:` from its stdout (`browserOpened: true` or `--no-open` means the
   open step is already done).
4. Fallback: raw create → run `link-pr-mr.js`, then open diffs yourself once.
5. For mark-merged: `link-pr-mr.js mark-merged --issue KEY`.
6. In user-facing summaries, link PR/MRs as `[title](url)`.
