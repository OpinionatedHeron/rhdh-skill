---
name: raise-pr
description: >
  Automate the full PR workflow for rhdh-plugins and community-plugins monorepos:
  detect workspace, build, generate changeset, commit, push, and create the GitHub PR.
  Auto-detects which repo you're in. Supports --a auto-approve mode to skip all
  approval gates. Accepts an optional Jira key or URL to link the PR to a Jira issue
  (adds Web Link, comment, and transitions to Review). Use when asked to "raise a PR",
  "create a PR", "submit a PR", "open a PR", "push my changes", "make a PR for this
  plugin", or "PR workflow". Also use when user says "raise pr", "/pr", or mentions
  creating a pull request in rhdh-plugins or community-plugins.
---

<essential_principles>

<principle name="scoped_dist_cleanup">
Pre-build cleanup uses `rm -rf plugins/*/dist packages/*/dist` scoped to the workspace directory. If permission errors occur (root-owned files from a prior Docker build), use a disposable Docker container to remove them — never use `sudo`. Never use `find -name dist` or any broad recursive search — that deletes `dist/` inside `node_modules` and breaks everything.
</principle>

<principle name="changesets_skip_packages">
Only plugins under `plugins/*` with published-source changes need changesets. Always ignore `packages/*` — those are private app/backend packages that are never published. Within each plugin, only include it if changes touch `src/` or other published paths (root `index.ts`, `config.d.ts`, `package.json`). Changes only in `dev/`, `tests/`, `__fixtures__/`, or storybook stories do not require a changeset.
</principle>

<principle name="baseline_diffing">
Capture `git status --porcelain` before builds as the baseline. After builds, only stage files that are new relative to that baseline. Pre-existing dirty files (local config overrides, dev fixtures) must never be staged.
</principle>

<principle name="step_echo_banners">
Before executing each numbered Step, echo a clearly visible banner to the terminal so the user can track progress:
```
echo "================ Step N — <Step title> ==========="
```
</principle>

</essential_principles>

## Mode: check for `--a` flag

Check if the user invoked this skill with `--a` (auto-approve mode).

- **`--a` present:** All approval gates (Steps 4, 8, and 9) are skipped — proceed automatically.
- **`--a` absent (default):** Approval gates require user confirmation before proceeding.

---

## Step 1 — Detect repo profile

Read `references/repo-profiles.md` and follow the detection logic. Run `git remote -v`, match the remote URLs, and load the matching profile (upstream repo, npm scope, PR body template, changeset docs link).

If no profile matches, ask the user which repo they are targeting before proceeding.

Store the profile values for use in Steps 5, 6, and 10.

---

## Step 1.5 — Resolve Jira context

Read `references/jira-input.md` for parsing rules and REST API patterns.

Resolve a Jira issue from one of these sources (in priority order):

1. **Caller context** — another skill (e.g., `bug-fix`) passes `jira_key`, `jira_url`, and `jira_summary` directly. Skip detection.
2. **Argument** — the user passed a Jira key or URL as an argument (e.g., `raise-pr RHDHBUGS-1934` or `raise-pr https://redhat.atlassian.net/browse/RHIDP-15252`).
3. **Branch name** — if the current branch contains a Jira key (e.g., `fix/RHDHBUGS-1934-keyboard-nav`), extract it.
4. **Prompt** — ask: "Jira issue key or URL? (enter to skip)".

**Parsing rules** (from `references/jira-input.md`):

- If input matches `(RHIDP|RHDHBUGS|RHDHPLAN|RHDHSUPP)-\d+` anywhere in the string, extract that as the key.
- If input contains `atlassian.net/browse/`, extract everything after `/browse/` as the key.
- Construct: `jira_url = https://redhat.atlassian.net/browse/<jira_key>`

**Fetch issue summary** (if key resolved and summary not provided by caller):

Use the Jira REST API per `references/jira-input.md` to fetch the issue summary. If auth is not configured or the fetch fails, store `jira_summary = null` and continue — the key and URL are still usable.

Store: `jira_key`, `jira_url`, `jira_summary` (all nullable). If no Jira reference was resolved, all three are null and Jira-specific behavior in later steps is skipped.

---

## Step 2 — Detect workspace(s) from staged changes

1. Run `git diff --cached --name-only` to list all staged files.
2. If no files are staged, stop: "No staged changes found. Stage your changes with `git add` before running this command."
3. Extract workspace names from staged file paths. The workspace is the second path segment (e.g., `workspaces/bulk-import/plugins/foo/src/index.ts` → workspace `bulk-import`, path `workspaces/bulk-import`).
4. If staged files span **multiple** workspaces, inform the user: "Changes detected in **N** workspace(s): `<list>`. Proceed? (Yes/No)". Wait for confirmation. If declined, stop.
5. Store the workspace names and paths for later steps.

