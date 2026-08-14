# Strict rewrite rules

Extra word set and a tighter bar for procedures, runbooks, safety notes, and
error messages. Independently usable: do not load `flavored.md` first. Unofficial
Simplified Technical English; not a certified ASD-STE100 checker.

Bar: **1.5** violations per 100 words. Mode `strict`. The linter adds
`strict_banned_word` on top of the flavored categories.

Pass `--strict` to `scripts/lint.py`.

## Guards

Keep every fact. Change the smallest span that removes a tell. Leave fenced
code, inline code, identifiers, commands, frontmatter keys, link targets, and
quoted third-party text untouched. Do not invent facts to satisfy the 1.5 bar.

Name the actor. Keep sentences at 20 words or fewer. Use present or simple past.
One instruction per sentence. Write the condition before the command:
`If the file is missing, exit 1.` Expand contractions. Replace em dashes and
semicolons with periods. Delete chatbot residue and `it's not just`
parallelism. Replace `serves as` / `stands as` with `is` or a job verb.

## Extra word set

These count only in strict. `May` the month does not count; lowercase `may`
does.

| Flagged | Write instead |
|---|---|
| however | `but`, or start a new sentence |
| since | `because` (reason) or `after` (time) |
| should | `must`, or the command: `Stop the pod.` |
| shall | `must`, or the command |
| using | `with`, or `use` as the verb |
| follow / follows / followed | `do` / `do the steps in` |
| may | `can` (ability) or `might` (possibility) |

Do not write `You should follow the runbook using the listed steps.`
Write `Do the steps in the runbook.`

## When this file applies

Procedures, runbooks, safety notes, and error messages — text a reader might
misread and then do the wrong thing. Descriptive docs, README overview, PR body,
and changelog stay flavored unless the user asked for strict.

Safety and errors: no hedge. Name the condition and the action. Do not write
`might want to consider`. Write `If X, do Y.`

## Linter JSON

`violations.strict_banned_word` is the extra count. `bar` is 1.5. `over_bar` is
the gate. Flavored categories still score.

## Checklist when Python cannot run

Walk the extra word set and the guards above by eye. Say the text was **not
linted**. Do not invent a `total_per100w`.
