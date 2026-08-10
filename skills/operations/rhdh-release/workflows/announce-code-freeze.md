# Workflow: Announce Code Freeze

Generate a Slack message announcing that Code Freeze milestone has been reached.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | Invoke `rhdh-jira`; require the needed capability in `JiraCapabilities/v1` |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
uv run scripts/release.py --json slack code-freeze {{RELEASE_VERSION}}
```

If the CLI succeeds, use its `slack_message` field directly (it's the filled template). If it fails, follow the manual steps below.

## Step 2 (fallback): Get blocker bugs

Invoke `rhdh-jira` with the `blockers` JQL from `references/jql-release.md` and
take the count from `JiraQueryResult/v1`.

## Step 3 (fallback): Get feature demos count

Use the `feature_demos` template composed from the Rich Filter `demo` entry:

```bash
uv run scripts/release.py --json rich-filter query static demo --version "{{RELEASE_VERSION}}" --count
```

## Step 4 (fallback): Get test day features count

Use the `test_day_features` template composed from the Rich Filter `Test Day` entry:

```bash
uv run scripts/release.py --json rich-filter query static "Test Day" --version "{{RELEASE_VERSION}}" --count
```

## Step 5 (fallback): Get total open issues count

Invoke `rhdh-jira` with the `open_issues` JQL from `references/jql-release.md`
and take the count from `JiraQueryResult/v1`.

## Step 6 (fallback): Fill template and output

Load the **Code Freeze Announcement** template from `references/slack-templates.md`.

Fill all placeholders:

- `{{RELEASE_VERSION}}` — the release version
- `{{BLOCKER_BUG_ISSUE_COUNT}}` — from Step 1
- `{{FEATURE_DEMO_ISSUE_COUNT}}` — from Step 2
- `{{TEST_DAY_FEATURE_ISSUE_COUNT}}` — from Step 3
- `{{OPEN_ISSUE_COUNT}}` — from Step 4
- `{{JIRA_LINK}}` — URL-encoded Jira search link for each count

**Output the filled template in a triple-backtick code block** for copy-paste into Slack.

</process>

<gotchas>

- This is the milestone announcement (sent ON the Code Freeze date), not the update (sent BEFORE).
- After Code Freeze: no cherry-picks without explicit RM approval, only critical CVEs considered for GA.

</gotchas>

<success_criteria>

- [ ] Slack message in triple-backtick code block
- [ ] Blocker bugs, feature demos, test day features, and open issue counts filled with Jira links

</success_criteria>