---

## Step 3 — Capture baseline snapshot

Run `git status --porcelain` and save the full output as the **baseline snapshot**. This captures all files that were already dirty or untracked before any build commands run. Used in Step 7 to filter out pre-existing changes.

---

## Step 4 — Create branch (only if on `main`) [APPROVAL GATE]

1. Run `git branch --show-current`.
2. **If on `main`:**
   a. Analyze the staged diff (`git diff --cached`) to understand the changes.
   b. Generate a branch name:
      - **If `jira_key` is set:** `fix/<workspace>-<JIRA-KEY>-<short-slug>` (e.g., `fix/adoption-insights-RHDHBUGS-1934-keyboard-nav-dropdown`). This matches the existing repo convention and enables auto-linking in the Jira Development panel.
      - **If no Jira key:** `feat/<workspace>-<short-description>` (use `fix/` for bug fixes). For multiple workspaces, use a general description.
   c. **If NOT auto-approve:** present the proposed branch name and a one-line summary. Wait for approval. **If auto-approve:** proceed immediately.
   d. Run `git checkout -b <branch-name>`.
3. **If NOT on `main`:** skip branch creation. Inform the user: "Already on branch `<name>`, skipping branch creation."

---

## Step 5 — Build and validate each workspace

For **each** workspace from Step 2, run the following commands **sequentially** inside the workspace directory (e.g., `workspaces/bulk-import`). If any command fails, **stop immediately** and report the error with the failing command, workspace, and output.

### 5.0 — Pre-build cleanup

Remove stale `dist/` directories that may contain root-owned files from previous Docker or sudo builds:

```
rm -rf plugins/*/dist packages/*/dist
```

If this fails with a permission error (`EACCES`), use a disposable Docker container to remove them (avoids needing `sudo` on the host):

```
docker run --rm -v "$(pwd)":/workspace alpine sh -c "rm -rf /workspace/plugins/*/dist /workspace/packages/*/dist"
```

### 5.1–5.6 — Build pipeline

Run in order:

1. `yarn` — install dependencies
2. `yarn prettier:fix` — format code
3. `yarn tsc:full` — full TypeScript type check
4. `yarn build:all` — build all packages
5. `yarn test --watchAll=false` — run tests (disable Jest watch mode)
6. `yarn build:api-reports:only` — generate/update API reports

---

## Step 6 — Generate changeset per workspace

For **each** workspace from Step 2, generate a changeset programmatically. Use the npm scope from the detected repo profile (Step 1).

1. From the staged diff (`git diff --cached`), determine:
   - Which **plugins** under this workspace are affected (look at `plugins/*` only — **ignore `packages/*`**).
   - Within each plugin, only include it if changes touch published paths (`src/`, root `index.ts`, `config.d.ts`, `package.json`). Skip plugins with changes only in `dev/`, `tests/`, `__fixtures__/`, or stories.
   - Read each affected plugin's `package.json` for its npm package name.
   - Infer the semver bump: `patch` for fixes, `minor` for features, `major` for breaking changes.
   - **If no plugins have published-source changes, skip changeset generation for this workspace.**
2. Generate a short summary (1-2 sentences).
3. Generate a random changeset ID: `<adjective>-<noun>-<verb>` pattern, lowercase, 5-8 chars per word. Each workspace gets a unique ID.
4. Write the changeset file to `<workspace>/.changeset/<random-id>.md`:

```
---
'<package-name>': <bump-type>
---

<summary>
```

If multiple packages are affected, list each on its own YAML line.

**Do NOT run `yarn changeset` interactively.** Create files programmatically.

---

## Step 7 — Identify build-generated files

1. Run `git status --porcelain` for the **current snapshot**.
2. Compare against the **baseline snapshot** from Step 3.
3. Files only in the current snapshot are build-generated (created by Step 5 builds or Step 6 changesets).
4. Files already in the baseline are pre-existing — exclude them from staging.

---

## Step 8 — Stage build-generated files [APPROVAL GATE]

1. Present the filtered list of build-generated files from Step 7.
2. **If NOT auto-approve:** ask the user for approval before staging. **If auto-approve:** stage all automatically.
3. Run `git add` for each approved file.

---

## Step 9 — Commit [APPROVAL GATE]

1. Run `git diff --cached --stat` to review all staged changes.
2. Generate a commit message in conventional commit format: `<type>(<workspace>): <short description>` (e.g., `feat(bulk-import): add batch repository import support`).
3. **If `jira_url` is set**, append a `Fixes:` trailer in the commit body:

```
fix(adoption-insights): enable keyboard navigation in header date-range dropdown

Fixes: https://redhat.atlassian.net/browse/RHDHBUGS-1934
```

