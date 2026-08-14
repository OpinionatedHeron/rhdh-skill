# Flavored rewrite rules

Unofficial Simplified Technical English flavor for docs, README, PR body,
changelog, and error text. Not a certified ASD-STE100 checker. Do not paste an
ASD dictionary here. The bundled linter is the score; this file is how to
rewrite so that score can pass.

Bar: **2.5** violations per 100 words (`total_per100w`). Mode `flavored`.

## Guards

Keep every fact. Change the smallest span that removes a tell. Leave fenced
code, inline code, identifiers, commands, frontmatter keys, link targets, and
quoted third-party text untouched. Do not invent a number, name, or claim to
make a sentence shorter.

## STE flavor

**One name per thing.** Pick one word for each concept and reuse it. Do not
rotate synonyms (`start` / `begin` / `initiate`). Technical nouns the source
already uses stay (`webhook`, `overlay`, `PipelineRun`).

**Active voice.** Name the actor. `The operator writes the secret` not `The
secret is written`. Keep a short stative (`is installed`) when no actor is in
the source; do not invent one.

**Short sentences.** Aim for 20 words or fewer. Split at the period. One idea
per sentence. Replace a semicolon with a period.

**Simple tenses.** Use present or simple past as the main verb. Avoid perfect
and progressive as the spine (`has been configured`, `is running` as the claim).
State the fact: `The chart configures the route.` / `The job ran.`

**Verbs, not nouns.** `Configure the plugin` not `perform the configuration of
the plugin`. Cut `make use of`, `carry out`, `conduct`.

**No phrasal verbs.** Write a single verb:

| Instead of | Write |
|---|---|
| spin up / spun up | start |
| spin down / tear down | stop / remove |
| reach out | contact |
| dive into | read / describe |
| kick off | start |
| roll out | release |
| ramp up | increase |
| circle back | return |
| drill down | inspect |

**No marketing adjectives.** Drop them, or keep only a measure that is already
in the source. Do not invent a benchmark to replace `fast`. The linter flags
words such as `seamless`, `robust`, `powerful`, `cutting-edge`, `effortless`,
`world-class`, `elegant`, `unlock`, `unleash`, `empower`, `supercharge`,
`enterprise-grade`, `battle-tested`.

**Plain words.** Prefer the short form. The linter flags (among others)
`begin`/`commence`/`initiate` → `start`; `utilize`/`leverage` → `use`;
`facilitate` → name the action; `ensure` → state the requirement; `prior to` →
`before`; `in order to` → `to`; `provide` → `give` or the concrete verb;
`additionally`/`furthermore`/`moreover` → a new sentence or delete;
`comprehensive`/`numerous`/`myriad`/`plethora` → a count from the source, or
cut; `aforementioned`/`henceforth`/`therein`/`whilst`/`amongst` → `this` /
`from now` / `in it` / `while` / `among`.

**No contractions.** `it is`, `do not`, `cannot`.

**No modal hedges.** Cut `it is important to note`, `it should be noted`,
`it is worth noting`, `please note that`, `as mentioned`, `as noted above`.
Keep the clause that followed.

**Articles and noun trains.** Keep `a`/`the` where English needs them. Break a
run of four or more uncapitalized nouns with `of` or a verb. The linter reports
`noun_train` as a sample; it does not add to the score. Still break the train.

**Paragraphs.** More than six sentences in one block is a `long_paragraph` hit.
Split.

## Mechanical tells (always on)

These are scored in every mode.

**Em dashes.** Replace `—` or `–` with a period, a comma, or parentheses.

**Chatbot residue.** Delete the sentence: `I hope this helps`, `let me know if`,
`would you like`, `you're absolutely right`, `of course!`, `here is a` /
`here is an`.

**Copula avoidance.** `serves as` / `stands as` → `is`, or a verb that names
the job. `The parser serves as a gateway` → `The parser is the gateway` (only
if that fact is in the source).

**`It's not just` parallelism.** `It's not just X, it's Y` → state Y, or state
X, from the source. Do not keep the antithesis.

## Worked example

Before:

> This seamless solution will leverage cutting-edge tooling to supercharge your
> workflow — it is important to note that the parser serves as a gateway. I hope
> this helps! It's not just a parser, it's a platform.

After:

> The tooling is in the workflow. The parser is the gateway.

Only facts that were in the source survive. `platform` was puff; drop it unless
the source defined it. Do not add actions the source never stated.

## Linter JSON

Consume the full object. Categories in `violations` that add to the score:
`long_sentence`, `semicolon`, `contraction`, `passive_voice`, `complex_tense`,
`ing_main_verb`, `nominalization`, `phrasal_verb`, `banned_word`,
`marketing_adjective`, `modal_hedge`, `long_paragraph`, `em_dash`,
`chatbot_residue`, `copula_avoidance`, `not_just_parallelism`.

Fix from `samples` and from the counts. `over_bar` is the gate.

## Checklist when Python cannot run

Walk the categories above by eye. Say the text was **not linted**. Do not invent
a `total_per100w`.
