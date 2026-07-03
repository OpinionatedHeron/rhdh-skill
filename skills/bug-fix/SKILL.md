---
name: bug-fix
description: >
  Reproduce, diagnose, fix, and PR RHDH plugin bugs from Jira tickets using
  Playwright e2e tests with before/after screen recordings. Accepts a Jira key
  (RHDHBUGS-1934), Jira URL (redhat.atlassian.net/browse/...), or a request to
  "fix this bug", "reproduce and fix", "/bug-fix". Chains into raise-pr for the
  full PR lifecycle including post-PR Jira updates (Web Link, comment, transition
  to Review).
---

<essential_principles>

<principle name="repro_test_is_temporary">
The reproduction test (`_repro-<KEY>.test.ts`) is a diagnostic tool, not a deliverable. It is deleted before staging. It must never appear in the PR.
</principle>

<principle name="runtime_discovery">
Do not hardcode workspace internals. Discover each workspace's e2e infrastructure at runtime by reading its `playwright.config.ts`, `e2e-tests/utils/`, and `plugins/*/src/translations/ref.ts`. The `references/workspace-map.md` maps Jira components to workspace directories, but everything else is discovered dynamically.
</principle>

<principle name="video_evidence">
Every bug fix PR must include before/after visual evidence. Playwright video recording captures the bug in action (before) and the fix working (after). These are converted to GIFs and embedded in the PR description.
</principle>

<principle name="step_echo_banners">
Before executing each numbered Step, echo a clearly visible banner to the terminal so the user can track progress:
```
echo "================ Step N — <Step title> ==========="
```
</principle>

<principle name="preflight_port_cleanup">
Before running any Playwright test, check whether the dev-server port (from `playwright.config.ts`) is already in use. If it is, kill the process occupying it:
```
lsof -ti:<PORT> | xargs kill -9 2>/dev/null || true
```
A stale dev server from a prior session will cause the test to connect to the wrong app and time out.
</principle>

</essential_principles>

## Prerequisites

- Working checkout of `rhdh-plugins` (or `community-plugins`)
- `yarn` available on PATH
- `ffmpeg` available on PATH (for video conversion; fall back to raw `.webm` if absent)
- Jira auth configured (`.jira-token` next to `acli` binary, or Jira MCP in Cursor)

---

## Step 1 — Fetch Jira issue and parse details

Read `references/workspace-map.md` for the Jira component-to-workspace mapping.

1. Parse the Jira reference from the user's input. Follow the parsing rules in `raise-pr/references/jira-input.md`:
   - Bare key: `RHDHBUGS-1934`
   - Browse URL: `https://redhat.atlassian.net/browse/RHDHBUGS-1934`
   - URL without scheme: `redhat.atlassian.net/browse/RHIDP-15252`
2. Fetch the full issue details using the Jira REST API or MCP (`read_jira_issue`):
   - Summary, description, steps to reproduce
   - Component field (maps to workspace)
   - Status (for post-PR transition)
   - Attachments/screenshots (visual reference for reproduction)
3. Store: `jira_key`, `jira_url`, `jira_summary`, `jira_description`, `jira_component`, `jira_status`

**If the description has no clear steps to reproduce**: ask the user to provide reproduction steps before proceeding.

---

## Step 2 — Identify workspace and discover e2e infrastructure

1. Map the Jira **Component** field to a workspace directory using `references/workspace-map.md`.
   - If no component is set or the component is unknown: ask the user which workspace to target.
2. Navigate to the workspace: `cd workspaces/<workspace-dir>`
3. **Discover e2e infrastructure dynamically**:
   - Read `playwright.config.ts` for port configuration, locale list, start commands, and `APP_MODE` support.
   - Scan `e2e-tests/utils/` to discover available helper functions (translations, navigation, API mocking, accessibility).
   - Read `plugins/*/src/translations/ref.ts` for translation key structure (used for i18n-safe selectors).
   - Read `plugins/*/src/components/` to build a component-to-source-file map.
4. Run `yarn install` if `node_modules` is missing or stale.

**If the workspace has no `playwright.config.ts`**: fall back to a screenshot-only approach — skip video recording and use DOM assertions or manual screenshots instead.

Read `references/e2e-patterns.md` for shared Playwright patterns across all rhdh-plugins workspaces.

---

## Step 3 — Write reproduction test with video recording

Read `references/e2e-patterns.md` for test patterns and `references/video-recording.md` for video configuration.

1. Create a temporary test file: `e2e-tests/_repro-<JIRA-KEY>.test.ts`
   - The `_` prefix signals this file is temporary and should not be committed.
2. The test must:
   - Import workspace-specific helpers discovered in Step 2.
   - Use i18n-safe selectors (via translation keys) where available.
   - Configure video recording per-test:
     ```typescript
     test.use({
       video: { mode: 'on', size: { width: 1280, height: 720 } },
     });
     ```
   - Encode the "steps to reproduce" from the Jira description as Playwright actions.
   - Assert the **expected** behavior (the assertion should fail when the bug is present).
3. **Pre-flight: kill stale dev server** — before running the test, ensure the dev-server port (read from `playwright.config.ts` `webServer.url`) is free:
   ```
   lsof -ti:<PORT> | xargs kill -9 2>/dev/null || true
   ```
4. Run the test against the `en` locale in legacy mode:
   ```
   APP_MODE=legacy npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en
   ```
