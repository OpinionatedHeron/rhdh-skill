---
name: prose-editing
description: >-
  Edits prose somebody already wrote so it stops reading as machine-written,
  then scores the result with the bundled lint.py and reports total_per100w
  before and after. Reads the draft and picks one of four registers: strict for
  a runbook or an operator-facing error message, flavored for a README, a docs
  page, a changelog, or the body of a pull request that already exists, voiced
  for a release announcement or a bylined post, review to report every finding
  and change nothing. The two compressing registers apply an unofficial
  ASD-STE100 sentence and word discipline. Use for "make this not sound like
  AI", "tighten this draft", "score this and tell me what is wrong without
  rewriting it", or a register named outright such as strict, flavored, voiced,
  or review. It edits the words of a draft it is handed. Choosing what the
  document should say, composing the pull request, and filing the issue stay
  with whoever owns them.
compatibility: "Python 3.9+; the bundled linter is stdlib-only"
---

# Prose Editing

Remove the tells that mark a draft as machine-written, keep every fact, and
prove the change with a score taken before and after.

## Registers

Four routes. Infer one from the document. Never open by asking which one to
run: apply the register, then say in one line which register you used and which
one the user can ask for instead. A caller who names a register overrides the
inference.

| Register | The document is | Load |
|---|---|---|
| `strict` | a procedure, a runbook, a safety note, or an operator-facing error message | [mechanical](references/mechanical.md), [compression](references/compression.md) whole |
| `flavored` | a README, a docs page, a PR body, a changelog, a Jira issue description, or a code comment | [mechanical](references/mechanical.md), [compression](references/compression.md) down to its `strict` section |
| `voiced` | a release announcement, a blog post, or a document written under a byline | [mechanical](references/mechanical.md), [voice](references/voice.md) |
| `review` | anything nobody may rewrite | all three: [mechanical](references/mechanical.md), [compression](references/compression.md), [voice](references/voice.md) |

Each row names a whole document. A span inside a document leaves the row alone:
an error string quoted in a blog post, a runbook section inside a PR body, and a
first-person aside in a docs page all take the register of the document holding
them. The guards below keep the string itself intact.

### Precedence

The registers rank by how much of a draft they are licensed to change.

1. `review` rewrites nothing.
2. `voiced` rewrites machine tells and leaves sentence construction alone.
3. `flavored` also compresses: contractions expanded, sentences split at twenty
   words, semicolons cut.
4. `strict` also applies the procedure word set and the safety labels.

**When a document answers to two rows, take the one higher in that list.** A
README with a bylined introduction is `voiced`. A PR body that is mostly a
runbook is `flavored`. A changelog of CVE fixes is `flavored`, so `may allow
remote code execution` survives the pass.

When no row fits, take `voiced`. A document you cannot place still carries
machine tells worth removing, and compressing prose you cannot place is the
expensive mistake.

Take `review` whenever the user asks for findings, an audit, a score, or a
second opinion, whenever the user says not to change the text, and whenever the
text belongs to somebody else. A third-party README, a quoted spec, and a
customer's bug report are read, scored, and reported, never edited.

## Loop

Step 1 routes `review` out of this loop. Steps 2 to 8 belong to the three
rewriting registers.

