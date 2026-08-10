# Workflow: Announce Feature Freeze

Generate a Slack message announcing that Feature Freeze milestone has been reached.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | Invoke `rhdh-jira`; require the needed capability in `JiraCapabilities/v1` |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json slack feature-freeze {{RELEASE_VERSION}}
```

Use its `slack_message` field directly. If it reports that `release_notes` is
unavailable, run `python scripts/release.py --json check`, configure the Rich
Filter as shown in `references/config.md`, and retry. Do not use a hardcoded
release-notes query because the Rich Filter is the source of truth.

</process>

<gotchas>

- This is the milestone announcement (sent ON the Feature Freeze date), not the update (sent BEFORE).
- Include Jira search links for all counts so recipients can drill down.

</gotchas>

<success_criteria>

- [ ] Slack message in triple-backtick code block
- [ ] EPICs, CVEs, and release notes counts filled with Jira links

</success_criteria>
