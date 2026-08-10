# Optional: call this linker from `raise-pr`

`raise-pr` Step 11 should call this skill's linker for the Web link + comment,
then keep `raise-pr`'s Review transition.

```bash
# After PR_URL and PR_TITLE are known (raise-pr Step 10):
REPO_SHORT="$(basename "$(git rev-parse --show-toplevel)")"
PR_NUM=…   # from gh pr create output / API

node "$SKILL/scripts/link-pr-mr.js" link \
  --issue "$JIRA_KEY" \
  --url "$PR_URL" \
  --title "${REPO_SHORT} #${PR_NUM}: ${PR_TITLE}" \
  --host github \
  --no-defaults

# Then transition to Review (raise-pr intent — do not rely on linker In Progress):
acli jira workitem transition --key "$JIRA_KEY" --status "Review" --yes
```

Why `--no-defaults`: the linker’s default status target is **In Progress**;
`raise-pr` wants **Review** after PR submit. Defaults (story points, team, etc.)
remain available for general agent sessions that use `create-pr-mr.js` alone.