1. **Infer the register.** Use the table above. State your choice in the reply,
   not as a question before you start. When the register is `review`, go to
   [Review](#review) and run none of the steps below.

2. **Score the source.** Do this before any editing. `<register>` is the
   register from step 1.

   ```bash
   python scripts/lint.py --json --register <register> /abs/path/draft.md > before.json
   ```

   Run from this skill's directory so `scripts/lint.py` resolves, and give the
   draft as an absolute path. Use `python3` where `python` is not on PATH. Write
   pasted text to a file in the system temporary directory first, so both runs
   read the same bytes and neither one depends on shell quoting.

3. **Read the whole report.** See [The report](#the-report), and work every
   category through the false-positive tests before you change anything.

4. **Rewrite.** Load the reference files the register calls for and apply them.
   Hold to the guards below.

5. **Score the rewrite against the baseline.**

   ```bash
   python scripts/lint.py --json --register <register> --baseline before.json /abs/path/draft.md
   ```

   `--baseline` adds a `delta` object holding `before`, `after`, and
   `improved`. `--help` lists the rest of the flags.

6. **Rewrite and score at most once more, then stop.** Two rewrite-and-score
   cycles is the cap whatever the score is. A category still firing after the
   second cycle gets reported as remaining, with what it is.

7. **Report the delta.** Give `before` and `after` per 100 words and name the
   categories that fell.

   > Register `flavored`. Score 9.4 to 3.1 per 100 words. `ai_vocabulary` 6 to
   > 0, `passive_voice` 4 to 1, `em_dash` 3 to 0. One `verbose_word` hit is
   > left in a quoted upstream release note. Ask for `strict` to also apply the
   > procedure word set.

   The report's own `bar` says how far a document still has to travel. It is
   not the verdict. A draft that moved from 9.4 to 3.1 improved, and the report
   says so rather than calling it a failure. A draft that moved from 2.6 to 2.4
   barely moved, and the report says that too.

8. **Deliver.** Take the first matching row of the delivery table.

## Review

Read, score, report. Nothing gets edited, and one score is the whole numeric
result.

1. **Score once.**

   ```bash
   python scripts/lint.py --json --register review /abs/path/draft.md
   ```

2. **Read the whole report.** See [The report](#the-report).

3. **Decide which hits govern.** `--register review` scores mechanical,
   compression, and voice together, and it adds the strict-only word set, so
   the report is a superset of any one register. The tool cannot tell what kind
   of document it was handed. You can. Name the register the document would take
   if somebody were rewriting it, read `by_layer` to see where the score comes
   from, and recommend an edit only for the layers that register loads. Report
   the rest as **out of register**: named, counted, and left without a
   recommendation.

   > A bylined post on the 1.10 upgrade scores 11 `contraction` and 6
   > `long_sentence`. The document is `voiced` and `voiced` loads no
   > compression, so those are not defects. Report the counts. Recommend no
   > expansion of `we've`.

   > A CVE changelog scores `strict_banned_word` on `may allow remote code
   > execution` and on `should upgrade to 1.10.2`. Those are the accurate words
   > for a vulnerability note, and a changelog is not a procedure. Report them.
   > Recommend neither `can allow` nor `must upgrade`.

4. **Report.** For each governing category, say what the hit is and what edit
   you would make. For each out-of-register category, say what it is and why it
   stands. State the single score.

5. **Deliver** by the `review` row of the delivery table.

## The report

Consume the full JSON object. Never pipe it through `head`, `tail`, or `grep`,
and never judge the text from an exit code alone.

| Key | What it tells you |
|---|---|
| `violations` | the count per category. This is the record of what the linter found and what you have to account for. |
| `samples` | up to six example hits per category, deduplicated. Twelve identical passives arrive as one sample. Read these for the shape of a hit, and `violations` for how many there are. |
| `by_layer` | which layer carries the score, so you know which reference governs |
| `markers` | `noun_train` and `rule_of_three`, reported but never scored |
| `delta` | `before`, `after`, `improved` |
| `total_per100w`, `bar`, `over_bar` | the score and its context |

When Python cannot run, work from the loaded reference files by eye, say the
text was **not linted**, and report no number. Do not estimate a score.

## Guards

- Keep every fact. Each claim, number, name, version, and condition in the
  source survives into the rewrite.
- Change the smallest span that removes the tell. Do not restyle a sentence no
  rule touches.
- Never invent a number, a name, a date, or a benchmark to satisfy a length cap
  or to replace a vague claim. A source with no measurement produces a rewrite
  with no measurement. Where a vague sentence cannot be made specific from the
  source, cut it or write the plain version.
- Leave untouched: fenced code, inline code, identifiers, commands, YAML
  frontmatter, link targets, and quoted third-party text. Link text is prose
  and you may edit it. The target inside the parentheses stays.
- An error string that a support engineer greps for is an identifier. Rewrite
  the sentences around it, not the string.
- When the draft already reads well, return it unchanged and say so with the
  score.

## False positives

The linter matches strings. It cannot tell a word being used from a word being
named. A glossary, a style guide, a bug report quoting a stack trace, and this
skill's own reference files all score for vocabulary they are discussing rather
than using.

Read each hit in place and put it through four tests.

- **Used or named?** A hit inside a definition, an example, a quotation, or a
  list of words to avoid is not a tell. Leave it and say why in the report.
- **Would the fix change a fact?** Then it is not a fix.
- **Is the hit inside somebody else's words?** Quoted upstream text stays.
- **Does its layer govern this document?** Under `review` the report covers
  every layer, so a hit can be real and still not apply to the document in
  hand. Report it as out of register. In a rewriting register this test never
  fires, because the linter scores only the layers that register loads.

A hit that survives all four is real, and a real hit has two honest endings:
fixed, or reported as remaining with what it is once the two rewrite cycles are
spent. Report a real hit under its own name. The false-positive label belongs
only to a hit that failed one of the four tests.

Two levers when a document has to name what it forbids. Blockquotes, table
cells, and code spans are removed before scoring, so putting examples in
blockquotes and word lists in tables clears the noise at the source. When the
words must sit in running prose, pass `--quote-safe`, which suppresses the
word-list categories and keeps the structural ones.

Some things are not tells at all:

- **One em dash.** Writers and editors use them. The habit is the tell, not the
  character.
- **Formal vocabulary.** The word lists name specific words. Do not flatten a
  precise word because it sounds academic.

Four categories firing inside one paragraph is a diagnosis rather than four
hits. That paragraph is the exception to the smallest-span guard: rewrite it
whole.

## Delivery

Take the first row that matches.

| The call came from | Where the text goes | What comes back |
|---|---|---|
| another skill | the return value | the prose the caller asked for and nothing else. Under `review`, the findings. |
| a person, under `review` | nowhere | findings per category with the edit you would make, plus the score. No rewritten document. |
| a person, who gave a file path | that file, edited in place | summary, delta, remaining tells |
| a person, who pasted the text | the reply | rewrite, delta, remaining tells |

A skill-to-skill call that asks for a rewrite returns text its caller is about
to post. Keep the register line, the score, and the delta out of that returned
text, and state them in the transcript beside it, where they stay your own gate
rather than becoming part of a PR review body. A skill-to-skill `review` is the
one exception: findings and their score are the whole deliverable, so they go in
the return value.

Edit the user's file yourself. Do not route that write through another skill.

## Remaining tells

Two problems survive every regex. Check for both after the final score.

- **A hollow paragraph.** It carries no fact, name, number, or command that the
  paragraph before it lacked. Cut it, or merge the one clause that is new.
- **A restated heading.** A heading followed by a sentence that says the
  heading again before the real content starts. Delete the sentence.

## Completion

Work is done when all of these hold.

- A register was inferred or taken from the caller, applied, and named, with the
  alternative offered in one line. That line goes in the reply to a person and
  in the transcript beside a return to another skill.
- The source was scored before the rewrite and the rewrite was scored against
  that baseline, or the reply says **not linted** and reports no number. A
  `review` has one score and no baseline.
- `before` and `after` per 100 words are stated with the categories that fell,
  in the reply to a person or in the transcript beside a return to another
  skill. A `review` states its single score instead, with the edit it would make
  for each governing hit.
- Every category holding a count above zero in the final `violations` is
  accounted for: fixed, reported as a false positive with a reason, reported as
  out of register under `review`, or reported as remaining with what it is.
- No fact, number, name, version, or identifier appears in the rewrite that is
  absent from the source.
- Code, commands, frontmatter, link targets, and quoted third-party text are
  unchanged from the source.
- Delivery matches the first matching row of the delivery table, and a `review`
  produced no rewritten document.
