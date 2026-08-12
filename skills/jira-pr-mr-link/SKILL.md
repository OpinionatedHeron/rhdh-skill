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
empty issue fields. Prefer these scripts over hand-rolled `gh`/`glab` + REST/MCP
for the Jira side.

Scripts live under this skill’s `scripts/` directory. Resolve that path from the
installed skill root (agents already have it when reading this file):

```bash
SKILL="$(cd "$(dirname "$0")" && pwd)"   # or absolute path to skills/jira-pr-mr-link
node "$SKILL/scripts/create-pr-mr.js" …
node "$SKILL/scripts/link-pr-mr.js" …
```

From `raise-pr`, use the relative skill path (do **not** invent `$JIRA_PR_MR_LINK_SKILL`):

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
4. Runs `link-pr-mr.js link` (unless `--no-link`) — **fails closed** if Jira auth
   is missing (pass `--no-link` to skip)
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
  (comments are paginated so busy tickets still match).

### RHDHPLAN → RHIDP auto-move

If the linked issue is an **Epic**, **Story**, or **Task** in **RHDHPLAN**,
`link` moves it to **RHIDP** (same issue type) via the Jira bulk-move API, then
continues Web link / defaults / comment on the **new** key. Features and other
RHDHPLAN types are left alone.

Stdout includes `move: …` and the post-move `issue:` key.

Comment shape (only **newly set** fields — never lists `kept` values):

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
`warn:` line (do not treat silent failures as “still open”). For GitLab
remotelinks it passes `--hostname` from the URL (e.g. `gitlab.cee.redhat.com`),
so CEE MRs are not queried against `gitlab.com`. Prefer `glab` default
`host: gitlab.cee.redhat.com` in `~/.config/glab-cli/config.yml` for day-to-day
CEE work.

When summarizing updated/left-open items to the user, always use markdown links
(`[title](url)`), never bare `repo #N` text.

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

Also accepted: `$JIRA_PR_MR_CONFIG`, legacy `~/.config/jira-pr-mr-web-link/config.json`,
or `$SKILL/config.local.json` (do not commit personal email).

Precedence: **CLI > env > config file > Jira CLI hints** (`login` / `board.id`
from `~/.config/.jira/.config.yml` may fill assignee/board only).

| Field | Required when applying defaults |
|-------|----------------------------------|
| `assigneeEmail` | yes (or Jira `login` email) |
| `teamId` / `teamName` | yes |
| `boardId` | yes (or jira CLI `board.id`) |
| `storyPoints` | yes |
| `priorityName` | yes (never overwrites an existing priority) |
| `storyPointsField` / `teamField` / `sprintField` | yes (examples in `config.example.json`) |
| Status | → **In Progress** unless already In Progress / Review / Closed |

Skip all defaults: `--no-defaults` or `JIRA_PR_MR_APPLY_DEFAULTS=0`.

## Relationship to `raise-pr`

[`raise-pr`](../raise-pr/SKILL.md) stays scoped to **rhdh-plugins** /
**community-plugins** (build, changesets, recordings). Do **not** fold this
skill into it.

For the Jira side after `raise-pr` creates a PR, prefer calling `link-pr-mr.js`
instead of hand-rolling remotelink/comment (see
[references/raise-pr-integration.md](references/raise-pr-integration.md)). Use
`--no-defaults` when `raise-pr` will transition the issue to **Review** itself.

## Agent checklist

1. Resolve Jira key. Ask if missing (unless user skipped Jira).
2. Commit on a feature branch. Put the Jira browse URL and `Generated-by: cursor`
   in the **PR/MR body** (`create-pr-mr.js` appends them when missing; skips
   `Ref:` for community-plugins).
3. Run **`create-pr-mr.js`** once.
4. Done when: `create-pr-mr.js` ran once, and you reported `url:` / `diffs:` /
   `browserOpened:` / `jiraLink:` from its stdout.
5. Treat `browserOpened: true` (or `--no-open`) as the open step already handled;
   do not start a second create or browser open for the same PR/MR.
6. Fallback: raw create → run `link-pr-mr.js`, then open diffs yourself once.
7. For mark-merged: `link-pr-mr.js mark-merged --issue KEY`. Report results with
   markdown links (`[title](url)`), never bare `repo #N`. Prefer script stdout
   URL lines / remotelink URLs when present.
8. **Always link PR/MRs in user-facing summaries** (create, link, or
   mark-merged). Never list title-only `repo #N` text.
