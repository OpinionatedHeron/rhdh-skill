---
name: prose-clean
description: >-
  Rewrites technical prose tight and scores it with a bundled Simplified
  Technical English linter. Use for prose-clean, technical writing, docs,
  README, PR body, changelog, or error message drafts that need ASD-STE100
  flavor: one name per thing, active voice, short sentences. Also use when
  asked to STE-flavor documentation, lint a runbook or procedure, tighten
  release notes, rewrite wordy docs, or run the bundled linter on a draft.
  Prefer this skill whenever the user wants technical prose shorter, consistent,
  and lintable.
compatibility: "Python 3.9+; bundled linter is stdlib-only"
---

# Prose Clean

Rewrite technical prose tight. Prove it with the bundled linter.

## Loop

1. **Identify delivery.** Infer one:
   - **Paste** — the draft is in the conversation.
   - **File** — the user named a path. The rewrite lands in that file.
   - **Embedded** — another skill called this one. Return cleaned prose only.
   - **Write-from-notes** — only when this skill is already invoked and there is
     no source draft. Draft from the conversation notes; then treat as paste.

2. **Select strictness.** Default **flavored** (bar 2.5 per 100 words). If the
   user already said `strict` or `flavored`, use that. Else if the text reads as
   a procedure, runbook, safety note, or error message, and delivery is not
   embedded, ask once whether to apply the strict word set. Default flavored if
   they do not answer. Never ask after a draft exists. A later `strict` re-runs
   this loop from step 3.

3. **Rewrite.** Read [references/flavored.md](references/flavored.md). When
   strict is selected, also read [references/strict.md](references/strict.md).
   Keep every fact. Change the smallest span that removes a tell. Leave code
   spans, identifiers, commands, frontmatter keys, link targets, and quoted
   third-party text untouched. Do not invent facts to satisfy a length cap.

4. **Lint.** From this skill directory, consume the full JSON. Never pipe
   through `head`, `tail`, or `grep`. Pass `--strict` when strict is selected.

   ```bash
   python scripts/lint.py --json DRAFT.md
   python scripts/lint.py --json --strict DRAFT.md
   python scripts/lint.py --json   # stdin
   ```

   If Python cannot run, apply the checklist in flavored.md (and strict.md when
   strict) by eye, say the text was **not linted**, skip any numeric score, and
   continue to step 5.

5. **Fix, then audit.** If the linter ran, repair every reported category and
   lint again. Stop after two lint-fix passes even if still over the bar — then
   state the score. Then do a remaining-tells pass the regex cannot see:
   - **Hollow paragraph** — adds no fact, name, number, or command the previous
     paragraph lacked. Cut it, or merge the one new clause.
   - **Fake significance** — the sentence only says the topic matters. Cut it.
     Do not replace it with a different significance claim.

   When flavored was used on procedure, runbook, safety, or error text, add one
   line that `strict` re-runs under the 1.5 bar. Do not ask.

6. **Deliver.**

   | Mode | Artifact | Conversation |
   |---|---|---|
   | Paste | — | Rewrite, score, remaining-tells |
   | File | Rewrite in place | Summary, score, remaining-tells |
   | Embedded | Cleaned prose only | Score is the agent's gate; keep it out of the artifact |

   A file edit in the user's workspace is this skill's job; do not route it
   through another skill. Do not present text as clean without a score, except
   the explicit **not linted** case in step 4.

## Completion

Done when all of these hold:

- The linter ran and its JSON was consumed, or the checklist ran and the reply
  says **not linted**.
- A score is reported (`mode`, `total_per100w`, `bar`, `over_bar`), unless not
  linted.
- Flavored `total_per100w` is ≤ 2.5, or strict is ≤ 1.5, or two lint-fix passes
  finished and the score is still stated.
- Remaining-tells were audited.
- Delivery matches the mode in step 6.
