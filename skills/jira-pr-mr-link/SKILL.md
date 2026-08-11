---
name: jira-pr-mr-link
description: >-
  Create GitHub PRs / GitLab MRs and link them to Jira (Web link, comment,
  optional missing-field defaults, open diffs) via create-pr-mr.js, or link an
  existing PR/MR with link-pr-mr.js / mark-merged. Title format `repo #N: <title>`.
  Use when opening a PR/MR that cites a Jira key, linking existing PRs/MRs to
  Jira, marking merged Web links, or replacing hand-rolled remotelink/comment
  steps. Complements raise-pr (plugin monorepos) without folding into it.
---

# Jira PR / MR create + Web links

Zero-token Node scripts for **GitHub and GitLab**: create the PR/MR, attach a
Jira remote Web link, post/update a structured comment, and optionally fill
empty issue fields. Prefer these scripts over hand-rolled `gh`/`glab` + REST/MCP
for the Jira side.

Scripts live under this skill’s `scripts/` directory. Resolve that path from the
installed skill root (agents already have it when reading this file).

```bash
SKILL="$(dirname "$0")"   # or absolute path to skills/jira-pr-mr-link
node "$SKILL/scripts/create-pr-mr.js" …
node "$SKILL/scripts/link-pr-mr.js" …
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
4. Runs `link-pr-mr.js link` (unless `--no-link`)
5. Opens the diffs page (unless `--no-open`). Agents must **not** open it again
   after this script succeeds — that produces a duplicate browser tab.

Flags: `--draft`, `--no-push`, `--no-link`, `--no-open`, `--host github|gitlab`.

Requires `JIRA_API_TOKEN` + `~/.config/.jira/.config.yml` for linking.
Appends `Ref: https://redhat.atlassian.net/browse/KEY` and `Generated-by: cursor`
to the body when missing.

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
- `--no-defaults` skips In Progress + metadata fills.
- `--no-comment` skips the Jira comment.
- If a comment already mentions the PR/MR URL, it is **updated** in place.

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
config file (or env/CLI). Missing keys error with copy/paste setup instructions.

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
2. Commit on a feature branch (Jira browse URL + `Generated-by: cursor` in the body).
3. Run **`create-pr-mr.js`** once. Report `url:` / `diffs:` and the linker summary.
4. Do **not** also hand-roll `gh`/`glab` create + MCP comments for the same PR/MR.
5. **Do not open the diffs twice.** `create-pr-mr.js` already opens the browser
   (look for `[INFO] opened diffs:` or `diffs:` in stdout). Do **not** also run
   `xdg-open` / `open` / equivalent unless you used raw `gh`/`glab` (or passed
   `--no-open`).
6. Fallback: raw create → run `link-pr-mr.js`, then open diffs yourself once.
7. For mark-merged: `link-pr-mr.js mark-merged --issue KEY`. Report results with
   markdown links (`[title](url)`), never bare `repo #N`. Prefer script stdout
   URL lines / remotelink URLs when present.
8. **Always link PR/MRs in user-facing summaries** (create, link, or
   mark-merged). Never list title-only `repo #N` text.
