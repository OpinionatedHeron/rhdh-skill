# Skill naming and namespace isolation

**Status:** Accepted.

## Context

Every promoted model-invoked skill carries an `rhdh-` prefix. The prefix looks
redundant once skills are grouped into folders, and removing it reads as an
obvious cleanup: `plugins/rhdh-plugin-export` says "plugin" twice and "rhdh" once
more than the path already does.

It is not redundant, and this ADR exists because the cleanup is tempting enough to
be proposed repeatedly. It was proposed during the decomposition, accepted, and
reversed only after the namespace was measured.

**Folders are stripped at install.** `npx skills add … -g` flattens every skill
into `~/.claude/skills/` with no category layer. Verified directly: previously
installed skills sit there as top-level entries. The validator names the host roots
explicitly, and no skill references a category path. The folder never reaches the
router.

**The router matches descriptions, not paths.** A skill competes against every
other installed skill on description text alone. A representative developer machine
carried **70 installed skills** when this was measured, from several unrelated
packs.

Concrete collisions found for the proposed bare names:

- `plugin-development` — in Claude Code, "plugin" means a *Claude Code plugin*.
  Skills shipped with the host claim "create a plugin, build a plugin, scaffold a
  plugin". A bare name collides on nearly every trigger phrase.
- `to-issue` / `to-epic` / `to-feature` — near-synonyms of the `to-tickets` and
  `to-spec` family from a pack this project's own README tells users to install.
- `refine`, `assign` — bare verbs with no domain anchor, colliding with `triage`
  and the grilling family.
- `raise-pr` — collides with `pr-writer`, `gh-stack`, and `pr-review-github`.

## Decision

Every promoted model-invoked skill keeps the `rhdh-` prefix, including reference
skills. Human-invoked entry points (`ask-rhdh`, `setup-rhdh-skills`) carry the
token in whatever position reads naturally.

Within the prefix, name by **domain then verb**, matching the trigger phrase the
skill claims: `rhdh-jira-create`, `rhdh-jira-refine`, `rhdh-pr-create`,
`rhdh-pr-review`, `rhdh-prow-jobs`. Sibling skills use the same word for the same
thing — not `rhdh-pull-request` beside `rhdh-pr-review`.

Two skills must not share a name prefix unless they share a domain. `rhdh-test-plan`
beside `rhdh-test-placement` reads as one family and is two unrelated jobs; the
first becomes `rhdh-test-plan-review` so the verb separates them.

A description states the proper nouns it owns — project keys, repository names,
tool names — because a literal token is the strongest anchor available. Dropping
`RHIDP-1234` from a description in favour of the phrase "Jira keys" measurably
weakened routing for a bare issue key, and was restored.

## Consequences

- Eight characters per skill, paid once, in exchange for the only isolation the
  pack has after installation.
- The prefix cannot be removed later without re-breaking every user's install, so
  the decision is effectively permanent.
- Growing from 18 to ~41 skills roughly doubles the namespace footprint. Removing
  the disambiguator at the same time would have been the single highest-risk change
  in the restructure.
- Names are longer than the folder structure suggests they need to be. That
  redundancy is deliberate: the folder is for readers of this repository, the
  prefix is for the router on someone else's machine.
