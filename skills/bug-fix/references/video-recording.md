# Video Recording: Playwright Capture & Conversion

How to capture before/after screen recordings for bug fix PRs. Reference this in Steps 3, 4, 6, and 7.

## Playwright Video Configuration

The reproduction test must **always create its own browser context** with `recordVideo` to guarantee video capture regardless of how the workspace's e2e infrastructure manages contexts:

```typescript
test('repro', async ({ browser }) => {
  const context = await browser.newContext({
    recordVideo: { dir: 'test-results/', size: { width: 1280, height: 720 } },
  });
  const page = await context.newPage();

  // ... test steps ...

  await context.close(); // finalizes the video file
});
```

- **`recordVideo.dir`** — directory where Playwright saves the `.webm` file.
- **`size`** — 1280x720 gives good quality at reasonable file size. Matches most laptop viewports.
- **`context.close()`** — MUST be called to finalize the video. Without it the file may be incomplete.

All rhdh-plugins workspaces use `@playwright/test` >= 1.60.0, which supports this config.

### Why not `test.use({ video: ... })`?

`test.use()` only applies to Playwright's auto-created contexts. Many rhdh-plugins workspaces (e.g., `lightspeed`) manually create contexts in `beforeAll` helpers, which bypasses `test.use()` entirely. By always creating our own context with `recordVideo`, we avoid this pitfall.

## Where Videos Land

Playwright saves videos to the `test-results/` directory inside the workspace:

```
workspaces/<workspace>/test-results/
└── <test-describe-title>-<test-title>-<browser>/
    └── video.webm
```

The exact path depends on the test title. After running, find the video:

```bash
find test-results -name "video.webm" -type f
```

## Capturing Before/After Videos

### Before fix (Step 4)

After the reproduction test **fails** (bug is present):

```bash
mkdir -p e2e-tests/_repro-artifacts
cp test-results/*/video.webm e2e-tests/_repro-artifacts/before-fix.webm
```

### After fix (Step 6)

Clean the test results first, then re-run:

```bash
rm -rf test-results/
APP_MODE=legacy npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en
cp test-results/*/video.webm e2e-tests/_repro-artifacts/after-fix.webm
```

## Converting to GIF

GitHub PR descriptions support inline images (PNG, GIF, JPEG) but NOT inline `.webm` video. Convert to GIF for embedding.

### With ffmpeg (recommended)

```bash
ffmpeg -i e2e-tests/_repro-artifacts/before-fix.webm \
  -vf "fps=10,scale=800:-1" -loop 0 \
  e2e-tests/_repro-artifacts/before-fix.gif

ffmpeg -i e2e-tests/_repro-artifacts/after-fix.webm \
  -vf "fps=10,scale=800:-1" -loop 0 \
  e2e-tests/_repro-artifacts/after-fix.gif
```

Options explained:
- `fps=10` — 10 frames per second (balances smoothness vs file size)
- `scale=800:-1` — scale width to 800px, maintain aspect ratio
- `-loop 0` — loop the GIF infinitely

### Check if ffmpeg is available

```bash
which ffmpeg >/dev/null 2>&1 && echo "available" || echo "not found"
```

### Without ffmpeg (fallback)

If `ffmpeg` is not installed:

1. Keep the `.webm` files as-is.
2. After the PR is created, upload the `.webm` files as PR comment attachments.
3. Reference them in the PR body as download links rather than inline images.
4. Inform the user: "Install `ffmpeg` for inline GIF previews in PRs: `brew install ffmpeg` (macOS) or `sudo apt install ffmpeg` (Linux)."

## Embedding in PR Description

### With GIFs (inline preview)

After creating the PR with placeholder text, upload the GIFs. Two approaches:

**Approach A — GitHub drag-and-drop URL**

1. Create the PR with placeholder image references.
2. Open the PR in a browser.
3. Drag the GIF files into the PR description editor.
4. GitHub uploads them to `user-images.githubusercontent.com` and generates URLs.
5. The PR body is updated with the real URLs.

**Approach B — PR comment with images**

1. Create the PR with the description text (no images).
2. Add a PR comment with the GIFs:
   ```
   gh pr comment <PR_NUMBER> --body "## Recordings

   ### Before fix
   (drag before-fix.gif here)

   ### After fix
   (drag after-fix.gif here)"
   ```

**Approach A is preferred** because images are directly in the PR description.

### Without GIFs (webm attachments)

```markdown
## UI before changes
[Download before-fix.webm](link-to-attachment)

## UI after changes
[Download after-fix.webm](link-to-attachment)
```

## Cleanup

After the PR is created and images are uploaded, remove all temporary artifacts:

```bash
rm -rf e2e-tests/_repro-artifacts/
rm -rf test-results/
```
