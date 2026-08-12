# Call this linker from `raise-pr`

`raise-pr` Step 11 calls this skill's linker for the Web link + comment, then
runs its own **Review** transition.

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
# RHDHPLAN Epic/Story/Task may have been moved to RHIDP — use post-move key:
EFFECTIVE_KEY="$(printf '%s\n' "$LINK_OUT" | awk -F': ' '/^issue:/{print $2; exit}')"
EFFECTIVE_KEY="${EFFECTIVE_KEY:-$JIRA_KEY}"

acli jira workitem transition --key "$EFFECTIVE_KEY" --status "Review" --yes
```

Why `--no-defaults`: the linker’s default status target is **In Progress**;
`raise-pr` wants **Review** after PR submit. Defaults (story points, team, etc.)
remain available for general agent sessions that use `create-pr-mr.js` alone.
