# Humanizer Gate

`/humanizer` is required for every review draft, including analysis-only.
Cluster-only routes that produce no review prose do not need it.

Before drafting, check whether the named skill is available through the host's
skill inventory. Do not scan installation directories and do not implement a
local substitute.

If unavailable, return exactly this interface and stop the draft branch:

```yaml
contract: SetupRequired/v1
id: rhdh-pr-review-humanizer
createdAt: 2026-08-10T12:00:00Z
data:
  missing: [humanizer]
  nextCommand: /setup-rhdh-skills
```

After the top-level summary and inline bodies exist, invoke `/humanizer` on all
of them. Preserve technical meaning, severity, file paths, line numbers,
suggestion fences, and review event. Present only the humanized draft to the
user.
