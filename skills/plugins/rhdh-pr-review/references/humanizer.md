# Humanizer Gate

`/humanizer` is required for every review draft, including analysis-only.
Cluster-only routes that produce no review prose do not need it.

Before drafting, check whether the named skill is available through the host's
skill inventory. Do not scan installation directories and do not implement a
local substitute.

If unavailable, stop the draft branch and return the `SetupRequired/v1` envelope
defined by the named skill `rhdh-mutation-gate`, with `id: rhdh-pr-review-humanizer`,
`route: install`, `missing: [humanizer]`, and
`nextCommand: /setup-rhdh-skills install`. Generate `createdAt` when the
artifact is produced; never copy a timestamp out of an example.

After the top-level summary and inline bodies exist, invoke `/humanizer` on all
of them. Preserve technical meaning, severity, file paths, line numbers,
suggestion fences, and review event. Present only the humanized draft to the
user.
