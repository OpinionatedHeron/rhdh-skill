---
name: bug-fix
description: >
  Reproduce, diagnose, fix, and PR RHDH plugin bugs from Jira tickets using
  Playwright e2e tests with before/after screen recordings. Accepts a Jira key
  (RHDHBUGS-1934), Jira URL (redhat.atlassian.net/browse/...), or a request to
  "fix this bug", "reproduce and fix", "/bug-fix".   Chains into raise-pr for the
  full PR lifecycle including post-PR Jira comment.
---

<essential_principles>

<principle name="skill_entry_banner">
As the very first action when the skill is invoked, echo a skill entry banner to the terminal:
```
echo "================ Using Bug Fix Skill ==========="
```
This must happen before any other work (reading references, MCP calls, etc.).
</principle>

<principle name="repro_test_is_temporary">
The reproduction test (`_repro-<KEY>.test.ts`) is a diagnostic tool, not a deliverable. It is deleted before staging. It must never appear in the PR.
</principle>

<principle name="runtime_discovery">
Do not hardcode workspace internals. Discover each workspace's e2e infrastructure at runtime by reading its `playwright.config.ts`, `e2e-tests/utils/`, and `plugins/*/src/translations/ref.ts`. The `references/workspace-map.md` maps Jira components to workspace directories, but everything else is discovered dynamically.
</principle>

<principle name="video_evidence">
Every bug fix PR with a UI change MUST include before/after screen recordings. This is NON-NEGOTIABLE and cannot be skipped, deferred, or worked around. The recordings prove the bug existed and the fix resolves it.

Enforcement rules:
- The reproduction test MUST be written and run BEFORE any fix is applied (Steps 3-4 happen before Step 5). Violating this order means there is no "before" state to record.
- The repro test MUST create its own browser context with `recordVideo` — NEVER use workspace bootstrap helpers (e.g., `bootstrapLightspeedE2ePage`) as they do not enable video recording.
- If video files are not present in `e2e-tests/_repro-artifacts/` at Step 8, STOP and go back to capture them. Do NOT proceed to PR creation without recordings.
- If the Playwright `context.close()` call is missing, the video file will be incomplete — always close the context.
</principle>

<principle name="fix_after_repro">
NEVER apply the code fix before Steps 3 and 4 are complete. The correct order is:
1. Write repro test (Step 3)
2. Run repro test — it must FAIL (bug confirmed)
3. Capture "before" video (Step 4)
4. ONLY THEN apply the fix (Step 5)

If you find yourself wanting to fix first and test after, STOP — you are violating the step order. The "before" recording cannot be captured retroactively.
</principle>

<principle name="step_echo_banners">
Before executing each numbered Step, echo a clearly visible banner to the terminal so the user can track progress — even if the step's actual work is done via MCP tools or file reads rather than shell commands:
```
echo "================ Step N — <Step title> ==========="
```
This applies to ALL steps including Step 1. Run the echo command in a Shell tool call before doing anything else for that step.
</principle>

<principle name="preflight_port_cleanup">
Before running any Playwright test, check whether the dev-server port (from `playwright.config.ts`) is already in use. If it is, kill the process occupying it:
```
lsof -ti:<PORT> | xargs kill -9 2>/dev/null || true
```
A stale dev server from a prior session will cause the test to connect to the wrong app and time out.
</principle>

<principle name="preflight_system_limits">
Before running any Playwright test, ensure the system file descriptor limit is raised and always use `required_permissions: ["all"]` on the shell command to avoid sandbox restrictions on browser launch:
```
ulimit -n 65536 2>/dev/null || true
```
Without this, webpack's file watcher (Watchpack) may hit `EMFILE: too many open files` and crash Chrome/Chromium.
</principle>

</essential_principles>

## Prerequisites

- **`gh` CLI** — GitHub CLI must be installed and authenticated (`gh auth status` should show logged in). Install: https://cli.github.com/
- **Jira MCP** — The Atlassian Rovo MCP server must be configured in Cursor for Jira comment updates. Setup guide: https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/
  - If not configured, the skill will skip Jira updates and log a warning.
- Working checkout of `rhdh-plugins` (or `community-plugins`)
- `yarn` available on PATH
- `ffmpeg` available on PATH (for video conversion; fall back to raw `.webm` if absent)

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
   - Import workspace-specific helpers discovered in Step 2 **only for navigation/setup** (e.g., API mocking, translations).
   - Use i18n-safe selectors (via translation keys) where available.
   - **Always create its own browser context with video recording** — do NOT rely on workspace bootstrap helpers for the context, as they may not enable video. Use the `browser` fixture directly:
     ```typescript
     test('repro', async ({ browser }) => {
       const context = await browser.newContext({
         recordVideo: { dir: 'test-results/', size: { width: 1280, height: 720 } },
       });
       const page = await context.newPage();
       
       // ... test steps using page ...
       
       await context.close(); // finalizes the video file
     });
     ```
     This guarantees video recording regardless of how the workspace's own e2e infrastructure manages contexts.
   - **CRITICAL**: Do NOT use workspace-provided bootstrap/setup functions (like `bootstrapLightspeedE2ePage`, `setupE2eTest`, etc.) as the browser context source. These helpers create contexts WITHOUT video recording. You MUST call `browser.newContext({ recordVideo: ... })` yourself and then replicate only the mock setup from those helpers (API mocking, route handlers) on your custom page. Copy the mock calls — not the context creation.
   - Encode the "steps to reproduce" from the Jira description as Playwright actions.
   - Assert the **expected** behavior (the assertion should fail when the bug is present).
