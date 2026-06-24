---
name: fork-sync
description: |
  Automatically sync all branches in a forked repository with their upstream counterparts.
  Use when you need to sync fork with upstream, update forked repo, pull latest upstream changes, bring fork up to date, or sync all branches at once.
  Also use when asked to update fork, sync with upstream, pull upstream changes across multiple branches, or when your fork is behind the original repository.
---

# Fork Sync

Automatically sync all branches in a forked repository with their upstream counterparts. Safely updates existing branches and creates new upstream branches locally while preserving all local work.

## Quick Start

Run in any git repository with an upstream remote configured. The skill will:
- Sync all branches that are simply behind upstream (fast-forward only)
- Create new local branches for upstream branches that don't exist locally
- Report any branches that need manual attention due to conflicts or local commits

## Setup Requirements

Before running, verify your repository has an upstream remote configured:

```bash
git remote -v
```

You should see an `upstream` remote pointing to the original repository. If not, add it:

```bash
git remote add upstream <original-repo-url>
```

## Workflow

Run the sync operation using the built-in script:

```bash
python scripts/sync_fork.py
```

The skill follows this safe sequence:

1. **Environment Check** — Verify we're in a git repo with upstream configured
2. **Fetch Latest** — Download all upstream changes without modifying local branches  
3. **Branch Analysis** — Compare local and upstream branches to plan sync operations
4. **Safe Sync** — Update branches that can be fast-forwarded without data loss
5. **Create Missing** — Add new local tracking branches for upstream branches
6. **Report Results** — Provide clear summary of all operations and any required actions

### Available Options

- `--dry-run` — Preview what would be done without making changes
- `--branches <branch1> <branch2>` — Sync only specific branches
- `--json` — Output results as structured JSON for further processing

### Sync Operations

**Safe to auto-sync:**
- Branches that are behind upstream with no local commits (fast-forward merge)
- New upstream branches that don't exist locally (create and track)

**Requires manual attention:**
- Branches with uncommitted changes (preserved, sync skipped)
- Branches with local commits ahead of upstream (potential merge needed)
- Branches with merge conflicts (manual resolution required)

## Key Guidelines

- **Safety First** — Never lose local work or uncommitted changes. When in doubt, skip and report.
- **Fast-forward Only** — Only update branches that can be cleanly fast-forwarded. Divergent branches require manual review.
- **Preserve Local State** — Don't modify working directory or current branch unless explicitly safe.
- **Clear Communication** — Always report what was done, what was skipped, and why.

## Branch Filtering

By default, syncs all branches. Optional filtering available:
- Specify branch patterns to include/exclude
- Focus on specific branches for targeted updates
- Skip inactive or experimental branches

## Output Format

The skill provides a structured summary:

**✅ Successfully Synced:** Branches updated with commit counts
**🆕 Created:** New branches added from upstream  
**⚠️ Skipped:** Branches that need attention with specific reasons
**❌ Errors:** Any failures with suggested fixes

## Script Integration

This skill uses `scripts/sync_fork.py` to handle all git operations. The script provides structured JSON output that enables precise error handling and user communication.

**Always run the script first** to gather current repository state and sync results. Process the JSON output to:
- Interpret any errors and provide specific guidance
- Translate technical results into user-friendly summaries
- Suggest next steps for branches that couldn't be synced automatically

**Example workflow:**
1. Run `python scripts/sync_fork.py --json` to perform sync
2. Parse JSON results to understand what happened
3. Provide clear summary to user with any required actions

## Gotchas

- **Uncommitted Changes** — Branches with dirty working trees are automatically skipped to prevent data loss
- **Divergent History** — Branches with local commits ahead of upstream require manual merge decisions
- **Authentication** — Ensure you have proper access to fetch from upstream (SSH keys, tokens, etc.)
- **Large Repositories** — Initial upstream fetch may take time for repos with extensive history
- **Force-pushed Upstream** — If upstream has rewritten history, manual intervention may be needed

## Error Recovery

Common issues and solutions:

**"No upstream remote configured"**
→ Add upstream: `git remote add upstream <original-repo-url>`

**"Authentication failed"** 
→ Check SSH keys or access tokens for upstream repository

**"Merge conflict detected"**
→ Manual resolution required: `git checkout <branch> && git merge upstream/<branch>`

**"Branch has local commits"**
→ Review commits and decide: merge, rebase, or keep separate