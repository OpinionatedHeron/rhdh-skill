#!/usr/bin/env python3
"""Sync all branches in a forked repository with their upstream counterparts."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def run_git_command(cmd: List[str], cwd: Path = None) -> Tuple[bool, str, str]:
    """Run a git command and return (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or Path.cwd(),
            capture_output=True,
            text=True,
            shell=(sys.platform == "win32")
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def check_git_repo() -> Dict:
    """Check if we're in a valid git repository with upstream configured."""
    # Check if it's a git repo
    success, _, _ = run_git_command(["git", "rev-parse", "--git-dir"])
    if not success:
        return {"valid": False, "error": "Not a git repository"}

    # Check for upstream remote
    success, remotes, _ = run_git_command(["git", "remote"])
    if not success or "upstream" not in remotes.split():
        return {"valid": False, "error": "No upstream remote configured"}

    # Get upstream URL for info
    success, upstream_url, _ = run_git_command(["git", "remote", "get-url", "upstream"])
    if not success:
        return {"valid": False, "error": "Could not get upstream URL"}

    return {"valid": True, "upstream_url": upstream_url}


def fetch_upstream() -> Dict:
    """Fetch all branches from upstream."""
    success, stdout, stderr = run_git_command(["git", "fetch", "upstream", "--prune"])
    return {
        "success": success,
        "output": stdout,
        "error": stderr
    }


def get_branch_info() -> Dict:
    """Get information about all local and upstream branches."""
    # Get local branches
    success, local_output, _ = run_git_command(["git", "branch", "--format=%(refname:short)"])
    local_branches = local_output.split() if success else []

    # Get upstream branches (excluding HEAD pointer)
    success, upstream_output, _ = run_git_command(["git", "branch", "-r", "--format=%(refname:short)"])
    if success:
        upstream_branches = [
            branch.replace("upstream/", "")
            for branch in upstream_output.split()
            if branch.startswith("upstream/") and not branch.endswith("/HEAD")
        ]
    else:
        upstream_branches = []

    return {
        "local_branches": local_branches,
        "upstream_branches": upstream_branches,
        "new_branches": [b for b in upstream_branches if b not in local_branches]
    }


def check_branch_status(branch: str) -> Dict:
    """Check the status of a specific branch relative to upstream."""
    # Save current branch
    success, current_branch, _ = run_git_command(["git", "branch", "--show-current"])
    if not success:
        return {"error": "Could not determine current branch"}

    # Check if branch has uncommitted changes
    success, _, _ = run_git_command(["git", "checkout", branch])
    if not success:
        return {"error": f"Could not checkout branch {branch}"}

    # Check working directory status
    success, status_output, _ = run_git_command(["git", "status", "--porcelain"])
    has_changes = success and len(status_output.strip()) > 0

    # Check commits ahead/behind upstream
    success, ahead_behind, _ = run_git_command([
        "git", "rev-list", "--left-right", "--count",
        f"upstream/{branch}...{branch}"
    ])

    ahead, behind = 0, 0
    if success and ahead_behind.strip():
        try:
            behind, ahead = map(int, ahead_behind.split())
        except ValueError:
            pass

    # Return to original branch
    run_git_command(["git", "checkout", current_branch.strip()])

    return {
        "branch": branch,
        "has_uncommitted_changes": has_changes,
        "ahead": ahead,
        "behind": behind,
        "can_fast_forward": behind > 0 and ahead == 0 and not has_changes
    }


def sync_branch(branch: str) -> Dict:
    """Sync a branch with upstream if safe to do so."""
    status = check_branch_status(branch)
    if "error" in status:
        return status

    if not status["can_fast_forward"]:
        return {
            "branch": branch,
            "synced": False,
            "reason": "Cannot fast-forward",
            "details": status
        }

    # Perform the sync
    success, _, _ = run_git_command(["git", "checkout", branch])
    if not success:
        return {"branch": branch, "synced": False, "reason": "Could not checkout branch"}

    success, output, error = run_git_command(["git", "merge", "--ff-only", f"upstream/{branch}"])
    if success:
        return {
            "branch": branch,
            "synced": True,
            "commits_pulled": status["behind"],
            "output": output
        }
    else:
        return {
            "branch": branch,
            "synced": False,
            "reason": "Fast-forward merge failed",
            "error": error
        }


def create_branch(branch: str) -> Dict:
    """Create a new local branch tracking upstream."""
    success, output, error = run_git_command([
        "git", "checkout", "-b", branch, f"upstream/{branch}"
    ])

    if success:
        # Set up tracking
        run_git_command(["git", "branch", "--set-upstream-to", f"upstream/{branch}", branch])
        return {
            "branch": branch,
            "created": True,
            "tracking": f"upstream/{branch}"
        }
    else:
        return {
            "branch": branch,
            "created": False,
            "error": error
        }


def main():
    parser = argparse.ArgumentParser(description="Sync forked repository with upstream")
    parser.add_argument(
        "--branches",
        nargs="*",
        help="Specific branches to sync (default: all branches)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    results = {
        "repo_check": check_git_repo(),
        "synced": [],
        "created": [],
        "skipped": [],
        "errors": []
    }

    if not results["repo_check"]["valid"]:
        if args.json:
            json.dump(results, sys.stdout, indent=2)
        else:
            print(f"Error: {results['repo_check']['error']}")
        sys.exit(1)

    # Fetch upstream
    if not args.dry_run:
        fetch_result = fetch_upstream()
        if not fetch_result["success"]:
            results["errors"].append({
                "operation": "fetch",
                "error": fetch_result["error"]
            })
            if args.json:
                json.dump(results, sys.stdout, indent=2)
            else:
                print(f"Error fetching upstream: {fetch_result['error']}")
            sys.exit(1)

    # Get branch information
    branch_info = get_branch_info()
    target_branches = args.branches if args.branches else branch_info["local_branches"]

    # Save current branch to restore later
    success, original_branch, _ = run_git_command(["git", "branch", "--show-current"])
    original_branch = original_branch.strip() if success else "main"

    # Sync existing branches
    for branch in target_branches:
        if branch in branch_info["local_branches"]:
            if args.dry_run:
                status = check_branch_status(branch)
                if status.get("can_fast_forward"):
                    results["synced"].append({
                        "branch": branch,
                        "would_sync": True,
                        "commits_to_pull": status["behind"]
                    })
                else:
                    results["skipped"].append({
                        "branch": branch,
                        "reason": "Would require manual attention",
                        "details": status
                    })
            else:
                sync_result = sync_branch(branch)
                if sync_result.get("synced"):
                    results["synced"].append(sync_result)
                else:
                    results["skipped"].append(sync_result)

    # Create new branches from upstream
    for branch in branch_info["new_branches"]:
        if not args.branches or branch in args.branches:
            if args.dry_run:
                results["created"].append({
                    "branch": branch,
                    "would_create": True,
                    "tracking": f"upstream/{branch}"
                })
            else:
                create_result = create_branch(branch)
                if create_result.get("created"):
                    results["created"].append(create_result)
                else:
                    results["errors"].append(create_result)

    # Return to original branch
    if not args.dry_run:
        run_git_command(["git", "checkout", original_branch])

    # Output results
    if args.json:
        json.dump(results, sys.stdout, indent=2)
    else:
        print_human_summary(results, args.dry_run)

    # Exit with appropriate code
    sys.exit(0 if not results["errors"] else 1)


def print_human_summary(results: Dict, dry_run: bool):
    """Print a human-readable summary of the sync operation."""
    action_verb = "Would sync" if dry_run else "Synced"

    print(f"\n🔄 Fork Sync {'(Dry Run) ' if dry_run else ''}Summary")
    print(f"📍 Upstream: {results['repo_check']['upstream_url']}")
    print()

    if results["synced"]:
        print(f"✅ {action_verb}:")
        for item in results["synced"]:
            commits = item.get("commits_pulled", item.get("commits_to_pull", 0))
            print(f"   • {item['branch']} ({commits} commits)")

    if results["created"]:
        create_verb = "Would create" if dry_run else "Created"
        print(f"\n🆕 {create_verb}:")
        for item in results["created"]:
            tracking = item.get('tracking', f"upstream/{item['branch']}")
            print(f"   • {item['branch']} → {tracking}")

    if results["skipped"]:
        print(f"\n⚠️  Skipped:")
        for item in results["skipped"]:
            reason = item.get("reason", "Unknown reason")
            print(f"   • {item['branch']} - {reason}")

            # Add helpful details for common skip reasons
            details = item.get("details", {})
            if details.get("has_uncommitted_changes"):
                print(f"     (has uncommitted changes)")
            elif details.get("ahead", 0) > 0:
                print(f"     (has {details['ahead']} local commits)")

    if results["errors"]:
        print(f"\n❌ Errors:")
        for error in results["errors"]:
            if "branch" in error:
                print(f"   • {error['branch']}: {error.get('error', 'Unknown error')}")
            else:
                print(f"   • {error.get('operation', 'Unknown')}: {error.get('error', 'Unknown error')}")

    print()


if __name__ == "__main__":
    main()