# Optional: call this linker from `raise-pr`

`raise-pr` Step 11 should call this skill's linker for the Web link + comment,
then keep `raise-pr`'s Review transition.

```bash
# After PR_URL and PR_TITLE are known (raise-pr Step 10):
REPO_SHORT="$(basename "$(git rev-parse --show-toplevel)")"
PR_NUM=…   # from gh pr create output / API

LINK_OUT="$(node "../jira-pr-mr-link/scripts/link-pr-mr.js" link \
  --issue "$JIRA_KEY" \
  --url "$PR_URL" \
  --title "${REPO_SHORT} #${PR_NUM}: ${PR_TITLE}" \
  --host github \
  --no-defaults)"
echo "$LINK_OUT"
# If the issue was a RHDHPLAN Epic/Story/Task, linker may have moved it to RHIDP —
# prefer the post-move key from stdout for the Review transition:
EFFECTIVE_KEY="$(printf '%s\n' "$LINK_OUT" | awk -F': ' '/^issue:/{print $2; exit}')"
EFFECTIVE_KEY="${EFFECTIVE_KEY:-$JIRA_KEY}"

# Then transition to Review (raise-pr intent — do not rely on linker In Progress):
acli jira workitem transition --key "$EFFECTIVE_KEY" --status "Review" --yes
```

Why `--no-defaults`: the linker’s default status target is **In Progress**;
`raise-pr` wants **Review** after PR submit. Defaults (story points, team, etc.)
remain available for general agent sessions that use `create-pr-mr.js` alone.

Path note: resolve `link-pr-mr.js` relative to the installed `skills/` tree (same
shape as other cross-skill references). Do not invent `$JIRA_PR_MR_LINK_SKILL`.