5. The test should **fail** — confirming the bug is reproduced.

**If the test passes** (bug not reproduced): re-read the Jira description, adjust the test, and retry. If still not reproducible after 2 attempts, report findings and ask the user for guidance.

---

## Step 4 — Capture "before" recording

1. After the failed test run (Step 3), locate the video file in `test-results/`.
   - Playwright saves videos at `test-results/<test-title>/video.webm`.
2. Copy the video to a stable path:
   ```
   mkdir -p e2e-tests/_repro-artifacts
   cp test-results/*/video.webm e2e-tests/_repro-artifacts/before-fix.webm
   ```
3. Store the path for later conversion (Step 7).

---

## Step 5 — Diagnose and fix

1. **Diagnose**: trace from the failing Playwright selector back to the source:
   - Identify which React component renders the UI element under test.
   - Read the component source code (`plugins/*/src/components/`).
   - Identify the root cause (e.g., MUI prop misconfiguration, missing state update, CSS issue, accessibility gap, i18n key mismatch).
2. **Apply the fix** in the source code.
3. **Validate**:
   - `yarn tsc:full` — type check passes.
   - `yarn test --watchAll=false` — unit tests pass.

**Confidence gates** — ask the user before proceeding if:
- Multiple possible root causes exist — present options and let the user choose.
- The fix touches more than 3 files — show the plan and get approval.
- The fix changes API surface or public types — this may need a minor version bump.

---

## Step 6 — Capture "after" recording

1. Re-run the reproduction test:
   ```
   APP_MODE=legacy npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en
   ```
2. The test should **pass** — confirming the fix works.
3. Copy the video:
   ```
   cp test-results/*/video.webm e2e-tests/_repro-artifacts/after-fix.webm
   ```
4. Optionally run in NFS mode as well to check for mode-specific regressions:
   ```
   APP_MODE=nfs npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en
   ```

**If the test still fails after the fix**: re-examine the diagnosis and iterate.

---

## Step 7 — Convert videos for PR embedding

Read `references/video-recording.md` for conversion details.

1. Check if `ffmpeg` is available on PATH.
2. **If available**: convert `.webm` to `.gif`:
   ```
   ffmpeg -i e2e-tests/_repro-artifacts/before-fix.webm -vf "fps=10,scale=800:-1" -loop 0 e2e-tests/_repro-artifacts/before-fix.gif
   ffmpeg -i e2e-tests/_repro-artifacts/after-fix.webm -vf "fps=10,scale=800:-1" -loop 0 e2e-tests/_repro-artifacts/after-fix.gif
   ```
3. **If `ffmpeg` is not available**: keep the `.webm` files and note that they will be uploaded as PR comment attachments instead of inline GIFs.

---

## Step 8 — Clean up and create PR

### 8.1 — Delete temporary files

Remove the reproduction test and artifacts — these must not appear in the PR:

```
rm e2e-tests/_repro-<KEY>.test.ts
rm -rf test-results/
```

Keep `e2e-tests/_repro-artifacts/` temporarily (needed for PR image upload).

### 8.2 — Stage fix files

Stage only the code fix (not the repro test or artifacts):

```
git add <fixed-source-files>
```

### 8.3 — Chain into raise-pr

Invoke `raise-pr --a` with the following caller context:

| Field | Value |
|-------|-------|
| `jira_key` | The resolved Jira key from Step 1 |
| `jira_url` | `https://redhat.atlassian.net/browse/<jira_key>` |
| `jira_summary` | Issue summary from Step 1 |
| `recordings` | `{ before: "e2e-tests/_repro-artifacts/before-fix.gif", after: "e2e-tests/_repro-artifacts/after-fix.gif" }` |
| `pr_description_extra` | `### Root cause\n<diagnosis from Step 5>` |

`raise-pr` handles: repo detection, build, changeset, commit (with `Fixes:` trailer), push, PR creation (with `## UI before/after changes`), and post-PR Jira updates (Web Link, comment, transition to Review).

### 8.4 — Final cleanup

After the PR is created, delete the artifacts directory:

```
rm -rf e2e-tests/_repro-artifacts/
```

---

## When NOT to Use

- **Backend-only bugs** — if the bug has no UI component, there is nothing to video-record. Use standard debugging and fix workflows instead.
- **Bugs requiring live backend data** — if reproduction depends on real API responses that cannot be mocked via the workspace's e2e test infrastructure.
- **Cross-workspace bugs** — if the fix requires changes across multiple workspaces, handle each workspace separately or use `raise-pr` directly.
- **Non-RHDH Jira projects** — this skill's workspace mapping is specific to `rhdh-plugins` workspaces and RHDH Jira projects (RHIDP, RHDHBUGS, RHDHPLAN, RHDHSUPP).

<reference_index>

## Reference Index

| Reference | Load when... |
|-----------|-------------|
| `references/workspace-map.md` | Always — at the start of every invocation (Step 1-2) |
| `references/e2e-patterns.md` | When writing the reproduction test (Step 3) |
| `references/video-recording.md` | When configuring video capture (Step 3) and converting videos (Step 7) |
| `raise-pr/references/jira-input.md` | When parsing Jira keys/URLs (Step 1) — shared with raise-pr |
| `raise-pr/references/repo-profiles.md` | Loaded by raise-pr during Step 8.3 chain |

</reference_index>
