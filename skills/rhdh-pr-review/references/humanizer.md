# Humanizer Gate

Shared prerequisite for every `review-code.md` draft path (including analysis-only). Do not re-implement humanizer here — invoke the installed skill.

## Humanizer prerequisite

Before drafting or presenting any review draft (top-level summary + inlines):

1. Run `python scripts/setup.py --humanizer-only --json` and check `humanizer_found`.
2. If missing: hard-stop. State that the `humanizer` skill is required before presenting review prose. Ask for confirmation, then install the minimal command from the setup output (`minimal_install`). Prefer recommending the recommended install when the user wants a fuller setup. Re-run the check. Continue only when `humanizer_found` is true.
3. The setup script detects only — it does not install. Confirm + install are owned by this skill.
4. Use `--humanizer-only` so the gate message stays humanizer-specific.

## When to invoke

After the review draft exists (top-level + inline bodies) and **before** presenting it to the user for event-type choice / confirmation:

1. Invoke the installed `humanizer` skill (read its SKILL.md and follow it; `/humanizer` if the host supports slash-commands).
2. Run it on **both** the top-level summary and every inline comment body.
3. Present the humanized draft to the user — never show pre-humanizer prose as the draft.

Applies to all `review-code.md` routes, including analysis-only (route 2). Cluster-testing-only routes that never draft review prose do not need this gate.