4. **If NOT auto-approve:** present the commit message and staged file summary. Wait for approval. **If auto-approve:** commit immediately.
5. Commit with the **`-s` flag** (Signed-off-by):

```
git commit -s -m "<subject>" -m "Fixes: <jira_url>"
```

If no `jira_url`, omit the second `-m` flag.

---

## Step 10 — Push and create PR

1. Push the branch:

```
git push -u origin HEAD
```

2. Generate a PR title from the commit subject line.
3. Build the PR body from the detected repo profile template (Step 1). The body has conditional sections:
   - **`## Fixed`** — include only if `jira_key` is set. Format: `- [<JIRA-KEY>](<jira_url>) — <jira_summary>`.
   - **`## UI before changes` / `## UI after changes`** — include only if `recordings` are provided in caller context. Embed the before/after GIF URLs.
   - **`pr_description_extra`** — if provided by caller context (e.g., root cause analysis from `bug-fix`), insert it after the generated description paragraph.
   - **`## Checklist`** — always present.
4. Create the PR using `gh pr create` with the repo-appropriate template. Use the upstream repo value for `--repo` and `main` for `--base`. Pass the body via HEREDOC:

```
gh pr create --repo <upstream-repo> --base main --title "<title>" --body "$(cat <<'EOF'
<assembled PR body>
EOF
)"
```

5. Capture and store the PR URL for Step 11.
6. Display the PR URL.

---

## Step 11 — Post-PR Jira updates

**Skip this step entirely if `jira_key` is null.**

Read `references/jira-input.md` for REST API patterns and auth setup.

### 11.1 — Add Web Link on Jira issue

Add the PR as a Web Link on the Jira issue using the REST API:

```
POST /rest/api/3/issue/<jira_key>/remotelink
Body: { "object": { "url": "<PR_URL>", "title": "PR: <PR_title>" } }
```

### 11.2 — Add comment

Add a comment documenting the PR submission:

```
acli jira workitem comment add --key <jira_key> --comment "PR submitted: <PR_URL>" --yes
```

If `acli` is not available, use the REST API:

```
POST /rest/api/3/issue/<jira_key>/comment
Body: { "body": { "type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "PR submitted: <PR_URL>"}]}] } }
```

### 11.3 — Transition to Review

Always attempt the transition — the user explicitly linked a Jira issue, so the intent is to move it to Review.

1. Query available transitions:

```
GET /rest/api/3/issue/<jira_key>/transitions
```

2. Find the transition whose `to.name` is `"Review"` (case-insensitive match).
3. **If found**: execute it:

```
POST /rest/api/3/issue/<jira_key>/transitions
Body: { "transition": { "id": "<transition_id>" } }
```

4. **If "Review" is not in the available transitions**: warn the user — "Issue `<jira_key>` is in status `<current_status>`. Cannot transition directly to Review. Available transitions: `<list>`. Move to the required status first."

---

## Gotchas

- **Fork workflows:** The user may have `origin` pointing to their fork and `upstream` to the canonical repo. Detection checks all remotes, not just `origin`. The `--repo` flag on `gh pr create` targets the canonical upstream regardless of which remote `origin` points to.
- **Multiple workspaces:** Each workspace gets its own build cycle (Step 5) and changeset (Step 6). The commit (Step 9) bundles everything into one commit. If the user prefers separate PRs per workspace, they should stage and run the skill once per workspace.
- **Changeset ID collisions:** Each workspace must get a unique random ID. If generating for multiple workspaces in one run, track used IDs and avoid duplicates.

## Caller Context (optional)

When another skill chains into `raise-pr`, it may provide a **caller context** with pre-resolved values. If present, these override the defaults — skip detection for any field that is already provided.

| Field | Type | Used in | Description |
|-------|------|---------|-------------|
| `jira_key` | string | Steps 1.5, 4, 9, 10, 11 | Pre-resolved Jira issue key (skip Step 1.5 detection) |
| `jira_url` | string | Steps 9, 10, 11 | Full Jira browse URL |
| `jira_summary` | string | Step 10 | Issue summary for the PR body `## Fixed` section |
| `recordings` | object | Step 10 | `{ before: "<path>", after: "<path>" }` — GIF paths for `## UI before/after changes` |
| `pr_description_extra` | string | Step 10 | Extra text inserted after the description (e.g., root cause analysis) |

Skills that chain into `raise-pr`:

- **`bug-fix`** — provides all five fields after reproducing and fixing a Jira bug with Playwright video recordings.

<reference_index>

## Reference Index

| Reference | Load when... |
|-----------|-------------|
| `references/repo-profiles.md` | Always — at the start of every invocation (Step 1) |
| `references/jira-input.md` | When resolving Jira context (Step 1.5) and performing post-PR Jira updates (Step 11) |

</reference_index>