3. **Pre-flight: kill stale dev server** — before running the test, ensure the dev-server port (read from `playwright.config.ts` `webServer.url`) is free:
   ```
   lsof -ti:<PORT> | xargs kill -9 2>/dev/null || true
   ```
4. Run the test against the `en` locale in legacy mode. **Always** prefix with `ulimit -n 65536` and use `required_permissions: ["all"]` on the Shell tool call:
   ```
   ulimit -n 65536 && APP_MODE=legacy npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en
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

**If no video file is found in `test-results/`**: the test likely used a bootstrap helper instead of a custom `recordVideo` context. Rewrite the test to use `browser.newContext({ recordVideo: ... })` directly, then re-run.

---

## Step 5 — Diagnose and fix

1. **Capture diagnostic context** from the failing state (before applying any fix). Re-use the reproduction test or run a lightweight Playwright script to gather:

   a. **Screenshot** of the buggy UI state:
      ```typescript
      await page.screenshot({ path: 'e2e-tests/_repro-artifacts/bug-state.png', fullPage: true });
      ```
   b. **DOM snapshot** of the target element:
      ```typescript
      const targetEl = page.locator('<selector-under-test>');
      const domSnapshot = await targetEl.evaluate(el => el.outerHTML);
      ```
   c. **Computed styles** of the target element (capture properties relevant to the bug):
      ```typescript
      const styles = await targetEl.evaluate(el => {
        const cs = window.getComputedStyle(el);
        return { display: cs.display, overflow: cs.overflow, scrollbarWidth: cs.scrollbarWidth };
      });
      ```

   Use the screenshot (read it as an image), DOM structure, and computed styles to identify the exact root cause before modifying any source files. This provides concrete runtime evidence rather than guessing from source alone.

2. **Diagnose**: trace from the failing Playwright selector back to the source:
   - Identify which React component renders the UI element under test.
   - Read the component source code (`plugins/*/src/components/`).
   - Cross-reference the captured DOM/styles with the component's render logic to pinpoint the root cause (e.g., MUI prop misconfiguration, missing state update, CSS issue, accessibility gap, i18n key mismatch).
3. **Apply the fix** in the source code.
4. **Validate**:
   - `yarn tsc:full` — type check passes.
   - `yarn test --watchAll=false` — unit tests pass.

**Confidence gates** — ask the user before proceeding if:
- Multiple possible root causes exist — present options and let the user choose.
- The fix touches more than 3 files — show the plan and get approval.
- The fix changes API surface or public types — this may need a minor version bump.

---

## Step 6 — Capture "after" recording

1. Re-run the reproduction test (with `ulimit` and `required_permissions: ["all"]`):
   ```
   ulimit -n 65536 && APP_MODE=legacy npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en
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

### 8.0 — Validate recordings exist [HARD GATE]

Before proceeding with cleanup or PR creation, verify both recording files exist:

```
test -f e2e-tests/_repro-artifacts/before-fix.webm || { echo "ERROR: before-fix.webm missing — go back to Step 4"; exit 1; }
test -f e2e-tests/_repro-artifacts/after-fix.webm || { echo "ERROR: after-fix.webm missing — go back to Step 6"; exit 1; }
```

If either file is missing, DO NOT proceed. Return to the relevant step (4 or 6) and capture the recording. This gate ensures the PR will always have visual evidence.

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
| `test_plan` | Auto-generated markdown checklist (see below) |

**Generating the `test_plan`:**

Build a markdown checklist of verification steps for the reviewer. Derive them from:
1. **Jira steps-to-reproduce** — convert each step into a positive verification action (e.g., "Click Help menu" becomes "- [ ] Open the Help menu").
2. **Expected behavior after fix** — add steps verifying the fix works (e.g., "- [ ] Verify scrollbar appears on hover").
3. **Regression check** — add at least one step confirming nothing else broke (e.g., "- [ ] Verify other menus/display modes are unchanged").

Example output:
```
- [ ] Open the dropdown menu with many items
- [ ] Verify scrollbar is hidden by default
- [ ] Hover over the menu content area
- [ ] Verify scrollbar becomes visible on hover
- [ ] Verify other dropdown menus are unaffected
```

`raise-pr` handles: repo detection, build, changeset, commit (with `Fixes:` trailer), push, PR creation (with `## UI before/after changes` and `## Test Plan`), and post-PR Jira comment.

> `raise-pr` uploads the GIF files to the branch via GitHub Contents API and embeds the resulting `raw.githubusercontent.com` URLs directly in the PR description. No manual image upload or separate PR comment is needed.

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
